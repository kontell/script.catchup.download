"""Add-on settings, and the credential record kept in hidden settings.

The record is plugin.video.kofin's (``kofin.core.settings.Credentials``):
the same setting ids, a device id minted once, and the address stored as a
sign-in normalised it.
"""

import uuid
from typing import Optional

import xbmc
import xbmcaddon
import xbmcgui

from catchup import auth, log

ADDON_ID = "script.catchup.download"


def get_addon() -> xbmcaddon.Addon:
    return xbmcaddon.Addon(ADDON_ID)


def get_str(setting_id: str) -> str:
    return get_addon().getSetting(setting_id)


def set_str(setting_id: str, value: str) -> None:
    get_addon().setSetting(setting_id, value)


def get_int(setting_id: str) -> int:
    try:
        return get_addon().getSettingInt(setting_id)
    except (RuntimeError, TypeError):
        return 0


def set_bool(setting_id: str, value: bool) -> None:
    get_addon().setSettingBool(setting_id, value)


def localized(string_id: int) -> str:
    return get_addon().getLocalizedString(string_id)


def addon_name() -> str:
    return str(get_addon().getAddonInfo("name"))


def addon_version() -> str:
    return str(get_addon().getAddonInfo("version"))


def device_name() -> str:
    """Kodi's own friendly name, as Kofin and pvr.kofin name the device."""
    return xbmc.getInfoLabel("System.FriendlyName") or "Kodi"


def user_agent() -> str:
    return xbmc.getUserAgent()


def notify(message: str, icon: str = xbmcgui.NOTIFICATION_INFO, time_ms: int = 5000) -> None:
    xbmcgui.Dialog().notification(addon_name(), message, icon, time_ms)


class Credentials:
    """The hidden-settings credential record for the single server."""

    def __init__(
        self,
        server_address: str = "",
        server_name: str = "",
        server_id: str = "",
        user_id: str = "",
        display_user: str = "",
        token: str = "",
        device_id: str = "",
        is_logged_in: bool = False,
    ) -> None:
        self.server_address = server_address
        self.server_name = server_name
        self.server_id = server_id
        self.user_id = user_id
        self.display_user = display_user
        self.token = token
        self.device_id = device_id
        self.is_logged_in = is_logged_in

    @classmethod
    def load(cls) -> "Credentials":
        addon = get_addon()
        stored_address = addon.getSetting("serverAddress")
        try:
            server_address = auth.normalize_address(stored_address)
        except ValueError:
            server_address = stored_address
        creds = cls(
            server_address=server_address,
            server_name=addon.getSetting("serverName"),
            server_id=addon.getSetting("serverId"),
            user_id=addon.getSetting("userId"),
            display_user=addon.getSetting("displayUser"),
            token=addon.getSetting("accessToken"),
            device_id=addon.getSetting("deviceId"),
            is_logged_in=addon.getSettingBool("isLoggedIn"),
        )
        if creds.server_address != stored_address:
            set_str("serverAddress", creds.server_address)
        if not creds.device_id:
            creds.device_id = uuid.uuid4().hex
            set_str("deviceId", creds.device_id)
        log.register_secret(creds.token)
        return creds

    def save(self) -> None:
        set_str("serverAddress", self.server_address)
        set_str("serverName", self.server_name)
        set_str("serverId", self.server_id)
        set_str("userId", self.user_id)
        set_str("displayUser", self.display_user)
        set_str("accessToken", self.token)
        set_str("deviceId", self.device_id)
        set_bool("isLoggedIn", self.is_logged_in)
        log.register_secret(self.token)

    def header(self) -> str:
        return auth.build_auth_header(
            device_name(), self.device_id, addon_version(), self.token
        )

    @classmethod
    def clear(cls) -> None:
        """Log out: drop the session, keep the server address and device id."""
        for setting_id in ("serverName", "serverId", "userId", "displayUser", "accessToken"):
            set_str(setting_id, "")
        set_bool("isLoggedIn", False)


def open_settings() -> None:
    xbmc.executebuiltin("Addon.OpenSettings(%s)" % ADDON_ID)


def credentials_or_none() -> Optional[Credentials]:
    creds = Credentials.load()
    return creds if creds.is_logged_in and creds.token else None
