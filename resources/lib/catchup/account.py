"""Log in and log out (settings buttons), as plugin.video.kofin's account flow."""

import time
from typing import Optional

import xbmc
import xbmcgui

from catchup import auth, settings
from catchup.http import Http, HttpError, JellyfinError, Unauthorized
from catchup.log import Logger
from catchup.settings import Credentials

LOG = Logger(__name__)

QUICK_CONNECT_TIMEOUT_SECONDS = 180
QUICK_CONNECT_POLL_SECONDS = 1.5


def _text(string_id: int) -> str:
    return settings.localized(string_id)


def login() -> None:
    creds = Credentials.load()
    if creds.is_logged_in:
        settings.notify(_text(30025))
        return

    address_raw = settings.get_str("serverAddress")
    if not address_raw:
        address_raw = xbmcgui.Dialog().input(_text(30052))
        if not address_raw:
            return

    transport = Http(settings.user_agent())
    try:
        address = auth.normalize_address(address_raw)
        info = auth.public_info(transport, address)
    except HttpError as error:
        LOG.warning("server ping answered badly for %s: %s", address_raw, error)
        settings.notify(_text(30821) % error, xbmcgui.NOTIFICATION_ERROR)
        return
    except JellyfinError as error:
        LOG.warning("server ping failed for %s: %s", address_raw, error)
        settings.notify(_text(30018), xbmcgui.NOTIFICATION_ERROR)
        return
    except ValueError as error:
        LOG.warning("server address refused: %s", error)
        settings.notify(_text(30018), xbmcgui.NOTIFICATION_ERROR)
        return

    header = auth.build_auth_header(
        settings.device_name(), creds.device_id, settings.addon_version()
    )
    server_name = info.get("ServerName") or address

    try:
        result = _authenticate(transport, address, header, server_name)
    except Unauthorized:
        settings.notify(_text(30017), xbmcgui.NOTIFICATION_ERROR)
        return
    except JellyfinError as error:
        LOG.warning("sign-in failed: %s", error)
        settings.notify(_text(30018), xbmcgui.NOTIFICATION_ERROR)
        return
    finally:
        transport.close()

    if result is None or not result.token:
        return

    creds.server_address = address
    creds.server_name = server_name
    creds.server_id = result.server_id
    creds.user_id = result.user_id
    creds.display_user = result.user_name
    creds.token = result.token
    creds.is_logged_in = True
    creds.save()
    settings.notify(_text(30016) % result.user_name)
    LOG.info("signed in to %s", server_name)


def _authenticate(
    transport: Http, address: str, header: str, server_name: str
) -> Optional[auth.AuthResult]:
    quick_connect = False
    try:
        quick_connect = auth.quick_connect_enabled(transport, address, header)
    except JellyfinError:
        pass

    if quick_connect:
        choice = xbmcgui.Dialog().select(
            _text(30027) % server_name, [_text(30011), _text(30012)]
        )
        if choice < 0:
            return None
        if choice == 0:
            return _login_quick_connect(transport, address, header)
    return _login_password(transport, address, header)


def _login_password(
    transport: Http, address: str, header: str
) -> Optional[auth.AuthResult]:
    username = xbmcgui.Dialog().input(_text(30013))
    if not username:
        return None
    # Dialog.input answers "" both for a cancel and for an empty password,
    # which a Jellyfin account may have; the keyboard says which it was.
    keyboard = xbmc.Keyboard("", _text(30014), True)
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return None
    return auth.authenticate_password(
        transport, address, header, username, keyboard.getText()
    )


def _login_quick_connect(
    transport: Http, address: str, header: str
) -> Optional[auth.AuthResult]:
    state = auth.quick_connect_initiate(transport, address, header)
    secret = state.get("Secret", "")
    code = state.get("Code", "")
    if not secret or not code:
        return None

    progress = xbmcgui.DialogProgress()
    progress.create(_text(30011), _text(30015) % code)
    monitor = xbmc.Monitor()
    started = time.time()
    try:
        while time.time() - started < QUICK_CONNECT_TIMEOUT_SECONDS:
            if progress.iscanceled():
                return None
            if auth.quick_connect_poll(transport, address, header, secret):
                return auth.authenticate_quick_connect(
                    transport, address, header, secret
                )
            percent = int((time.time() - started) * 100 / QUICK_CONNECT_TIMEOUT_SECONDS)
            progress.update(min(99, percent), _text(30015) % code)
            if monitor.waitForAbort(QUICK_CONNECT_POLL_SECONDS):
                return None
    finally:
        progress.close()
    settings.notify(_text(30024), xbmcgui.NOTIFICATION_WARNING)
    return None


def logout() -> None:
    creds = Credentials.load()
    if not creds.is_logged_in:
        settings.notify(_text(30026))
        return
    if not xbmcgui.Dialog().yesno(settings.addon_name(), _text(30019) % creds.server_name):
        return

    transport = Http(settings.user_agent())
    auth.logout(transport, creds.server_address, creds.header())
    transport.close()

    Credentials.clear()
    settings.notify(_text(30020))
    LOG.info("signed out")
