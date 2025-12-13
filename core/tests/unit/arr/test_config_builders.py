# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for config builders."""

from charmarr_lib.core import (
    ApplicationConfigBuilder,
    DownloadClient,
    DownloadClientConfigBuilder,
    DownloadClientType,
    MediaManager,
)
from charmarr_lib.core.interfaces import DownloadClientProviderData, MediaIndexerRequirerData

# DownloadClientConfigBuilder tests


def test_qbittorrent_uses_correct_implementation(qbittorrent_provider, mock_credentials):
    """qBittorrent config sets correct implementation and contract."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    assert result["implementation"] == "QBittorrent"
    assert result["configContract"] == "QBittorrentSettings"
    assert result["protocol"] == "torrent"


def test_qbittorrent_parses_url_components(qbittorrent_provider, mock_credentials):
    """qBittorrent config extracts host/port from URL."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["host"] == "qbittorrent"
    assert fields["port"] == 8080
    assert fields["useSsl"] is False


def test_qbittorrent_uses_credentials_from_secret(qbittorrent_provider, mock_credentials):
    """qBittorrent config includes credentials from secret callback."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["username"] == "admin"
    assert fields["password"] == "supersecret"


def test_qbittorrent_sets_category_field_for_radarr(qbittorrent_provider, mock_credentials):
    """qBittorrent config uses movieCategory field for Radarr."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "radarr-1080p", MediaManager.RADARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["movieCategory"] == "radarr-1080p"


def test_qbittorrent_sets_category_field_for_sonarr(qbittorrent_provider, mock_credentials):
    """qBittorrent config uses tvCategory field for Sonarr."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "sonarr", MediaManager.SONARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["tvCategory"] == "sonarr"


def test_qbittorrent_https_url(mock_credentials):
    """qBittorrent config detects HTTPS from URL scheme."""
    provider = DownloadClientProviderData(
        api_url="https://qbit.example.com:443",
        credentials_secret_id="secret:creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit",
    )

    result = DownloadClientConfigBuilder.build(
        provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["useSsl"] is True
    assert fields["port"] == 443


def test_qbittorrent_base_path(mock_credentials):
    """qBittorrent config uses base_path for urlBase field."""
    provider = DownloadClientProviderData(
        api_url="http://qbittorrent:8080",
        credentials_secret_id="secret:creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit",
        base_path="/qbit",
    )

    result = DownloadClientConfigBuilder.build(
        provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["urlBase"] == "/qbit"


def test_sabnzbd_uses_correct_implementation(sabnzbd_provider, mock_api_key):
    """SABnzbd config sets correct implementation and contract."""
    result = DownloadClientConfigBuilder.build(
        sabnzbd_provider, "radarr", MediaManager.RADARR, mock_api_key
    )

    assert result["implementation"] == "Sabnzbd"
    assert result["configContract"] == "SabnzbdSettings"
    assert result["protocol"] == "usenet"


def test_sabnzbd_uses_api_key_from_secret(sabnzbd_provider, mock_api_key):
    """SABnzbd config includes API key from secret callback."""
    result = DownloadClientConfigBuilder.build(
        sabnzbd_provider, "radarr", MediaManager.RADARR, mock_api_key
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["apiKey"] == "test-api-key-123"


def test_sabnzbd_sets_category_field_for_lidarr(sabnzbd_provider, mock_api_key):
    """SABnzbd config uses musicCategory field for Lidarr."""
    result = DownloadClientConfigBuilder.build(
        sabnzbd_provider, "lidarr", MediaManager.LIDARR, mock_api_key
    )

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["musicCategory"] == "lidarr"


def test_download_client_common_fields(qbittorrent_provider, mock_credentials):
    """Download client config includes common fields."""
    result = DownloadClientConfigBuilder.build(
        qbittorrent_provider, "radarr", MediaManager.RADARR, mock_credentials
    )

    assert result["enable"] is True
    assert result["priority"] == 1
    assert result["name"] == "qbittorrent"
    assert result["tags"] == []


# ApplicationConfigBuilder tests


def test_radarr_uses_correct_implementation(radarr_requirer, mock_api_key):
    """Radarr application config sets correct implementation and contract."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    assert result["implementation"] == "Radarr"
    assert result["configContract"] == "RadarrSettings"


def test_application_includes_prowlarr_url(radarr_requirer, mock_api_key):
    """Application config includes prowlarr URL in fields."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["prowlarrUrl"] == "http://prowlarr:9696"


def test_application_includes_base_url(radarr_requirer, mock_api_key):
    """Application config includes media manager base URL."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["baseUrl"] == "http://radarr:7878"


def test_application_includes_api_key(radarr_requirer, mock_api_key):
    """Application config includes API key from secret callback."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    fields = {f["name"]: f["value"] for f in result["fields"]}
    assert fields["apiKey"] == "test-api-key-123"


def test_application_strips_trailing_slash(mock_api_key):
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


def test_application_appends_base_path(mock_api_key):
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


def test_application_common_fields(radarr_requirer, mock_api_key):
    """Application config includes common fields."""
    result = ApplicationConfigBuilder.build(radarr_requirer, "http://prowlarr:9696", mock_api_key)

    assert result["name"] == "radarr-1080p"
    assert result["syncLevel"] == "fullSync"
    assert result["tags"] == []


def test_sonarr_implementation(mock_api_key):
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
