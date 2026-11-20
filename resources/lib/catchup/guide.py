"""The "Save to recordings" context item on a guide programme."""

import json
from typing import Any, Optional

import xbmc
import xbmcgui

from catchup import programme, server, settings
from catchup.http import HttpError, JellyfinError, ServerUnreachable, Unauthorized
from catchup.log import Logger

LOG = Logger(__name__)


def _text(string_id: int) -> str:
    return settings.localized(string_id)


def _rpc(method: str, params: dict[str, Any]) -> Any:
    answer = json.loads(
        xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}))
    )
    if "error" in answer:
        raise RuntimeError("%s: %s" % (method, answer["error"]))
    return answer.get("result") or {}


def read_programme(item: Optional[xbmcgui.ListItem]) -> Optional[dict[str, Any]]:
    """The server request for the focused guide programme, or None.

    The guide item's path carries the start; the channel's name and number
    come from its labels; JSON-RPC supplies the rest (end, title,
    description, image) from the same broadcast.
    """
    path = (item.getPath() if item is not None else "") or xbmc.getInfoLabel("ListItem.FileNameAndPath")
    start = programme.guide_start(path)
    name = xbmc.getInfoLabel("ListItem.ChannelName")
    number = xbmc.getInfoLabel("ListItem.ChannelNumberLabel")
    if start is None or not name:
        LOG.warning("not a guide programme: path %r, channel %r", path, name)
        return None

    for group in ("alltv", "allradio"):
        channels = _rpc(
            "PVR.GetChannels",
            {"channelgroupid": group, "properties": ["channelnumber", "subchannelnumber"]},
        ).get("channels", [])
        channel = programme.find_channel(channels, name, number)
        if channel is None:
            continue
        broadcasts = _rpc(
            "PVR.GetBroadcasts",
            {
                "channelid": channel["channelid"],
                "properties": ["title", "plot", "plotoutline", "starttime", "endtime", "thumbnail"],
            },
        ).get("broadcasts", [])
        broadcast = programme.find_broadcast(broadcasts, start)
        if broadcast is None:
            continue
        return programme.build_request(
            name,
            number,
            broadcast,
            settings.get_int("padBeforeMinutes"),
            settings.get_int("padAfterMinutes"),
        )

    LOG.warning("no broadcast of %s starts at %s", name, start)
    return None


def save(item: Optional[xbmcgui.ListItem]) -> None:
    try:
        request = read_programme(item)
    except RuntimeError as error:
        LOG.error("reading the programme failed: %s", error)
        request = None
    if request is None:
        settings.notify(_text(30104), xbmcgui.NOTIFICATION_ERROR)
        return
    if not programme.has_finished(request):
        settings.notify(_text(30103), xbmcgui.NOTIFICATION_WARNING)
        return

    creds = settings.credentials_or_none()
    if creds is None:
        settings.notify(_text(30105), xbmcgui.NOTIFICATION_WARNING)
        settings.open_settings()
        return

    message = "[B]%s[/B][CR]%s, %s[CR]%s" % (
        request["Title"],
        request["ChannelName"],
        programme.describe(request),
        _text(30101),
    )
    if not xbmcgui.Dialog().yesno(_text(30100), message):
        return

    try:
        job = server.queue(creds, request)
    except Unauthorized:
        settings.notify(_text(30022), xbmcgui.NOTIFICATION_ERROR)
        return
    except HttpError as error:
        settings.notify(_refusal(error, request["Title"]), xbmcgui.NOTIFICATION_ERROR, 8000)
        return
    except ServerUnreachable:
        settings.notify(_text(30018), xbmcgui.NOTIFICATION_ERROR)
        return
    except JellyfinError as error:
        settings.notify(_text(30821) % error, xbmcgui.NOTIFICATION_ERROR)
        return

    LOG.info("queued %s on %s (%s)", request["Title"], request["ChannelName"], (job or {}).get("Id"))
    settings.notify(_text(30102) % request["Title"])


def _refusal(error: HttpError, title: str) -> str:
    body = error.json()
    reason = body.get("Message") if isinstance(body, dict) else None
    if error.status_code == 409:
        return _text(30109) % title
    if error.status_code == 403:
        return _text(30108)
    if error.status_code == 404 and not reason:
        return _text(30107)
    if error.status_code == 503:
        return _text(30107)
    return _text(30106) % (reason or error)
