# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Reconcilers for synchronizing *arr application state with Juju relations."""

import logging
from typing import Any, Protocol

from pydantic import ValidationError

from charmarr_lib.core._arr._arr_client import ArrApiClient
from charmarr_lib.core._arr._base_client import ArrApiError, BaseArrApiClient
from charmarr_lib.core._arr._config_builders import (
    ApplicationConfigBuilder,
    DownloadClientConfigBuilder,
    SecretGetter,
)
from charmarr_lib.core._arr._protocols import MediaIndexerClient
from charmarr_lib.core.enums import MediaManager
from charmarr_lib.core.interfaces import (
    DownloadClientProviderData,
    MediaIndexerRequirerData,
)

logger = logging.getLogger(__name__)


class NamedItem(Protocol):
    """Protocol for items with id and name attributes."""

    @property
    def id(self) -> int: ...

    @property
    def name(self) -> str: ...


class ReconcileOperations[T: NamedItem](Protocol):
    """Protocol defining operations needed for generic reconciliation."""

    def get_current(self) -> list[T]: ...
    def get_full(self, item_id: int) -> dict[str, Any]: ...
    def delete(self, item_id: int) -> None: ...
    def add(self, config: dict[str, Any]) -> Any: ...
    def update(self, item_id: int, config: dict[str, Any]) -> Any: ...


def _extract_field_value(fields: list[dict[str, Any]], field_name: str) -> Any:
    """Extract a field value from *arr API fields array."""
    for field in fields:
        if field.get("name") == field_name:
            return field.get("value")
    return None


def _needs_config_update(
    existing: dict[str, Any],
    desired: dict[str, Any],
    top_level_keys: list[str],
) -> bool:
    """Check if *arr config needs to be updated by comparing top-level keys and fields."""
    for key in top_level_keys:
        if existing.get(key) != desired.get(key):
            return True

    existing_fields = existing.get("fields", [])
    desired_fields = desired.get("fields", [])
    desired_field_values = {f["name"]: f.get("value") for f in desired_fields}

    for field_name, desired_value in desired_field_values.items():
        existing_value = _extract_field_value(existing_fields, field_name)
        if existing_value != desired_value:
            return True

    return False


_DOWNLOAD_CLIENT_KEYS = ["enable", "protocol", "implementation", "configContract"]
_APPLICATION_KEYS = ["syncLevel", "implementation", "configContract"]


def _reconcile_items[T: NamedItem](
    ops: ReconcileOperations[T],
    desired_configs: dict[str, dict[str, Any]],
    comparison_keys: list[str],
    item_type_name: str,
) -> None:
    """Generic reconciliation of *arr API items.

    Args:
        ops: Operations for interacting with the API
        desired_configs: Mapping of item name to desired configuration
        comparison_keys: Top-level keys to compare for update detection
        item_type_name: Human-readable name for logging (e.g., "download client")
    """
    current = ops.get_current()
    current_by_name = {item.name: item for item in current}

    for name, current_item in current_by_name.items():
        if name not in desired_configs:
            logger.info("Removing %s: %s", item_type_name, name)
            ops.delete(current_item.id)

    for name, desired_config in desired_configs.items():
        try:
            existing = current_by_name.get(name)
            if existing:
                existing_full = ops.get_full(existing.id)
                if _needs_config_update(existing_full, desired_config, comparison_keys):
                    logger.info("Updating %s: %s", item_type_name, name)
                    ops.update(existing.id, desired_config)
            else:
                logger.info("Adding %s: %s", item_type_name, name)
                ops.add(desired_config)
        except (ArrApiError, ValidationError) as e:
            logger.warning("Failed to reconcile %s %s: %s", item_type_name, name, e)


class _DownloadClientOps:
    """Operations adapter for download client reconciliation."""

    def __init__(self, client: ArrApiClient) -> None:
        self._client = client

    def get_current(self):
        return self._client.get_download_clients()

    def get_full(self, item_id: int) -> dict[str, Any]:
        return self._client.get_download_client(item_id)

    def delete(self, item_id: int) -> None:
        self._client.delete_download_client(item_id)

    def add(self, config: dict[str, Any]):
        return self._client.add_download_client(config)

    def update(self, item_id: int, config: dict[str, Any]):
        return self._client.update_download_client(item_id, config)


