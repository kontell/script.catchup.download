"""Logging to kodi.log, with the session token kept out.

Importable without Kodi so the unit tests can load the modules that log.
"""

from typing import Any

try:
    import xbmc

    _LEVELS = {
        "debug": xbmc.LOGDEBUG,
        "info": xbmc.LOGINFO,
        "warning": xbmc.LOGWARNING,
        "error": xbmc.LOGERROR,
    }
except ImportError:  # pragma: no cover - outside Kodi
    xbmc = None
    _LEVELS = {}

PREFIX = "[script.catchup.download]"
_SECRETS: set[str] = set()


def register_secret(value: str) -> None:
    """Never write ``value`` to the log."""
    if value and len(value) >= 6:
        _SECRETS.add(value)


def _redact(text: str) -> str:
    for secret in _SECRETS:
        text = text.replace(secret, "<redacted>")
    return text


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name.rsplit(".", 1)[-1]

    def _log(self, level: str, message: str, args: tuple[Any, ...]) -> None:
        if xbmc is None:
            return
        try:
            text = message % args if args else message
        except (TypeError, ValueError):
            text = "%s %r" % (message, args)
        xbmc.log("%s %s: %s" % (PREFIX, self.name, _redact(text)), _LEVELS[level])

    def debug(self, message: str, *args: Any) -> None:
        self._log("debug", message, args)

    def info(self, message: str, *args: Any) -> None:
        self._log("info", message, args)

    def warning(self, message: str, *args: Any) -> None:
        self._log("warning", message, args)

    def error(self, message: str, *args: Any) -> None:
        self._log("error", message, args)
