# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for download-client interface."""

from typing import ClassVar

import pytest
from ops import CharmBase
from pydantic import ValidationError
from scenario import Context, Relation, State

from charmarr_lib.core import DownloadClient, DownloadClientType, MediaManager
from charmarr_lib.core.interfaces import (
    DownloadClientProvider,
    DownloadClientProviderData,
    DownloadClientRequirer,
    DownloadClientRequirerData,
)


class ProviderCharm(CharmBase):
    """Minimal charm using DownloadClientProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"download-client": {"interface": "download_client"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = DownloadClientProvider(self, "download-client")


class RequirerCharm(CharmBase):
    """Minimal charm using DownloadClientRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"download-client": {"interface": "download_client"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = DownloadClientRequirer(self, "download-client")


def test_xor_validation_fails_with_neither():
    """Test XOR validator fails when neither auth field is provided."""
    with pytest.raises(ValidationError, match="Must provide either"):
        DownloadClientProviderData(
            api_url="http://qbit:8080",
            client=DownloadClient.QBITTORRENT,
            client_type=DownloadClientType.TORRENT,
            instance_name="qbit",
        )


def test_xor_validation_fails_with_both():
    """Test XOR validator fails when both auth fields are provided."""
    with pytest.raises(ValidationError, match="Cannot provide both"):
        DownloadClientProviderData(
            api_url="http://qbit:8080",
            api_key_secret_id="secret://123",
            credentials_secret_id="secret://456",
            client=DownloadClient.QBITTORRENT,
            client_type=DownloadClientType.TORRENT,
            instance_name="qbit",
        )


def test_provider_publish_and_get_requirers():
    """Test provider publishes with 'config' key and retrieves requirers."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    requirer_data = DownloadClientRequirerData(
        manager=MediaManager.RADARR, instance_name="radarr-4k"
    )
    relation = Relation(
        endpoint="download-client",
        interface="download_client",
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = DownloadClientProviderData(
            api_url="http://qbit:8080",
            credentials_secret_id="secret://456",
            client=DownloadClient.QBITTORRENT,
            client_type=DownloadClientType.TORRENT,
            instance_name="qbit-vpn",
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()
        requirers = mgr.charm.provider.get_requirers()

    relation_out = state_out.get_relations("download-client")[0]
    assert "config" in relation_out.local_app_data
    assert len(requirers) == 1
    assert requirers[0].manager == MediaManager.RADARR


def test_requirer_handles_multiple_providers():
    """Test requirer correctly handles multiple provider relations."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    qbit = DownloadClientProviderData(
        api_url="http://qbit:8080",
        credentials_secret_id="secret://1",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit-vpn",
    )
    sab = DownloadClientProviderData(
        api_url="http://sab:8080",
        api_key_secret_id="secret://2",
        client=DownloadClient.SABNZBD,
        client_type=DownloadClientType.USENET,
        instance_name="sab",
    )
    state_in = State(
        leader=True,
        relations=[
            Relation(
                endpoint="download-client",
                interface="download_client",
                remote_app_data={"config": qbit.model_dump_json()},
            ),
            Relation(
                endpoint="download-client",
                interface="download_client",
                remote_app_data={"config": sab.model_dump_json()},
            ),
        ],
    )

    with ctx(ctx.on.start(), state_in) as mgr:
        providers = mgr.charm.requirer.get_providers()

    assert len(providers) == 2
    clients = {p.client for p in providers}
    assert clients == {DownloadClient.QBITTORRENT, DownloadClient.SABNZBD}


def test_requirer_is_ready_logic():
    """Test requirer is_ready when published and has provider."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = DownloadClientProviderData(
        api_url="http://qbit:8080",
        credentials_secret_id="secret://1",
        client=DownloadClient.QBITTORRENT,
        client_type=DownloadClientType.TORRENT,
        instance_name="qbit",
    )
    requirer_data = DownloadClientRequirerData(manager=MediaManager.RADARR, instance_name="radarr")
    relation = Relation(
        endpoint="download-client",
        interface="download_client",
        local_app_data={"config": requirer_data.model_dump_json()},
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is True

    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_provider_publish_data_non_leader():
    """Test provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="download-client", interface="download_client")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = DownloadClientProviderData(
            api_url="http://qbit:8080",
            credentials_secret_id="secret://456",
            client=DownloadClient.QBITTORRENT,
            client_type=DownloadClientType.TORRENT,
            instance_name="qbit",
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("download-client")[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_publish_data_non_leader():
    """Test requirer doesn't publish data when not leader."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="download-client", interface="download_client")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirer_data = DownloadClientRequirerData(
            manager=MediaManager.RADARR,
            instance_name="radarr",
        )
        mgr.charm.requirer.publish_data(requirer_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("download-client")[0]
    assert "config" not in relation_out.local_app_data
