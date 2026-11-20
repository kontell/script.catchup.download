"""The LAN server picker (Account settings button), ported from
plugin.video.kofin's ``kofin.plugin.serverpicker``.

Broadcasts Jellyfin's UDP discovery probe, verifies each answer over HTTP,
and writes the chosen address into ``serverAddress`` so Log in has something
to work with. The settings button carries ``<close>true</close>``, so Kodi
has saved and closed the dialog before this runs; it reopens it afterwards,
so the filled field is the confirmation and Log in is the next press.

The verification is not a liveness check: the address in question is the
one the server published, which Jellyfin derives per caller and which can
name a host this box cannot reach. When it does not answer, the datagram's
own source address is tried.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, NamedTuple, Optional, Union

import xbmc
import xbmcgui

from catchup import auth, discovery, settings
from catchup.http import Http, JellyfinError
from catchup.log import Logger
from catchup.settings import Credentials

LOG = Logger(__name__)

PROBE_WORKERS = 4
POLL_SECONDS = 0.1


class Candidate(NamedTuple):
    found: discovery.Found
    address: str
    info: Optional[dict[str, Any]]
    reachable: bool


def _text(string_id: int) -> str:
    return settings.localized(string_id)


def _addresses(found: discovery.Found) -> list[str]:
    addresses = [found.address] if discovery.may_probe(found) else []
    fallback = discovery.fallback_address(found)
    if fallback and fallback not in addresses:
        addresses.append(fallback)
    return addresses


def _verify(transport: Http, found: discovery.Found) -> Candidate:
    for address in _addresses(found):
        try:
            info = auth.probe_public_info(transport, address)
        except (JellyfinError, ValueError) as error:
            LOG.debug("discovery: %s unreachable at %s (%s)", found.name, address, error)
            continue
        return Candidate(found=found, address=address, info=info, reachable=True)
    return Candidate(found=found, address=found.address, info=None, reachable=False)


def _scan_with_progress(transport: Http) -> Optional[list[Candidate]]:
    """Run the broadcast window, verifying hits as they land. None means the
    user cancelled."""
    progress = xbmcgui.DialogProgress()
    progress.create(settings.addon_name(), _text(30827))
    monitor = xbmc.Monitor()
    arrivals: list[discovery.Found] = []
    probes: list[Future[Candidate]] = []
    cancelled = False

    try:
        with ThreadPoolExecutor(max_workers=PROBE_WORKERS + 1) as pool:
            scanning = pool.submit(discovery.scan, arrivals.append)
            elapsed = 0.0
            started_probes = 0
            while True:
                while started_probes < len(arrivals):
                    probes.append(pool.submit(_verify, transport, arrivals[started_probes]))
                    started_probes += 1
                if scanning.done():
                    break
                if progress.iscanceled():
                    cancelled = True
                    break
                elapsed += POLL_SECONDS
                progress.update(
                    min(99, int(elapsed * 100 / discovery.SCAN_SECONDS)), _text(30827)
                )
                if monitor.waitForAbort(POLL_SECONDS):
                    cancelled = True
                    break
            if cancelled:
                progress.close()
    finally:
        progress.close()

    failure = scanning.exception()
    if failure is not None:
        LOG.error("discovery scan failed: %s", failure)

    if cancelled:
        return None
    return [probe.result() for probe in probes]


def find_servers() -> None:
    """Find Jellyfin servers on the local network and fill in the address."""
    if Credentials.load().is_logged_in:
        return

    transport = Http(settings.user_agent())
    try:
        candidates = _scan_with_progress(transport)
    finally:
        transport.close()

    if candidates is None:
        return
    if not candidates:
        settings.notify(_text(30829), xbmcgui.NOTIFICATION_WARNING, 6000)
        return

    candidates.sort(key=lambda entry: (not entry.reachable, entry.found.name.lower()))
    items: list[Union[str, xbmcgui.ListItem]] = []
    for candidate in candidates:
        label, detail = discovery.label_for(candidate.found.name, candidate.address, candidate.info)
        if not candidate.reachable:
            detail = "%s · %s" % (detail, _text(30830))
        items.append(xbmcgui.ListItem(label, detail))

    choice = xbmcgui.Dialog().select(_text(30828), items, useDetails=True)
    if choice < 0:
        return

    picked = candidates[choice]
    settings.set_str("serverAddress", picked.address)
    LOG.info("discovery: server address set to %s", picked.address)
    if not picked.reachable:
        settings.notify(_text(30831) % picked.found.name, xbmcgui.NOTIFICATION_WARNING, 6000)
    settings.open_settings()
