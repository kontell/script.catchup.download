"""A small HTTP client over the standard library, with Kofin's error taxonomy.

Kofin's plugin process talks to the server over ``http.client`` rather than
``requests`` because the import costs about a second in Kodi's Python; this
add-on runs as a fresh script on every click, so it does the same, and
depends on nothing outside Python.
"""

import json
import socket
import urllib.error
import urllib.request
from typing import Any, Optional
from urllib.parse import urlencode

DEFAULT_TIMEOUT = 15.0


class JellyfinError(Exception):
    """Any failure talking to the server."""


class ServerUnreachable(JellyfinError):
    """No answer: refused, timed out, no route, a name that does not resolve."""


class HttpError(JellyfinError):
    """The server answered with an error status."""

    def __init__(self, status_code: int, message: str, body: bytes = b"") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body

    def json(self) -> Any:
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None


class Unauthorized(HttpError):
    """401: the session or the credentials were refused."""


class Response:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def json(self) -> Any:
        if not self.content:
            return None
        return json.loads(self.content.decode("utf-8"))


class Http:
    def __init__(self, user_agent: str = "") -> None:
        self.user_agent = user_agent

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        json_body: Any = None,
        timeout: Any = DEFAULT_TIMEOUT,
        retries: int = 1,
    ) -> Response:
        if params:
            url = url + ("&" if "?" in url else "?") + urlencode(params)
        data = None
        all_headers = {"Accept": "application/json"}
        if self.user_agent:
            all_headers["User-Agent"] = self.user_agent
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            all_headers["Content-Type"] = "application/json"
        all_headers.update(headers or {})
        # A (connect, read) pair, as requests takes it: urllib has one timeout.
        seconds = float(max(timeout)) if isinstance(timeout, tuple) else float(timeout)

        attempt = 0
        while True:
            request = urllib.request.Request(
                url, data=data, headers=all_headers, method=method
            )
            try:
                with urllib.request.urlopen(request, timeout=seconds) as response:
                    return Response(response.status, response.read())
            except urllib.error.HTTPError as error:
                body = error.read() if error.fp is not None else b""
                message = "%s %s -> %d" % (method, url.split("?", 1)[0], error.code)
                if error.code == 401:
                    raise Unauthorized(error.code, message, body) from None
                raise HttpError(error.code, message, body) from None
            except (urllib.error.URLError, socket.timeout, ConnectionError) as error:
                if attempt >= retries:
                    raise ServerUnreachable(str(error)) from None
                attempt += 1

    def close(self) -> None:
        pass
