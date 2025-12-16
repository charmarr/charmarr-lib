# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Core charm libraries for Charmarr."""

from charmarr_lib.core._arr import (
    ApplicationConfigBuilder,
    ApplicationResponse,
    ArrApiClient,
    ArrApiConnectionError,
    ArrApiError,
    ArrApiResponseError,
    DownloadClientConfigBuilder,
    DownloadClientResponse,
    HostConfigResponse,
    IndexerResponse,
    ProwlarrApiClient,
    ProwlarrHostConfigResponse,
    QualityProfileResponse,
    RootFolderResponse,
    SecretGetter,
    reconcile_download_clients,
    reconcile_external_url,
    reconcile_media_manager_connections,
    reconcile_root_folder,
)
from charmarr_lib.core._k8s import (
    K8sResourceManager,
    ReconcileResult,
    is_storage_mounted,
    reconcile_storage_volume,
)
from charmarr_lib.core.constants import (
    MEDIA_MANAGER_IMPLEMENTATIONS,
    MEDIA_TYPE_DOWNLOAD_PATHS,
)
from charmarr_lib.core.enums import (
    DownloadClient,
    DownloadClientType,
    MediaIndexer,
    MediaManager,
    RequestManager,
)

__all__ = [
    "MEDIA_MANAGER_IMPLEMENTATIONS",
    "MEDIA_TYPE_DOWNLOAD_PATHS",
    "ApplicationConfigBuilder",
    "ApplicationResponse",
    "ArrApiClient",
    "ArrApiConnectionError",
    "ArrApiError",
    "ArrApiResponseError",
    "DownloadClient",
    "DownloadClientConfigBuilder",
    "DownloadClientResponse",
    "DownloadClientType",
    "HostConfigResponse",
    "IndexerResponse",
    "K8sResourceManager",
    "MediaIndexer",
    "MediaManager",
    "ProwlarrApiClient",
    "ProwlarrHostConfigResponse",
    "QualityProfileResponse",
    "ReconcileResult",
    "RequestManager",
    "RootFolderResponse",
    "SecretGetter",
    "is_storage_mounted",
    "reconcile_download_clients",
    "reconcile_external_url",
    "reconcile_media_manager_connections",
    "reconcile_root_folder",
    "reconcile_storage_volume",
]
