# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Consolidated enums for Charmarr interfaces."""

from enum import Enum


class MediaIndexer(str, Enum):
    """Media indexer applications."""

    PROWLARR = "prowlarr"


class MediaManager(str, Enum):
    """Media manager applications."""

    RADARR = "radarr"
    SONARR = "sonarr"
    LIDARR = "lidarr"
    READARR = "readarr"
    WHISPARR = "whisparr"


class DownloadClient(str, Enum):
    """Download client applications."""

    QBITTORRENT = "qbittorrent"
    SABNZBD = "sabnzbd"


class DownloadClientType(str, Enum):
    """Download protocol categories."""

    TORRENT = "torrent"
    USENET = "usenet"


class RequestManager(str, Enum):
    """Request management applications."""

    OVERSEERR = "overseerr"
    JELLYSEERR = "jellyseerr"
