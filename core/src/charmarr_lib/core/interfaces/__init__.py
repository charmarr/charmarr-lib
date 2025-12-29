# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Juju relation interface implementations for Charmarr."""

from charmarr_lib.core.interfaces._download_client import (
    DownloadClientChangedEvent,
    DownloadClientProvider,
    DownloadClientProviderData,
    DownloadClientRequirer,
    DownloadClientRequirerData,
)
from charmarr_lib.core.interfaces._flaresolverr import (
    FlareSolverrChangedEvent,
    FlareSolverrProvider,
    FlareSolverrProviderData,
    FlareSolverrRequirer,
)
from charmarr_lib.core.interfaces._media_indexer import (
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
)
from charmarr_lib.core.interfaces._media_manager import (
    MediaManagerChangedEvent,
    MediaManagerProvider,
    MediaManagerProviderData,
    MediaManagerRequirer,
    MediaManagerRequirerData,
    QualityProfile,
)
from charmarr_lib.core.interfaces._media_storage import (
    MediaStorageChangedEvent,
    MediaStorageProvider,
    MediaStorageProviderData,
    MediaStorageRequirer,
    MediaStorageRequirerData,
)

__all__ = [
    "DownloadClientChangedEvent",
    "DownloadClientProvider",
    "DownloadClientProviderData",
    "DownloadClientRequirer",
    "DownloadClientRequirerData",
    "FlareSolverrChangedEvent",
    "FlareSolverrProvider",
    "FlareSolverrProviderData",
    "FlareSolverrRequirer",
    "MediaIndexerChangedEvent",
    "MediaIndexerProvider",
    "MediaIndexerProviderData",
    "MediaIndexerRequirer",
    "MediaIndexerRequirerData",
    "MediaManagerChangedEvent",
    "MediaManagerProvider",
    "MediaManagerProviderData",
    "MediaManagerRequirer",
    "MediaManagerRequirerData",
    "MediaStorageChangedEvent",
    "MediaStorageProvider",
    "MediaStorageProviderData",
    "MediaStorageRequirer",
    "MediaStorageRequirerData",
    "QualityProfile",
]