class _ApplicationOps:
    """Operations adapter for media manager application reconciliation."""

    def __init__(self, client: MediaIndexerClient) -> None:
        self._client = client

    def get_current(self):
        return self._client.get_applications()

    def get_full(self, item_id: int) -> dict[str, Any]:
        return self._client.get_application(item_id)

    def delete(self, item_id: int) -> None:
        self._client.delete_application(item_id)

    def add(self, config: dict[str, Any]):
        return self._client.add_application(config)

    def update(self, item_id: int, config: dict[str, Any]):
        return self._client.update_application(item_id, config)


def reconcile_download_clients(
    api_client: ArrApiClient,
    desired_clients: list[DownloadClientProviderData],
    category: str,
    media_manager: MediaManager,
    get_secret: SecretGetter,
) -> None:
    """Reconcile download clients in Radarr/Sonarr/Lidarr.

    Syncs download client configuration (qBittorrent, SABnzbd) to match
    the desired state from Juju relations. Clients not in desired_clients
    will be deleted.

    Args:
        api_client: API client for Radarr/Sonarr/Lidarr
        desired_clients: Download client data from relations
        category: Category name for downloads (e.g., "radarr", "sonarr")
        media_manager: The type of media manager (determines category field name)
        get_secret: Callback to retrieve secret content by ID
    """
    desired_configs: dict[str, dict[str, Any]] = {}
    for provider in desired_clients:
        config = DownloadClientConfigBuilder.build(
            provider=provider,
            category=category,
            media_manager=media_manager,
            get_secret=get_secret,
        )
        desired_configs[provider.instance_name] = config

    _reconcile_items(
        _DownloadClientOps(api_client),
        desired_configs,
        _DOWNLOAD_CLIENT_KEYS,
        "download client",
    )


def reconcile_media_manager_connections(
    api_client: MediaIndexerClient,
    desired_managers: list[MediaIndexerRequirerData],
    indexer_url: str,
    get_secret: SecretGetter,
) -> None:
    """Reconcile media manager connections in an indexer application.

    Syncs application configuration (connections to Radarr/Sonarr/Lidarr)
    to match the desired state from Juju relations. Connections not in
    desired_managers will be deleted.

    Args:
        api_client: API client implementing MediaIndexerClient protocol
        desired_managers: Media manager data from media-indexer relations
        indexer_url: URL of the indexer instance (e.g., Prowlarr)
        get_secret: Callback to retrieve secret content by ID
    """
    desired_configs: dict[str, dict[str, Any]] = {}
    for requirer in desired_managers:
        config = ApplicationConfigBuilder.build(
            requirer=requirer,
            indexer_url=indexer_url,
            get_secret=get_secret,
        )
        desired_configs[requirer.instance_name] = config

    _reconcile_items(
        _ApplicationOps(api_client),
        desired_configs,
        _APPLICATION_KEYS,
        "media manager connection",
    )


def reconcile_root_folder(
    api_client: ArrApiClient,
    path: str,
) -> None:
    """Ensure root folder exists in Radarr/Sonarr/Lidarr. Additive only.

    Args:
        api_client: API client for Radarr/Sonarr/Lidarr
        path: Filesystem path that should exist as a root folder
    """
    existing = api_client.get_root_folders()
    existing_paths = {rf.path for rf in existing}

    if path not in existing_paths:
        logger.info("Adding root folder: %s", path)
        api_client.add_root_folder(path)


def reconcile_external_url(
    api_client: BaseArrApiClient,
    external_url: str,
) -> None:
    """Configure external URL in any *arr application host config.

    Args:
        api_client: Any *arr API client (extends BaseArrApiClient)
        external_url: External URL for the application
    """
    current_full = api_client.get_host_config_raw()
    current_external_url = current_full.get("applicationUrl", "")

    if current_external_url != external_url:
        logger.info("Updating external URL to: %s", external_url)
        api_client.update_host_config({"applicationUrl": external_url})
