"""Core charm libraries for Charmarr media automation.

This package provides:
- Juju relation interfaces for media automation
- API clients for *arr applications
- Reconcilers for managing application configuration
"""

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
from charmarr_lib.core.interfaces import (
    DownloadClientChangedEvent,
    DownloadClientProvider,
    DownloadClientProviderData,
    DownloadClientRequirer,
    DownloadClientRequirerData,
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
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
    "DownloadClientChangedEvent",
    "DownloadClientConfigBuilder",
    "DownloadClientProvider",
    "DownloadClientProviderData",
    "DownloadClientRequirer",
    "DownloadClientRequirerData",
    "DownloadClientResponse",
    "DownloadClientType",
    "HostConfigResponse",
    "IndexerResponse",
    "MediaIndexer",
    "MediaIndexerChangedEvent",
    "MediaIndexerProvider",
    "MediaIndexerProviderData",
    "MediaIndexerRequirer",
    "MediaIndexerRequirerData",
    "MediaManager",
    "ProwlarrApiClient",
    "ProwlarrHostConfigResponse",
    "QualityProfileResponse",
    "RequestManager",
    "RootFolderResponse",
    "SecretGetter",
    "reconcile_download_clients",
    "reconcile_external_url",
    "reconcile_media_manager_connections",
    "reconcile_root_folder",
]
