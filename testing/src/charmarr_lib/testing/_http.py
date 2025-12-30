# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""HTTP request helpers for integration testing."""

import json
import logging
from typing import Any

import jubilant
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class HttpResponse(BaseModel):
    """HTTP response from multimeter http-request action."""

    status_code: int
    body: str
    cookies: dict[str, str]

    def json_body(self) -> Any:
        """Parse body as JSON."""
        return json.loads(self.body)


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


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _exec_curl(
    juju: jubilant.Juju,
    unit: str,
    url: str,
    header_args: list[str],
    timeout: int,
) -> str:
    """Execute curl command in unit with retry."""
    result = juju.exec(
        "curl",
        "-s",
        "-w",
        r"\n%{http_code}",
        "--max-time",
        str(timeout),
        *header_args,
        url,
        unit=unit,
    )
    return result.stdout


def http_from_unit(
    juju: jubilant.Juju,
    unit: str,
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> HttpResponse:
    """Make HTTP GET request using curl from inside a unit.

    Args:
        juju: Juju instance.
        unit: Unit name to exec curl from (e.g. "prowlarr/0").
        url: Target URL.
        headers: Optional headers dict.
        timeout: Request timeout in seconds.

    Returns:
        HttpResponse with status_code, body, and empty cookies.

    Raises:
        RuntimeError: If the request fails.
    """
    header_args: list[str] = []
    if headers:
        for key, value in headers.items():
            header_args.extend(["-H", f"{key}: {value}"])

    try:
        output = _exec_curl(juju, unit, url, header_args, timeout)

        lines = output.rsplit("\n", 1)
        if len(lines) == 2:
            body, status_code_str = lines
        else:
            body = output
            status_code_str = "0"

        return HttpResponse(
            status_code=int(status_code_str),
            body=body,
            cookies={},
        )
    except Exception as e:
        raise RuntimeError(f"HTTP request from {unit} failed: {e}") from e
