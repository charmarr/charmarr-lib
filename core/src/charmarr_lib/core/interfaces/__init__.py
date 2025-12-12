# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Juju relation interface implementations for Charmarr."""

from charmarr_lib.core.interfaces.download_client import (
    DownloadClientChangedEvent,
    DownloadClientProvider,
    DownloadClientProviderData,
    DownloadClientRequirer,
    DownloadClientRequirerData,
)
from charmarr_lib.core.interfaces.media_indexer import (
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
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
]
