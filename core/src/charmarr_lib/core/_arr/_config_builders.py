# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Config builders for transforming relation data into API payloads."""

from collections.abc import Callable
from urllib.parse import urlparse

from charmarr_lib.core.constants import MEDIA_MANAGER_IMPLEMENTATIONS
from charmarr_lib.core.enums import DownloadClient, MediaManager
from charmarr_lib.core.interfaces import (
    DownloadClientProviderData,
    MediaIndexerRequirerData,
)

# Type alias for secret retrieval callback.
# Takes secret_id, returns dict with secret content (e.g., {"username": "...", "password": "..."})
SecretGetter = Callable[[str], dict[str, str]]

# Maps media manager types to the category field name in download client API payloads.
# Each *arr application uses a different field name for the download category.
_MEDIA_MANAGER_CATEGORY_FIELDS: dict[MediaManager, str] = {
    MediaManager.RADARR: "movieCategory",
    MediaManager.SONARR: "tvCategory",
    MediaManager.LIDARR: "musicCategory",
    MediaManager.READARR: "bookCategory",
    MediaManager.WHISPARR: "movieCategory",  # Uses same as Radarr
}

# Maps media manager types to Prowlarr sync category IDs (NewzNab standard).
# These are the default categories from Prowlarr's application schema.
# https://wiki.servarr.com/en/prowlarr/settings#categories
#
# NewzNab category ID ranges by media type:
#   2000-2090: Movies (2000=Movies, 2010=Foreign, 2020=Other, 2030=SD, 2040=HD,
#              2045=UHD, 2050=BluRay, 2060=3D, 2070=DVD, 2080=WEB-DL, 2090=x265)
#   3000-3060: Audio (3000=Audio, 3010=MP3, 3020=Video, 3030=Audiobook,
#              3040=Lossless, 3050=Podcast, 3060=Foreign)
#   5000-5090: TV (5000=TV, 5010=WEB-DL, 5020=Foreign, 5030=SD, 5040=HD,
#              5045=UHD, 5050=Other, 5060=Sport, 5070=Anime, 5080=Documentary, 5090=x265)
#   6000-6090: XXX (same structure as Movies)
#   7000-7060: Books (7000=Books, 7010=Mags, 7020=EBook, 7030=Comics,
#              7040=Technical, 7050=Foreign, 7060=Undefined)
_MEDIA_MANAGER_SYNC_CATEGORIES: dict[MediaManager, list[int]] = {
    MediaManager.RADARR: [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060, 2070, 2080, 2090],
    MediaManager.SONARR: [5000, 5010, 5020, 5030, 5040, 5045, 5050, 5060, 5070, 5080, 5090],
    MediaManager.LIDARR: [3000, 3010, 3020, 3030, 3040, 3050, 3060],
    MediaManager.READARR: [7000, 7010, 7020, 7030, 7040, 7050, 7060],
    MediaManager.WHISPARR: [6000, 6010, 6020, 6030, 6040, 6045, 6050, 6060, 6070, 6080, 6090],
}


