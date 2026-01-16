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

_DEFAULT_TRASH_PROFILES: dict[ContentVariant, str] = {
    ContentVariant.STANDARD: "",
    ContentVariant.UHD: "uhd-bluray-web",
    ContentVariant.ANIME: "anime",
}


def get_root_folder(variant: ContentVariant, manager: MediaManager) -> str:
    """Get root folder path for a content variant and media manager."""
    return _ROOT_FOLDERS[(variant, manager)]


def get_default_trash_profiles(variant: ContentVariant) -> str:
    """Get default trash profiles for a content variant.

    Returns:
        - standard: empty (no default profiles)
        - 4k: uhd-bluray-web
        - anime: anime
    """
    return _DEFAULT_TRASH_PROFILES[variant]
