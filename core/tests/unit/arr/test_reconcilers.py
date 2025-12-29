# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for reconcilers."""

from charmarr_lib.core import (
    MediaManagerConnection,
    reconcile_download_clients,
    reconcile_external_url,
    reconcile_media_manager_connections,
    reconcile_root_folder,
)
from charmarr_lib.core._arr._arr_client import DownloadClientResponse, RootFolderResponse
from charmarr_lib.core.enums import MediaManager

# reconcile_download_clients


def test_download_clients_adds_new(mock_arr_client, qbittorrent_provider, mock_credentials):
    """Adds download client when not present."""
    mock_arr_client.get_download_clients.return_value = []

    reconcile_download_clients(
        mock_arr_client, [qbittorrent_provider], "radarr", MediaManager.RADARR, mock_credentials
    )

    mock_arr_client.add_download_client.assert_called_once()


def test_download_clients_deletes_removed(mock_arr_client, mock_credentials):
    """Deletes download client not in desired list."""
    existing = DownloadClientResponse(
        id=1, name="old-client", enable=True, protocol="torrent", implementation="QBittorrent"
    )
    mock_arr_client.get_download_clients.return_value = [existing]

    reconcile_download_clients(
        mock_arr_client, [], "radarr", MediaManager.RADARR, mock_credentials
    )

    mock_arr_client.delete_download_client.assert_called_once_with(1)


def test_download_clients_updates_when_changed(
    mock_arr_client, qbittorrent_provider, mock_credentials
):
    """Updates download client when config differs."""
    existing = DownloadClientResponse(
        id=1, name="qbittorrent", enable=True, protocol="torrent", implementation="QBittorrent"
    )
    mock_arr_client.get_download_clients.return_value = [existing]
    mock_arr_client.get_download_client.return_value = {
        "id": 1,
        "name": "qbittorrent",
        "enable": True,
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
        "fields": [{"name": "host", "value": "old-host"}],
    }

    reconcile_download_clients(
        mock_arr_client, [qbittorrent_provider], "radarr", MediaManager.RADARR, mock_credentials
    )

    mock_arr_client.update_download_client.assert_called_once()


def test_download_clients_skips_unchanged(mock_arr_client, qbittorrent_provider, mock_credentials):
    """Skips update when config matches."""
    existing = DownloadClientResponse(
        id=1, name="qbittorrent", enable=True, protocol="torrent", implementation="QBittorrent"
    )
    mock_arr_client.get_download_clients.return_value = [existing]
    mock_arr_client.get_download_client.return_value = {
        "id": 1,
        "name": "qbittorrent",
        "enable": True,
        "protocol": "torrent",
        "implementation": "QBittorrent",
        "configContract": "QBittorrentSettings",
        "fields": [
            {"name": "host", "value": "qbittorrent"},
            {"name": "port", "value": 8080},
            {"name": "useSsl", "value": False},
            {"name": "urlBase", "value": ""},
            {"name": "username", "value": "admin"},
            {"name": "password", "value": "supersecret"},
            {"name": "movieCategory", "value": "radarr"},
        ],
    }

    reconcile_download_clients(
        mock_arr_client, [qbittorrent_provider], "radarr", MediaManager.RADARR, mock_credentials
    )

    mock_arr_client.update_download_client.assert_not_called()


# reconcile_media_manager_connections


def test_media_manager_connections_adds_new(mock_prowlarr_client, radarr_requirer, mock_api_key):
    """Adds application when not present."""
    mock_prowlarr_client.get_applications.return_value = []

    reconcile_media_manager_connections(
        mock_prowlarr_client, [radarr_requirer], "http://prowlarr:9696", mock_api_key
    )

    mock_prowlarr_client.add_application.assert_called_once()


def test_media_manager_connections_deletes_removed(mock_prowlarr_client, mock_api_key):
    """Deletes application not in desired list."""
    existing = MediaManagerConnection(id=1, name="old-app")
    mock_prowlarr_client.get_applications.return_value = [existing]

    reconcile_media_manager_connections(
        mock_prowlarr_client, [], "http://prowlarr:9696", mock_api_key
    )

    mock_prowlarr_client.delete_application.assert_called_once_with(1)


def test_media_manager_connections_updates_when_changed(
    mock_prowlarr_client, radarr_requirer, mock_api_key
):
    """Updates application when config differs."""
    existing = MediaManagerConnection(id=1, name="radarr-1080p")
    mock_prowlarr_client.get_applications.return_value = [existing]
    mock_prowlarr_client.get_application.return_value = {
        "id": 1,
        "name": "radarr-1080p",
        "syncLevel": "fullSync",
        "implementation": "Radarr",
        "configContract": "RadarrSettings",
        "fields": [{"name": "baseUrl", "value": "http://old-url:7878"}],
    }

    reconcile_media_manager_connections(
        mock_prowlarr_client, [radarr_requirer], "http://prowlarr:9696", mock_api_key
    )

    mock_prowlarr_client.update_application.assert_called_once()


# reconcile_root_folder


def test_root_folder_adds_missing(mock_arr_client):
    """Adds root folder when not present."""
    mock_arr_client.get_root_folders.return_value = []

    reconcile_root_folder(mock_arr_client, "/data/media/movies")

    mock_arr_client.add_root_folder.assert_called_once_with("/data/media/movies")


def test_root_folder_skips_existing(mock_arr_client):
    """Skips root folder when already present."""
    existing = RootFolderResponse(id=1, path="/data/media/movies", accessible=True)
    mock_arr_client.get_root_folders.return_value = [existing]

    reconcile_root_folder(mock_arr_client, "/data/media/movies")

    mock_arr_client.add_root_folder.assert_not_called()


# reconcile_external_url


def test_external_url_updates_when_different(mock_arr_client):
    """Updates external URL when different from current."""
    mock_arr_client.get_host_config_raw.return_value = {"applicationUrl": ""}

    reconcile_external_url(mock_arr_client, "https://radarr.example.com")

    mock_arr_client.update_host_config.assert_called_once_with(
        {"applicationUrl": "https://radarr.example.com"}
    )


def test_external_url_skips_when_same(mock_arr_client):
    """Skips update when external URL matches."""
    mock_arr_client.get_host_config_raw.return_value = {
        "applicationUrl": "https://radarr.example.com"
    }

    reconcile_external_url(mock_arr_client, "https://radarr.example.com")

    mock_arr_client.update_host_config.assert_not_called()