class DownloadClientConfigBuilder:
    """Build download client API payloads from relation data.

    Transforms DownloadClientProviderData into *arr API payloads
    for configuring download clients (qBittorrent, SABnzbd).
    """

    @staticmethod
    def build(
        provider: DownloadClientProviderData,
        category: str,
        media_manager: MediaManager,
        get_secret: SecretGetter,
    ) -> dict:
        """Transform relation data into *arr API payload.

        Args:
            provider: Download client relation data
            category: Category name for downloads (e.g., "radarr", "sonarr")
            media_manager: The type of media manager calling this builder
            get_secret: Callback to retrieve secret content by ID

        Returns:
            API payload dict ready for add_download_client()

        Raises:
            ValueError: If client type is not supported
            KeyError: If media_manager is not in category fields mapping
        """
        category_field = _MEDIA_MANAGER_CATEGORY_FIELDS[media_manager]

        if provider.client == DownloadClient.QBITTORRENT:
            return DownloadClientConfigBuilder._build_qbittorrent(
                provider, category, category_field, get_secret
            )
        elif provider.client == DownloadClient.SABNZBD:
            return DownloadClientConfigBuilder._build_sabnzbd(
                provider, category, category_field, get_secret
            )
        else:
            raise ValueError(f"Unsupported download client: {provider.client}")

    @staticmethod
    def _build_qbittorrent(
        provider: DownloadClientProviderData,
        category: str,
        category_field: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Build qBittorrent download client config."""
        if provider.credentials_secret_id is None:
            raise ValueError("qBittorrent requires credentials_secret_id")
        credentials = get_secret(provider.credentials_secret_id)

        parsed = urlparse(provider.api_url)

        return {
            "enable": True,
            "protocol": "torrent",
            "priority": 1,
            "name": provider.instance_name,
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "fields": [
                {"name": "host", "value": parsed.hostname},
                {"name": "port", "value": parsed.port or 8080},
                {"name": "useSsl", "value": parsed.scheme == "https"},
                {"name": "urlBase", "value": provider.base_path or ""},
                {"name": "username", "value": credentials["username"]},
                {"name": "password", "value": credentials["password"]},
                {"name": category_field, "value": category},
            ],
            "tags": [],
        }

    @staticmethod
    def _build_sabnzbd(
        provider: DownloadClientProviderData,
        category: str,
        category_field: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Build SABnzbd download client config."""
        if provider.api_key_secret_id is None:
            raise ValueError("SABnzbd requires api_key_secret_id")
        secret = get_secret(provider.api_key_secret_id)
        api_key = secret["api-key"]

        parsed = urlparse(provider.api_url)

        return {
            "enable": True,
            "protocol": "usenet",
            "priority": 1,
            "name": provider.instance_name,
            "implementation": "Sabnzbd",
            "configContract": "SabnzbdSettings",
            "fields": [
                {"name": "host", "value": parsed.hostname},
                {"name": "port", "value": parsed.port or 8080},
                {"name": "useSsl", "value": parsed.scheme == "https"},
                {"name": "urlBase", "value": provider.base_path or ""},
                {"name": "apiKey", "value": api_key},
                {"name": category_field, "value": category},
            ],
            "tags": [],
        }


class ApplicationConfigBuilder:
    """Build media indexer application API payloads from relation data.

    Transforms MediaIndexerRequirerData into application payloads
    for configuring connections to media managers (Radarr, Sonarr, etc.).

    Note: Currently builds Prowlarr-compatible payloads. The field names
    like "prowlarrUrl" are Prowlarr-specific API requirements.
    """

    @staticmethod
    def build(
        requirer: MediaIndexerRequirerData,
        indexer_url: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Transform relation data into application payload.

        Args:
            requirer: Media indexer requirer relation data
            indexer_url: URL of the indexer instance
            get_secret: Callback to retrieve secret content by ID

        Returns:
            API payload dict ready for add_application()

        Raises:
            KeyError: If manager type is not in MEDIA_MANAGER_IMPLEMENTATIONS
        """
        implementation, config_contract = MEDIA_MANAGER_IMPLEMENTATIONS[requirer.manager]

        secret = get_secret(requirer.api_key_secret_id)
        api_key = secret["api-key"]

        base_url = requirer.api_url.rstrip("/")
        if requirer.base_path:
            base_url = base_url + requirer.base_path

        sync_categories = _MEDIA_MANAGER_SYNC_CATEGORIES.get(requirer.manager, [])

        return {
            "name": requirer.instance_name,
            "syncLevel": "fullSync",
            "implementation": implementation,
            "configContract": config_contract,
            "fields": [
                {"name": "prowlarrUrl", "value": indexer_url},
                {"name": "baseUrl", "value": base_url},
                {"name": "apiKey", "value": api_key},
                {"name": "syncCategories", "value": sync_categories},
            ],
            "tags": [],
        }
