"""A guide programme, read from Kodi, turned into the server's request.

Kodi-free so it can be tested. Kodi gives a guide item the path
``pvr://guide/<epg id>/<start>.epg`` and its JSON-RPC answers ``starttime``
and ``endtime`` as ``YYYY-MM-DD HH:MM:SS``; all three are UTC
(``CPVREpgInfoTag`` keeps its times in UTC and writes them with
``GetAsDBDateTime``).
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import unquote

_GUIDE_PATH = re.compile(r"^pvr://guide/\d+/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\.epg$")


def parse_db_time(text: str) -> Optional[datetime]:
    """'2026-11-14 13:40:00' (UTC) -> an aware datetime, or None."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None


def guide_start(path: str) -> Optional[datetime]:
    """The programme's start from a guide item's path, or None for any other path."""
    match = _GUIDE_PATH.match(path or "")
    return parse_db_time(match.group(1)) if match else None


def image_url(thumbnail: str) -> Optional[str]:
    """The http(s) URL inside Kodi's ``image://<encoded url>/`` wrapper, or None.

    A local file or a ``special://`` path means nothing to the server, so only
    a web address is passed on.
    """
    if not thumbnail:
        return None
    url = thumbnail
    if url.startswith("image://"):
        url = unquote(url[len("image://"):].rstrip("/"))
    return url if url.startswith(("http://", "https://")) else None


def find_channel(channels: list[dict[str, Any]], name: str, number: str) -> Optional[dict[str, Any]]:
    """The JSON-RPC channel the guide item belongs to: by name, then number."""
    by_name = [c for c in channels if (c.get("label") or "").strip().lower() == (name or "").strip().lower()]
    if len(by_name) == 1:
        return by_name[0]
    pool = by_name or channels
    by_number = [c for c in pool if _channel_number(c) == (number or "").strip()]
    return by_number[0] if len(by_number) == 1 else None


def _channel_number(channel: dict[str, Any]) -> str:
    number = channel.get("channelnumber")
    sub = channel.get("subchannelnumber")
    if number is None:
        return ""
    return "%s.%s" % (number, sub) if sub else str(number)


def find_broadcast(broadcasts: list[dict[str, Any]], start: datetime) -> Optional[dict[str, Any]]:
    """The broadcast that starts at ``start``."""
    for broadcast in broadcasts:
        if parse_db_time(broadcast.get("starttime", "")) == start:
            return broadcast
    return None


def build_request(
    channel_name: str,
    channel_number: str,
    broadcast: dict[str, Any],
    pad_before_minutes: int = 0,
    pad_after_minutes: int = 0,
) -> Optional[dict[str, Any]]:
    """The body of ``POST /Comseg/Catchup``, or None when the broadcast lacks its times."""
    start = parse_db_time(broadcast.get("starttime", ""))
    end = parse_db_time(broadcast.get("endtime", ""))
    if start is None or end is None or end <= start:
        return None
    start -= timedelta(minutes=max(0, pad_before_minutes))
    end += timedelta(minutes=max(0, pad_after_minutes))
    return {
        "ChannelName": channel_name,
        "ChannelNumber": channel_number,
        "StartUtc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "EndUtc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Title": broadcast.get("title") or broadcast.get("label") or "",
        "Plot": broadcast.get("plot") or broadcast.get("plotoutline") or "",
        "ImageUrl": image_url(broadcast.get("thumbnail") or ""),
    }


def has_finished(request: dict[str, Any], now: Optional[datetime] = None) -> bool:
    end = datetime.strptime(request["EndUtc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return end <= (now or datetime.now(timezone.utc))


def describe(request: dict[str, Any]) -> str:
    """'Sat 14 Nov 13:40 – 16:30' in this box's local time."""
    start = datetime.strptime(request["StartUtc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone()
    end = datetime.strptime(request["EndUtc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone()
    return "%s %d %s – %s" % (
        start.strftime("%a"),
        start.day,
        start.strftime("%b %H:%M"),
        end.strftime("%H:%M"),
    )
