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
from charmarr_lib.core.interfaces._media_indexer import (
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
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
    "MediaIndexerChangedEvent",
    "MediaIndexerProvider",
    "MediaIndexerProviderData",
    "MediaIndexerRequirer",
    "MediaIndexerRequirerData",
    "MediaStorageChangedEvent",
    "MediaStorageProvider",
    "MediaStorageProviderData",
    "MediaStorageRequirer",
    "MediaStorageRequirerData",
]
