# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""API client for Prowlarr (/api/v1)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from charmarr_lib.core._arr._base_client import BaseArrApiClient

# Response models use extra="allow" to accept unknown fields from the API.
# This ensures forward compatibility when Prowlarr adds new fields, while
# still providing type safety for the fields we actually use.
# populate_by_name allows using both the alias (camelCase) and field name (snake_case).
_RESPONSE_MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True)


class ApplicationResponse(BaseModel):
    """Application response from Prowlarr API."""

    model_config = _RESPONSE_MODEL_CONFIG

    id: int
    name: str
    sync_level: str = Field(alias="syncLevel")
    implementation: str
    config_contract: str = Field(alias="configContract")


class IndexerResponse(BaseModel):
    """Indexer response from Prowlarr API."""

    model_config = _RESPONSE_MODEL_CONFIG

    id: int
    name: str
    enable: bool
    protocol: str
    implementation: str


class ProwlarrHostConfigResponse(BaseModel):
    """Host configuration response from Prowlarr API."""

    model_config = _RESPONSE_MODEL_CONFIG

    id: int
    bind_address: str = Field(alias="bindAddress")
    port: int
    url_base: str | None = Field(default=None, alias="urlBase")


class ProwlarrApiClient(BaseArrApiClient):
    """API client for Prowlarr (/api/v1).

    Provides methods for managing applications (connections to media managers),
    indexers, and host configuration.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the v1 API client.

        Args:
            base_url: Base URL of Prowlarr (e.g., "http://localhost:9696")
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            api_version="v1",
            timeout=timeout,
            max_retries=max_retries,
        )

    # Applications

    def get_applications(self) -> list[ApplicationResponse]:
        """Get all configured applications (media manager connections)."""
        return self._get_validated_list("/application", ApplicationResponse)

    def get_application(self, app_id: int) -> dict[str, Any]:
        """Get a single application by ID as raw dict.

        Returns the full API response including the fields array,
        useful for comparing against desired configuration.

        Args:
            app_id: ID of the application
        """
        return self._get(f"/application/{app_id}")

    def add_application(self, config: dict[str, Any]) -> ApplicationResponse:
        """Add a new application.

        Args:
            config: Application configuration payload
        """
        return self._post_validated("/application", config, ApplicationResponse)

    def update_application(
        self, app_id: int, config: dict[str, Any]
    ) -> ApplicationResponse:
        """Update an existing application.

        Args:
            app_id: ID of the application to update
            config: Updated application configuration
        """
        config_with_id = {**config, "id": app_id}
        return self._put_validated(
            f"/application/{app_id}", config_with_id, ApplicationResponse
        )

    def delete_application(self, app_id: int) -> None:
        """Delete an application.

        Args:
            app_id: ID of the application to delete
        """
        self._delete(f"/application/{app_id}")

    # Indexers (read-only, user manages via UI)

    def get_indexers(self) -> list[IndexerResponse]:
        """Get all configured indexers."""
        return self._get_validated_list("/indexer", IndexerResponse)

    # Host Config

    def get_host_config(self) -> ProwlarrHostConfigResponse:
        """Get host configuration."""
        return self._get_validated("/config/host", ProwlarrHostConfigResponse)

    def get_host_config_raw(self) -> dict[str, Any]:
        """Get host configuration as raw dict.

        Returns the full API response, useful for comparing against
        desired configuration or merging updates.
        """
        return self._get("/config/host")

    def update_host_config(self, config: dict[str, Any]) -> ProwlarrHostConfigResponse:
        """Update host configuration.

        Merges provided config with current settings.

        Args:
            config: Host configuration settings to update
        """
        current = self._get("/config/host")
        updated = {**current, **config}
        return self._put_validated("/config/host", updated, ProwlarrHostConfigResponse)
