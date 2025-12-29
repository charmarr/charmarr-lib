# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared fixtures for ARR unit tests."""

from unittest.mock import MagicMock

import pytest

from charmarr_lib.core import DownloadClient, DownloadClientType, MediaManager
from charmarr_lib.core.interfaces import DownloadClientProviderData, MediaIndexerRequirerData


@pytest.fixture
def mock_arr_client():
    """Create a mock ArrApiClient."""
    return MagicMock()


@pytest.fixture
def mock_prowlarr_client():
    """Create a mock ProwlarrApiClient."""
    return MagicMock()


@pytest.fixture
def qbittorrent_provider():
    """Create a qBittorrent download client provider data fixture."""
    return DownloadClientProviderData(
        api_url="http://qbittorrent:8080",
        credentials_secret_id="secret:qbit-creds",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbittorrent",
    )


@pytest.fixture
def sabnzbd_provider():
    """Create a SABnzbd download client provider data fixture."""
    return DownloadClientProviderData(
        api_url="http://sabnzbd:8080",
        api_key_secret_id="secret:sab-key",
        client=DownloadClient.SABNZBD,
        client_type=DownloadClientType.USENET,
        instance_name="sabnzbd",
    )


@pytest.fixture
def radarr_requirer():
    """Create a Radarr media indexer requirer data fixture."""
    return MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret:radarr-key",
        manager=MediaManager.RADARR,
        instance_name="radarr-1080p",
    )


@pytest.fixture
def mock_credentials():
    """Return a mock function for resolving credential secrets."""

    def _mock_credentials(secret_id: str) -> dict:
        return {"username": "admin", "password": "supersecret"}

    return _mock_credentials


@pytest.fixture
def mock_api_key():
    """Return a mock function for resolving API key secrets."""

    def _mock_api_key(secret_id: str) -> dict:
        return {"api-key": "test-api-key-123"}

    return _mock_api_key


@pytest.fixture
def charm_dir_with_recyclarr(tmp_path):
    """Create a charm directory with a fake recyclarr binary."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    recyclarr_bin = bin_dir / "recyclarr"
    recyclarr_bin.write_text("#!/bin/bash\nexit 0")
    recyclarr_bin.chmod(0o755)
    return tmp_path


@pytest.fixture
def charm_dir_without_recyclarr(tmp_path):
    """Create a charm directory without recyclarr binary."""
    return tmp_path
