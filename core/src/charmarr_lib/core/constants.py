# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared constants for Charmarr interfaces and API clients."""

from charmarr_lib.core.enums import MediaManager

# Maps media manager types to their download folder names.
# Used by:
# - Download client charms (qBittorrent, SABnzbd) to create categories with correct save paths
# - Arr charms to know where downloads will land (for import path configuration)
MEDIA_TYPE_DOWNLOAD_PATHS: dict[MediaManager, str] = {
    MediaManager.RADARR: "movies",
    MediaManager.SONARR: "tv",
    MediaManager.LIDARR: "music",
    MediaManager.READARR: "books",
    MediaManager.WHISPARR: "xxx",
}

# Maps media managers to their Prowlarr application implementation details.
# Tuple format: (implementation_name, config_contract_name)
# Used by ApplicationConfigBuilder to transform relation data into Prowlarr application payloads.
MEDIA_MANAGER_IMPLEMENTATIONS: dict[MediaManager, tuple[str, str]] = {
    MediaManager.RADARR: ("Radarr", "RadarrSettings"),
    MediaManager.SONARR: ("Sonarr", "SonarrSettings"),
    MediaManager.LIDARR: ("Lidarr", "LidarrSettings"),
    MediaManager.READARR: ("Readarr", "ReadarrSettings"),
    MediaManager.WHISPARR: ("Whisparr", "WhisparrSettings"),
}
