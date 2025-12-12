# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Juju relation interface implementations for Charmarr."""

from charmarr_lib.core.interfaces.media_indexer import (
    MediaIndexerChangedEvent,
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
)

__all__ = [
    "MediaIndexerChangedEvent",
    "MediaIndexerProvider",
    "MediaIndexerProviderData",
    "MediaIndexerRequirer",
    "MediaIndexerRequirerData",
]
