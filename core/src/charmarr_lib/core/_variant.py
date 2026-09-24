# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Content variant utilities for media managers."""

from charmarr_lib.core.enums import ContentVariant, MediaManager

_ROOT_FOLDERS: dict[tuple[ContentVariant, MediaManager], str] = {
    (ContentVariant.STANDARD, MediaManager.RADARR): "/data/media/movies",
    (ContentVariant.UHD, MediaManager.RADARR): "/data/media/movies-uhd",
    (ContentVariant.ANIME, MediaManager.RADARR): "/data/media/anime/movies",
    (ContentVariant.STANDARD, MediaManager.SONARR): "/data/media/tv",
    (ContentVariant.UHD, MediaManager.SONARR): "/data/media/tv-uhd",
    (ContentVariant.ANIME, MediaManager.SONARR): "/data/media/anime/tv",
}

# TRaSH Guides names its Sonarr profiles differently from its Radarr ones, so the
# default cannot be chosen from the variant alone.
_DEFAULT_TRASH_PROFILES: dict[tuple[ContentVariant, MediaManager], str] = {
    (ContentVariant.STANDARD, MediaManager.RADARR): "",
    (ContentVariant.UHD, MediaManager.RADARR): "uhd-bluray-web",
    (ContentVariant.ANIME, MediaManager.RADARR): "anime-remux-1080p",
    (ContentVariant.STANDARD, MediaManager.SONARR): "",
    (ContentVariant.UHD, MediaManager.SONARR): "web-2160p",
    (ContentVariant.ANIME, MediaManager.SONARR): "anime-remux-1080p",
}


def get_root_folder(variant: ContentVariant, manager: MediaManager) -> str:
    """Get root folder path for a content variant and media manager."""
    return _ROOT_FOLDERS[(variant, manager)]


def get_default_trash_profiles(variant: ContentVariant, manager: MediaManager) -> str:
    """Get the default Recyclarr template for a content variant and media manager.

    Returns an empty string for the standard variant, which syncs nothing.
    """
    return _DEFAULT_TRASH_PROFILES[(variant, manager)]
