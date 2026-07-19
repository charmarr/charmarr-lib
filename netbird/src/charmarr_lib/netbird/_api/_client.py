# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""NetBird Management REST API client."""

from __future__ import annotations

import logging
from typing import Any, Self

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from charmarr_lib.netbird.constants import (
    API_AUTH_SCHEME,
    API_BASE_PATH,
    NETWORK_ADMIN_ROLE,
)

logger = logging.getLogger(__name__)

# extra="allow" keeps parsing forward-compatible as the Management API grows fields.
RESPONSE_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class NetbirdApiError(Exception):
    """Base exception for Management API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NetbirdApiConnectionError(NetbirdApiError):
    """Raised when the connection to the Management API fails."""


class NetbirdApiResponseError(NetbirdApiError):
    """Raised when the Management API returns an error status."""


class SetupKeyResponse(BaseModel):
    """A setup key returned by the Management API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: str
    key: str = ""
    name: str = ""
    valid: bool = True
    revoked: bool = False


class ServiceUserResponse(BaseModel):
    """A service user returned by the Management API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: str
    name: str = ""
    role: str = ""
    is_service_user: bool = True


class TokenResponse(BaseModel):
    """A personal access token returned by the Management API.

    ``plain_token`` is only populated on creation and never again.
    """

    model_config = RESPONSE_MODEL_CONFIG

    id: str
    name: str = ""
    plain_token: str | None = None
    expiration_date: str | None = None


class NetbirdManagementClient:
    """Client for the NetBird Management REST API (`/api/*`, `Authorization: Token`)."""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Management base URL (e.g. "https://netbird.example.com")
            api_token: Personal access token for `Authorization: Token <pat>`
            timeout: Per-request timeout in seconds
            max_retries: Retries for transient connection/timeout failures
        """
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client with the auth header."""
        if self._client is None:
            self._client = httpx.Client(
                headers={"Authorization": f"{API_AUTH_SCHEME} {self._api_token}"},
                timeout=self._timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _url(self, endpoint: str) -> str:
        return f"{self._base_url}{API_BASE_PATH}/{endpoint.lstrip('/')}"

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = self._url(endpoint)

        @retry(
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _do_request() -> httpx.Response:
            response = self.client.request(method=method, url=url, json=json)
            response.raise_for_status()
            return response

        try:
            return _do_request()
        except httpx.ConnectError as e:
            raise NetbirdApiConnectionError(
                f"Failed to connect to {url} after {self._max_retries} attempts"
            ) from e
        except httpx.TimeoutException as e:
            raise NetbirdApiConnectionError(
                f"Request to {url} timed out after {self._max_retries} attempts"
            ) from e
        except httpx.HTTPStatusError as e:
            raise NetbirdApiResponseError(
                f"API request failed: {e.response.status_code} {e.response.reason_phrase}",
                status_code=e.response.status_code,
            ) from e

    def _get(self, endpoint: str) -> Any:
        return self._request("GET", endpoint).json()

    def _post(self, endpoint: str, json: dict[str, Any]) -> Any:
        return self._request("POST", endpoint, json=json).json()

    def _delete(self, endpoint: str) -> None:
        self._request("DELETE", endpoint)

    def list_setup_keys(self) -> list[SetupKeyResponse]:
        """List all setup keys."""
        return [SetupKeyResponse.model_validate(k) for k in self._get("/setup-keys")]

    def create_setup_key(
        self,
        name: str,
        *,
        key_type: str = "reusable",
        expires_in: int = 0,
        auto_groups: list[str] | None = None,
        ephemeral: bool = False,
    ) -> SetupKeyResponse:
        """Create a setup key.

        Args:
            name: Human-readable key name
            key_type: "reusable" or "one-off"
            expires_in: Lifetime in seconds; 0 means non-expiring
            auto_groups: Group IDs auto-assigned to peers using this key
            ephemeral: Whether peers registered with this key are ephemeral
        """
        payload: dict[str, Any] = {
            "name": name,
            "type": key_type,
            "expires_in": expires_in,
            "auto_groups": auto_groups or [],
            "ephemeral": ephemeral,
        }
        return SetupKeyResponse.model_validate(self._post("/setup-keys", payload))

    def list_users(self) -> list[ServiceUserResponse]:
        """List all users (includes service users)."""
        return [ServiceUserResponse.model_validate(u) for u in self._get("/users")]

    def create_service_user(
        self,
        name: str,
        *,
        role: str = NETWORK_ADMIN_ROLE,
        auto_groups: list[str] | None = None,
    ) -> ServiceUserResponse:
        """Create a service user (least-privilege role by default).

        Args:
            name: Service-user name
            role: Role to grant (defaults to network_admin)
            auto_groups: Group IDs auto-assigned to the user
        """
        payload: dict[str, Any] = {
            "name": name,
            "role": role,
            "is_service_user": True,
            "auto_groups": auto_groups or [],
        }
        return ServiceUserResponse.model_validate(self._post("/users", payload))

    def create_user_token(self, user_id: str, name: str, *, expires_in: int) -> TokenResponse:
        """Mint a personal access token for a user.

        The plaintext token is returned once, on `plain_token`.

        Args:
            user_id: Target user ID
            name: Token name
            expires_in: Lifetime in days (Management caps this at 365)
        """
        payload = {"name": name, "expires_in": expires_in}
        return TokenResponse.model_validate(self._post(f"/users/{user_id}/tokens", payload))
