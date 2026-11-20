"""The server's catchup downloads (settings button): a list, and cancel."""

from datetime import datetime, timezone
from typing import Any

import xbmcgui

from catchup import server, settings
from catchup.http import JellyfinError, Unauthorized

ENDED = {"Done", "Failed", "Cancelled"}


def _text(string_id: int) -> str:
    return settings.localized(string_id)


def _when(job: dict[str, Any]) -> str:
    try:
        start = datetime.strptime(job["Request"]["StartUtc"][:19], "%Y-%m-%dT%H:%M:%S")
    except (KeyError, TypeError, ValueError):
        return ""
    local = start.replace(tzinfo=timezone.utc).astimezone()
    return "%s %d %s" % (local.strftime("%a"), local.day, local.strftime("%b %H:%M"))


def label(job: dict[str, Any]) -> tuple[str, str]:
    title = (job.get("Request") or {}).get("Title") or "?"
    state = job.get("State") or "?"
    if state == "Downloading":
        state = "%s %d%%" % (state, job.get("Percent") or 0)
    detail = "%s · %s · %s" % (job.get("Channel") or "", _when(job), state)
    if job.get("Message"):
        detail += " — " + job["Message"]
    return title, detail


def show() -> None:
    creds = settings.credentials_or_none()
    if creds is None:
        settings.notify(_text(30105), xbmcgui.NOTIFICATION_WARNING)
        return
    try:
        jobs = server.jobs(creds)
    except Unauthorized:
        settings.notify(_text(30022), xbmcgui.NOTIFICATION_ERROR)
        return
    except JellyfinError as error:
        settings.notify(_text(30821) % error, xbmcgui.NOTIFICATION_ERROR)
        return
    if not jobs:
        settings.notify(_text(30129))
        return

    items = [xbmcgui.ListItem(*label(job)) for job in jobs]
    choice = xbmcgui.Dialog().select(_text(30128), items, useDetails=True)
    if choice < 0:
        return
    job = jobs[choice]
    if job.get("State") in ENDED:
        return
    title = (job.get("Request") or {}).get("Title") or "?"
    if xbmcgui.Dialog().yesno(_text(30128), _text(30130) % title):
        try:
            server.cancel(creds, job["Id"])
        except JellyfinError as error:
            settings.notify(_text(30821) % error, xbmcgui.NOTIFICATION_ERROR)
            return
        settings.notify(_text(30131))
