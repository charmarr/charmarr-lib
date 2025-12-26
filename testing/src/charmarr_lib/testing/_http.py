# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""HTTP request helpers using multimeter action."""

import json
import logging

import jubilant
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HttpResponse(BaseModel):
    """HTTP response from multimeter http-request action."""

    status_code: int
    body: str
    cookies: dict[str, str]


def http_request(
    juju: jubilant.Juju,
    url: str,
    method: str = "GET",
    basic_auth: tuple[str, str] | None = None,
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: int = 10,
) -> HttpResponse:
    """Make HTTP request from within the cluster via multimeter action.

    Args:
        juju: Juju instance.
        url: Target URL (must be reachable from within the cluster).
        method: HTTP method (GET, POST, PUT, DELETE).
        basic_auth: Optional (username, password) tuple for Basic Auth.
        headers: Optional headers dict.
        body: Optional request body.
        timeout: Request timeout in seconds.

    Returns:
        HttpResponse with status_code, body, and cookies.

    Raises:
        RuntimeError: If the request fails.
    """
    params: dict[str, str | int] = {
        "url": url,
        "method": method,
        "timeout": timeout,
    }

    if basic_auth:
        params["basic-auth"] = f"{basic_auth[0]}:{basic_auth[1]}"

    if headers:
        params["headers"] = json.dumps(headers)

    if body:
        params["body"] = body

    try:
        result = juju.run("charmarr-multimeter/0", "http-request", params)
        cookies_str = result.results.get("cookies", "")
        cookies = json.loads(cookies_str) if cookies_str else {}
        return HttpResponse(
            status_code=int(result.results["status-code"]),
            body=result.results.get("body", ""),
            cookies=cookies,
        )
    except Exception as e:
        raise RuntimeError(f"HTTP request failed: {e}") from e
