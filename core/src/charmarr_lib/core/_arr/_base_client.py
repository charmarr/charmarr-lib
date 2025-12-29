# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Base API client for *arr applications."""

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

logger = logging.getLogger(__name__)

# Response models use extra="allow" to accept unknown fields from the API.
# This ensures forward compatibility when *arr APIs add new fields, while
# still providing type safety for the fields we actually use.
RESPONSE_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class ArrApiError(Exception):
    """Base exception for arr API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ArrApiConnectionError(ArrApiError):
    """Raised when connection to the API fails."""


class ArrApiResponseError(ArrApiError):
    """Raised when the API returns an error response."""


class BaseArrApiClient:
    """Shared HTTP mechanics for all arr applications.

    Provides common HTTP patterns for interacting with *arr application APIs.
    Handles session management, API key authentication, and error handling
    with exponential backoff retries for transient failures.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_version: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the API client.

        Args:
            base_url: Base URL of the arr application (e.g., "http://localhost:7878")
            api_key: API key for authentication
            api_version: API version string (e.g., "v3" for Radarr, "v1" for Prowlarr)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._api_version = api_version
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create the HTTP client with configured headers."""
        if self._client is None:
            self._client = httpx.Client(
                headers={"X-Api-Key": self._api_key},
                timeout=self._timeout,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close client."""
        self.close()

    def _url(self, endpoint: str) -> str:
        """Build full URL for an API endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/downloadclient")

        Returns:
            Full URL including base URL and API version prefix
        """
        endpoint = endpoint.lstrip("/")
        return f"{self._base_url}/api/{self._api_version}/{endpoint}"

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            json: JSON body for POST/PUT requests
            params: Query parameters

        Returns:
            HTTP response object

        Raises:
            ArrApiConnectionError: If connection fails after all retries
            ArrApiResponseError: If the API returns an error response
        """
        url = self._url(endpoint)

        @retry(
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _do_request() -> httpx.Response:
            response = self.client.request(
                method=method,
                url=url,
                json=json,
                params=params,
            )
            response.raise_for_status()
            return response

        try:
            return _do_request()
        except httpx.ConnectError as e:
            raise ArrApiConnectionError(
                f"Failed to connect to {url} after {self._max_retries} attempts"
            ) from e
        except httpx.TimeoutException as e:
            raise ArrApiConnectionError(
                f"Request to {url} timed out after {self._max_retries} attempts"
            ) from e
        except httpx.HTTPStatusError as e:
            raise ArrApiResponseError(
                f"API request failed: {e.response.status_code} {e.response.reason_phrase}",
                status_code=e.response.status_code,
            ) from e

    def _get(self, endpoint: str, *, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request and return JSON response.

        Args:
            endpoint: API endpoint path
            params: Optional query parameters

        Returns:
            Parsed JSON response (dict or list)
        """
        response = self._request("GET", endpoint, params=params)
        return response.json()

    def _post(self, endpoint: str, json: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request and return JSON response.

        Args:
            endpoint: API endpoint path
            json: JSON body to send

        Returns:
            Parsed JSON response
        """
        response = self._request("POST", endpoint, json=json)
        return response.json()

    def _put(self, endpoint: str, json: dict[str, Any]) -> dict[str, Any]:
        """Make a PUT request and return JSON response.

        Args:
            endpoint: API endpoint path
            json: JSON body to send

        Returns:
            Parsed JSON response
        """
        response = self._request("PUT", endpoint, json=json)
        return response.json()

    def _delete(self, endpoint: str) -> None:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint path
        """
        self._request("DELETE", endpoint)

    def _get_validated[ModelT: BaseModel](
        self,
        endpoint: str,
        response_model: type[ModelT],
        *,
        params: dict[str, Any] | None = None,
    ) -> ModelT:
        """Make a GET request and validate response against a Pydantic model.

        Args:
            endpoint: API endpoint path
            response_model: Pydantic model class to validate against
            params: Optional query parameters

        Returns:
            Validated Pydantic model instance
        """
        data = self._get(endpoint, params=params)
        return response_model.model_validate(data)

    def _get_validated_list[ModelT: BaseModel](
        self,
        endpoint: str,
        item_model: type[ModelT],
        *,
        params: dict[str, Any] | None = None,
    ) -> list[ModelT]:
        """Make a GET request and validate response as a list of Pydantic models.

        Args:
            endpoint: API endpoint path
            item_model: Pydantic model class for list items
            params: Optional query parameters

        Returns:
            List of validated Pydantic model instances
        """
        data = self._get(endpoint, params=params)
        return [item_model.model_validate(item) for item in data]

    def _post_validated[ModelT: BaseModel](
        self,
        endpoint: str,
        json: dict[str, Any],
        response_model: type[ModelT],
    ) -> ModelT:
        """Make a POST request and validate response against a Pydantic model.

        Args:
            endpoint: API endpoint path
            json: JSON body to send
            response_model: Pydantic model class to validate against

        Returns:
            Validated Pydantic model instance
        """
        data = self._post(endpoint, json)
        return response_model.model_validate(data)

    def _put_validated[ModelT: BaseModel](
        self,
        endpoint: str,
        json: dict[str, Any],
        response_model: type[ModelT],
    ) -> ModelT:
        """Make a PUT request and validate response against a Pydantic model.

        Args:
            endpoint: API endpoint path
            json: JSON body to send
            response_model: Pydantic model class to validate against

        Returns:
            Validated Pydantic model instance
        """
        data = self._put(endpoint, json)
        return response_model.model_validate(data)

    def get_host_config_raw(self) -> dict[str, Any]:
        """Get host configuration as raw dict.

        All *arr applications have a /config/host endpoint that returns
        settings like bindAddress, port, urlBase, and applicationUrl.
        """
        return self._get("/config/host")

    def update_host_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update host configuration.

        Merges provided config with current settings and PUTs the result.

        Args:
            config: Host configuration settings to update

        Returns:
            Updated host configuration
        """
        current = self._get("/config/host")
        updated = {**current, **config}
        return self._put("/config/host", updated)
