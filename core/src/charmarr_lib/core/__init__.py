"""Core charm libraries for Charmarr media automation.

This package provides:
- Juju relation interfaces for media automation
- API clients for *arr applications
- Reconcilers for managing application configuration
"""

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
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
)

__all__ = [
    "MEDIA_MANAGER_IMPLEMENTATIONS",
    "MEDIA_TYPE_DOWNLOAD_PATHS",
    "DownloadClient",
    "DownloadClientType",
    "MediaIndexer",
    "MediaIndexerChangedEvent",
    "MediaIndexerProvider",
    "MediaIndexerProviderData",
    "MediaIndexerRequirer",
    "MediaIndexerRequirerData",
    "MediaManager",
    "RequestManager",
]
