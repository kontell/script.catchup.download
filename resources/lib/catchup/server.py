"""Comseg's catchup endpoints on the Jellyfin server."""

from typing import Any

from catchup import settings
from catchup.http import Http
from catchup.settings import Credentials

PATH = "/Comseg/Catchup"


def _call(creds: Credentials, method: str, path: str, body: Any = None) -> Any:
    transport = Http(settings.user_agent())
    try:
        response = transport.request(
            method,
            creds.server_address + path,
            headers={"Authorization": creds.header()},
            json_body=body,
            retries=0 if method == "POST" else 1,
        )
        return response.json()
    finally:
        transport.close()


def queue(creds: Credentials, request: dict[str, Any]) -> dict[str, Any]:
    """Queue a programme; the job comes back. Raises HttpError with the server's reason."""
    job: dict[str, Any] = _call(creds, "POST", PATH, request)
    return job


def jobs(creds: Credentials) -> list[dict[str, Any]]:
    answer = _call(creds, "GET", PATH)
    return answer if isinstance(answer, list) else []


def cancel(creds: Credentials, job_id: str) -> None:
    _call(creds, "DELETE", "%s/%s" % (PATH, job_id))
