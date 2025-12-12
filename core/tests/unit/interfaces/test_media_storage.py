# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for media-storage interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core.interfaces import (
    MediaStorageProvider,
    MediaStorageProviderData,
    MediaStorageRequirer,
    MediaStorageRequirerData,
)


class ProviderCharm(CharmBase):
    """Minimal charm using MediaStorageProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"media-storage": {"interface": "media_storage"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = MediaStorageProvider(self, "media-storage")


class RequirerCharm(CharmBase):
    """Minimal charm using MediaStorageRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"media-storage": {"interface": "media_storage"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = MediaStorageRequirer(self, "media-storage")


def test_provider_publish_and_get_connected_apps():
    """Test provider publishes data and retrieves connected apps."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    requirer_data = MediaStorageRequirerData(instance_name="radarr-4k")
    relation = Relation(
        endpoint="media-storage",
        interface="media_storage",
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = MediaStorageProviderData(pvc_name="charmarr-shared")
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()
        connected = mgr.charm.provider.get_connected_apps()

    relation_out = state_out.get_relations("media-storage")[0]
    assert "config" in relation_out.local_app_data
    assert len(connected) == 1
    assert connected[0] == "radarr-4k"


def test_requirer_get_provider_with_puid_pgid():
    """Test requirer correctly retrieves provider data including PUID/PGID."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaStorageProviderData(
        pvc_name="charmarr-shared",
        mount_path="/data",
        puid=1050,
        pgid=1050,
    )
    relation = Relation(
        endpoint="media-storage",
        interface="media_storage",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        retrieved = mgr.charm.requirer.get_provider()

    assert retrieved is not None
    assert retrieved.pvc_name == "charmarr-shared"
    assert retrieved.puid == 1050
    assert retrieved.pgid == 1050


def test_requirer_is_ready_with_provider():
    """Test requirer is_ready returns True when provider data exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaStorageProviderData(pvc_name="charmarr-shared")
    relation = Relation(
        endpoint="media-storage",
        interface="media_storage",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is True


def test_requirer_is_ready_without_relation():
    """Test requirer is_ready returns False when no relation exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)

    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_requirer_is_ready_without_provider_data():
    """Test requirer is_ready returns False when provider hasn't published data."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(
        endpoint="media-storage",
        interface="media_storage",
        remote_app_data={},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_provider_publish_data_non_leader():
    """Test provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="media-storage", interface="media_storage")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = MediaStorageProviderData(pvc_name="charmarr-shared")
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("media-storage")[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_publish_data_non_leader():
    """Test requirer doesn't publish data when not leader."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="media-storage", interface="media_storage")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirer_data = MediaStorageRequirerData(instance_name="radarr")
        mgr.charm.requirer.publish_data(requirer_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("media-storage")[0]
    assert "config" not in relation_out.local_app_data
