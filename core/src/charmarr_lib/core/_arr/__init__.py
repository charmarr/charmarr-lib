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
)
from charmarr_lib.core._arr._config_builders import (
    ApplicationConfigBuilder,
    DownloadClientConfigBuilder,
    SecretGetter,
)
from charmarr_lib.core._arr._prowlarr_client import (
    ApplicationResponse,
    IndexerResponse,
    ProwlarrApiClient,
    ProwlarrHostConfigResponse,
)
from charmarr_lib.core._arr._reconcilers import (
    reconcile_download_clients,
    reconcile_external_url,
    reconcile_media_manager_connections,
    reconcile_root_folder,
)

__all__ = [
    "ApplicationConfigBuilder",
    "ApplicationResponse",
    "ArrApiClient",
    "ArrApiConnectionError",
    "ArrApiError",
    "ArrApiResponseError",
    "DownloadClientConfigBuilder",
    "DownloadClientResponse",
    "HostConfigResponse",
    "IndexerResponse",
    "ProwlarrApiClient",
    "ProwlarrHostConfigResponse",
    "QualityProfileResponse",
    "RootFolderResponse",
    "SecretGetter",
    "reconcile_download_clients",
    "reconcile_external_url",
    "reconcile_media_manager_connections",
    "reconcile_root_folder",
]
