# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for config builders."""

import pytest

from charmarr_lib.core import (
    ApplicationConfigBuilder,
    DownloadClient,
    DownloadClientConfigBuilder,
    DownloadClientType,
    MediaManager,
)
from charmarr_lib.core.interfaces import (
    DownloadClientProviderData,
    MediaIndexerRequirerData,
)


@pytest.fixture
def qbittorrent_provider():
    return DownloadClientProviderData(
        api_url="http://qbittorrent:8080",
        credentials_secret_id="secret:qbit-creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbittorrent",
    )


@pytest.fixture
def sabnzbd_provider():
    return DownloadClientProviderData(
        api_url="http://sabnzbd:8080",
        api_key_secret_id="secret:sab-key",
        client=DownloadClient.SABNZBD,
        client_type=DownloadClientType.USENET,
        instance_name="sabnzbd",
    )


@pytest.fixture
def radarr_requirer():
    return MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret:radarr-key",
        manager=MediaManager.RADARR,
        instance_name="radarr-1080p",
    )


def mock_credentials(secret_id: str) -> dict:
    return {"username": "admin", "password": "supersecret"}


def mock_api_key(secret_id: str) -> dict:
    return {"api-key": "test-api-key-123"}


# DownloadClientConfigBuilder tests


def test_qbittorrent_uses_correct_implementation(qbittorrent_provider):
    """qBittorrent config sets correct implementation and contract."""
    result = DownloadClientConfigBuilder.build(qbittorrent_provider, "radarr", mock_credentials)

    assert result["implementation"] == "QBittorrent"
    assert result["configContract"] == "QBittorrentSettings"
    assert result["protocol"] == "torrent"


def test_qbittorrent_parses_url_components(qbittorrent_provider):
    """qBittorrent config extracts host/port from URL."""
    result = DownloadClientConfigBuilder.build(qbittorrent_provider, "radarr", mock_credentials)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["host"] == "qbittorrent"
    assert fields["port"] == 8080
    assert fields["useSsl"] is False


def test_qbittorrent_uses_credentials_from_secret(qbittorrent_provider):
    """qBittorrent config includes credentials from secret callback."""
    result = DownloadClientConfigBuilder.build(qbittorrent_provider, "radarr", mock_credentials)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["username"] == "admin"
    assert fields["password"] == "supersecret"


def test_qbittorrent_sets_category(qbittorrent_provider):
    """qBittorrent config sets category field from parameter."""
    result = DownloadClientConfigBuilder.build(qbittorrent_provider, "sonarr", mock_credentials)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["category"] == "sonarr"


def test_qbittorrent_https_url():
    """qBittorrent config detects HTTPS from URL scheme."""
    provider = DownloadClientProviderData(
        api_url="https://qbit.example.com:443",
        credentials_secret_id="secret:creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit",
    )

    result = DownloadClientConfigBuilder.build(provider, "radarr", mock_credentials)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["useSsl"] is True
    assert fields["port"] == 443


def test_qbittorrent_base_path():
    """qBittorrent config uses base_path for urlBase field."""
    provider = DownloadClientProviderData(
        api_url="http://qbittorrent:8080",
        credentials_secret_id="secret:creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit",
        base_path="/qbit",
    )

    result = DownloadClientConfigBuilder.build(provider, "radarr", mock_credentials)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["urlBase"] == "/qbit"


def test_sabnzbd_uses_correct_implementation(sabnzbd_provider):
    """SABnzbd config sets correct implementation and contract."""
    result = DownloadClientConfigBuilder.build(sabnzbd_provider, "radarr", mock_api_key)

    assert result["implementation"] == "Sabnzbd"
    assert result["configContract"] == "SabnzbdSettings"
    assert result["protocol"] == "usenet"


def test_sabnzbd_uses_api_key_from_secret(sabnzbd_provider):
    """SABnzbd config includes API key from secret callback."""
    result = DownloadClientConfigBuilder.build(sabnzbd_provider, "radarr", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["apiKey"] == "test-api-key-123"


def test_download_client_common_fields(qbittorrent_provider):
    """Download client config includes common fields."""
    result = DownloadClientConfigBuilder.build(qbittorrent_provider, "radarr", mock_credentials)

    assert result["enable"] is True
    assert result["priority"] == 1
    assert result["name"] == "qbittorrent"
    assert result["tags"] == []


# ApplicationConfigBuilder tests


def test_radarr_uses_correct_implementation(radarr_requirer):
    """Radarr application config sets correct implementation and contract."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    assert result["implementation"] == "Radarr"
    assert result["configContract"] == "RadarrSettings"


def test_application_includes_prowlarr_url(radarr_requirer):
    """Application config includes prowlarr URL in fields."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["prowlarrUrl"] == "http://prowlarr:9696"


def test_application_includes_base_url(radarr_requirer):
    """Application config includes media manager base URL."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["baseUrl"] == "http://radarr:7878"


def test_application_includes_api_key(radarr_requirer):
    """Application config includes API key from secret callback."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["apiKey"] == "test-api-key-123"


def test_application_strips_trailing_slash():
    """Application config strips trailing slash from API URL."""
    requirer = MediaIndexerRequirerData(
        api_url="http://radarr:7878/",
        api_key_secret_id="secret:key",
        manager=MediaManager.RADARR,
        instance_name="radarr",
    )

    result = ApplicationConfigBuilder.build(requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["baseUrl"] == "http://radarr:7878"


def test_application_appends_base_path():
    """Application config appends base_path to API URL."""
    requirer = MediaIndexerRequirerData(
        api_url="http://arr.example.com",
        api_key_secret_id="secret:key",
        manager=MediaManager.RADARR,
        instance_name="radarr",
        base_path="/radarr",
    )

    result = ApplicationConfigBuilder.build(requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["baseUrl"] == "http://arr.example.com/radarr"


def test_application_common_fields(radarr_requirer):
    """Application config includes common fields."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    assert result["name"] == "radarr-1080p"
    assert result["syncLevel"] == "fullSync"
    assert result["tags"] == []


def test_sonarr_implementation():
    """Sonarr uses correct implementation and contract."""
    requirer = MediaIndexerRequirerData(
        api_url="http://sonarr:8989",
        api_key_secret_id="secret:key",
        manager=MediaManager.SONARR,
        instance_name="sonarr",
    )

    result = ApplicationConfigBuilder.build(requirer, "http://prowlarr:9696", mock_api_key)

    assert result["implementation"] == "Sonarr"
    assert result["configContract"] == "SonarrSettings"
