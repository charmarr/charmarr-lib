# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Config builders for transforming relation data into API payloads."""

from collections.abc import Callable
from urllib.parse import urlparse

from charmarr_lib.core.constants import MEDIA_MANAGER_IMPLEMENTATIONS
from charmarr_lib.core.enums import DownloadClient
from charmarr_lib.core.interfaces import (
    DownloadClientProviderData,
    MediaIndexerRequirerData,
)

# Type alias for secret retrieval callback.
# Takes secret_id, returns dict with secret content (e.g., {"username": "...", "password": "..."})
SecretGetter = Callable[[str], dict[str, str]]


class DownloadClientConfigBuilder:
    """Build download client API payloads from relation data.

    Transforms DownloadClientProviderData into *arr API payloads
    for configuring download clients (qBittorrent, SABnzbd).
    """

    @staticmethod
    def build(
        provider: DownloadClientProviderData,
        category: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Transform relation data into *arr API payload.

        Args:
            provider: Download client relation data
            category: Category name for downloads (e.g., "radarr", "sonarr")
            get_secret: Callback to retrieve secret content by ID

        Returns:
            API payload dict ready for add_download_client()

        Raises:
            ValueError: If client type is not supported
        """
        if provider.client == DownloadClient.QBITTORRENT:
            return DownloadClientConfigBuilder._build_qbittorrent(
                provider, category, get_secret
            )
        elif provider.client == DownloadClient.SABNZBD:
            return DownloadClientConfigBuilder._build_sabnzbd(provider, category, get_secret)
        else:
            raise ValueError(f"Unsupported download client: {provider.client}")

    @staticmethod
    def _build_qbittorrent(
        provider: DownloadClientProviderData,
        category: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Build qBittorrent download client config."""
        assert provider.credentials_secret_id is not None
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
                {"name": "category", "value": category},
            ],
            "tags": [],
        }

    @staticmethod
    def _build_sabnzbd(
        provider: DownloadClientProviderData,
        category: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Build SABnzbd download client config."""
        assert provider.api_key_secret_id is not None
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
                {"name": "category", "value": category},
            ],
            "tags": [],
        }


class ApplicationConfigBuilder:
    """Build Prowlarr application API payloads from relation data.

    Transforms MediaIndexerRequirerData into Prowlarr application payloads
    for configuring connections to media managers (Radarr, Sonarr, etc.).
    """

    @staticmethod
    def build(
        requirer: MediaIndexerRequirerData,
        prowlarr_url: str,
        get_secret: SecretGetter,
    ) -> dict:
        """Transform relation data into Prowlarr application payload.

        Args:
            requirer: Media indexer requirer relation data
            prowlarr_url: URL of the Prowlarr instance
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

        return {
            "name": requirer.instance_name,
            "syncLevel": "fullSync",
            "implementation": implementation,
            "configContract": config_contract,
            "fields": [
                {"name": "prowlarrUrl", "value": prowlarr_url},
                {"name": "baseUrl", "value": base_url},
                {"name": "apiKey", "value": api_key},
                {"name": "syncCategories", "value": []},
            ],
            "tags": [],
        }
