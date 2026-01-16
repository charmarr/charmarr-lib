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


class ContentVariant(str, Enum):
    """Content variant for media manager instances.

    STANDARD is the default catch-all for any content type.
    UHD and ANIME are specialized variants with dedicated folders.
    """

    STANDARD = "standard"
    UHD = "4k"
    ANIME = "anime"
