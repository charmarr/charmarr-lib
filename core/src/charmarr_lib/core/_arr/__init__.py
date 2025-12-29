# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""API clients, config builders, and reconcilers for *ARR applications."""

from charmarr_lib.core._arr._arr_client import (
    ArrApiClient,
    DownloadClientResponse,
    HostConfigResponse,
    QualityProfileResponse,
    RootFolderResponse,
)
from charmarr_lib.core._arr._base_client import (
    ArrApiConnectionError,
    ArrApiError,
    ArrApiResponseError,
    BaseArrApiClient,
)
from charmarr_lib.core._arr._config_builders import (
    ApplicationConfigBuilder,
    DownloadClientConfigBuilder,
    SecretGetter,
)
from charmarr_lib.core._arr._config_xml import (
    config_has_api_key,
    generate_api_key,
    read_api_key,
    reconcile_config_xml,
    update_api_key,
)
from charmarr_lib.core._arr._protocols import (
    MediaIndexerClient,
    MediaManagerConnection,
)
from charmarr_lib.core._arr._reconcilers import (
    reconcile_download_clients,
    reconcile_external_url,
    reconcile_media_manager_connections,
    reconcile_root_folder,
)
from charmarr_lib.core._arr._recyclarr import (
    RecyclarrError,
    sync_trash_profiles,
)

__all__ = [
    "ApplicationConfigBuilder",
    "ArrApiClient",
    "ArrApiConnectionError",
    "ArrApiError",
    "ArrApiResponseError",
    "BaseArrApiClient",
    "DownloadClientConfigBuilder",
    "DownloadClientResponse",
    "HostConfigResponse",
    "MediaIndexerClient",
    "MediaManagerConnection",
    "QualityProfileResponse",
    "RecyclarrError",
    "RootFolderResponse",
    "SecretGetter",
    "config_has_api_key",
    "generate_api_key",
    "read_api_key",
    "reconcile_config_xml",
    "reconcile_download_clients",
    "reconcile_external_url",
    "reconcile_media_manager_connections",
    "reconcile_root_folder",
    "sync_trash_profiles",
    "update_api_key",
]
