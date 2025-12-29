# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""API client for Radarr, Sonarr, and Lidarr (/api/v3)."""

from typing import Any

from pydantic import BaseModel, Field

from charmarr_lib.core._arr._base_client import RESPONSE_MODEL_CONFIG, BaseArrApiClient


class DownloadClientResponse(BaseModel):
    """Download client response from *arr API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: int
    name: str
    enable: bool
    protocol: str
    implementation: str


class RootFolderResponse(BaseModel):
    """Root folder response from *arr API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: int
    path: str
    accessible: bool


class QualityProfileResponse(BaseModel):
    """Quality profile response from *arr API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: int
    name: str


class HostConfigResponse(BaseModel):
    """Host configuration response from *arr API."""

    model_config = RESPONSE_MODEL_CONFIG

    id: int
    bind_address: str = Field(alias="bindAddress")
    port: int
    url_base: str | None = Field(default=None, alias="urlBase")


class ArrApiClient(BaseArrApiClient):
    """API client for Radarr, Sonarr, and Lidarr (/api/v3).

    Provides methods for managing download clients, root folders,
    quality profiles, and host configuration.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the v3 API client.

        Args:
            base_url: Base URL of the arr application (e.g., "http://localhost:7878")
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            api_version="v3",
            timeout=timeout,
            max_retries=max_retries,
        )

    # Download Clients

    def get_download_clients(self) -> list[DownloadClientResponse]:
        """Get all configured download clients."""
        return self._get_validated_list("/downloadclient", DownloadClientResponse)

    def get_download_client(self, client_id: int) -> dict[str, Any]:
        """Get a download client by ID as raw dict.

        Args:
            client_id: ID of the download client
        """
        return self._get(f"/downloadclient/{client_id}")

    def add_download_client(self, config: dict[str, Any]) -> DownloadClientResponse:
        """Add a new download client.

        Args:
            config: Download client configuration payload
        """
        return self._post_validated("/downloadclient", config, DownloadClientResponse)

    def update_download_client(
        self, client_id: int, config: dict[str, Any]
    ) -> DownloadClientResponse:
        """Update an existing download client.

        Args:
            client_id: ID of the download client to update
            config: Updated download client configuration
        """
        config_with_id = {**config, "id": client_id}
        return self._put_validated(
            f"/downloadclient/{client_id}", config_with_id, DownloadClientResponse
        )

    def delete_download_client(self, client_id: int) -> None:
        """Delete a download client.

        Args:
            client_id: ID of the download client to delete
        """
        self._delete(f"/downloadclient/{client_id}")

    # Root Folders

    def get_root_folders(self) -> list[RootFolderResponse]:
        """Get all configured root folders."""
        return self._get_validated_list("/rootfolder", RootFolderResponse)

    def add_root_folder(self, path: str) -> RootFolderResponse:
        """Add a new root folder.

        Args:
            path: Filesystem path for the root folder
        """
        return self._post_validated("/rootfolder", {"path": path}, RootFolderResponse)

    # Quality Profiles (read-only for media-manager relation)

    def get_quality_profiles(self) -> list[QualityProfileResponse]:
        """Get all configured quality profiles."""
        return self._get_validated_list("/qualityprofile", QualityProfileResponse)

    # Host Config (get_host_config_raw and update_host_config are in BaseArrApiClient)

    def get_host_config(self) -> HostConfigResponse:
        """Get host configuration with typed response."""
        return self._get_validated("/config/host", HostConfigResponse)
