# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for media-indexer interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core import MediaIndexer, MediaManager
from charmarr_lib.core.interfaces import (
    MediaIndexerProvider,
    MediaIndexerProviderData,
    MediaIndexerRequirer,
    MediaIndexerRequirerData,
)


class ProviderCharm(CharmBase):
    """Minimal charm using MediaIndexerProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"media-indexer": {"interface": "media_indexer"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = MediaIndexerProvider(self, "media-indexer")


class RequirerCharm(CharmBase):
    """Minimal charm using MediaIndexerRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"media-indexer": {"interface": "media_indexer"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = MediaIndexerRequirer(self, "media-indexer")


def test_provider_publish_data():
    """Test provider publishes data with correct key and serialization."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="media-indexer", interface="media_indexer")
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = MediaIndexerProviderData(
            api_url="http://prowlarr:9696",
            api_key_secret_id="secret://123",
            indexer=MediaIndexer.PROWLARR,
        )
        mgr.charm.provider.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations(relation.endpoint)[0]
    assert "config" in relation_out.local_app_data
    parsed = MediaIndexerProviderData.model_validate_json(relation_out.local_app_data["config"])
    assert parsed.indexer == MediaIndexer.PROWLARR


def test_provider_get_requirers_parses_valid_data():
    """Test provider correctly parses valid requirer data."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    requirer_data = MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret://456",
        manager=MediaManager.RADARR,
        instance_name="radarr-4k",
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirers = mgr.charm.provider.get_requirers()

    assert len(requirers) == 1
    assert requirers[0].manager == MediaManager.RADARR
    assert requirers[0].instance_name == "radarr-4k"


def test_provider_get_requirers_skips_invalid_data():
    """Test provider skips invalid requirer data without raising."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        remote_app_data={"config": "invalid json"},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirers = mgr.charm.provider.get_requirers()

    assert len(requirers) == 0


def test_provider_is_ready_with_valid_data():
    """Test provider is_ready logic when conditions are met."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    provider_data = MediaIndexerProviderData(
        api_url="http://prowlarr:9696",
        api_key_secret_id="secret://123",
        indexer=MediaIndexer.PROWLARR,
    )
    requirer_data = MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret://456",
        manager=MediaManager.RADARR,
        instance_name="radarr-4k",
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        local_app_data={"config": provider_data.model_dump_json()},
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.provider.is_ready() is True


def test_provider_is_ready_false_no_relations():
    """Test provider is_ready logic with no relations."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    state_in = State(leader=True, relations=[])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.provider.is_ready() is False


def test_provider_is_ready_false_no_requirers():
    """Test provider is_ready logic when no valid requirers exist."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    provider_data = MediaIndexerProviderData(
        api_url="http://prowlarr:9696",
        api_key_secret_id="secret://123",
        indexer=MediaIndexer.PROWLARR,
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        local_app_data={"config": provider_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.provider.is_ready() is False


def test_requirer_publish_data():
    """Test requirer publishes data with correct key and serialization."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="media-indexer", interface="media_indexer")
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = MediaIndexerRequirerData(
            api_url="http://radarr:7878",
            api_key_secret_id="secret://456",
            manager=MediaManager.RADARR,
            instance_name="radarr-4k",
        )
        mgr.charm.requirer.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations(relation.endpoint)[0]
    assert "config" in relation_out.local_app_data
    parsed = MediaIndexerRequirerData.model_validate_json(relation_out.local_app_data["config"])
    assert parsed.manager == MediaManager.RADARR


def test_requirer_get_provider_data_parses_valid():
    """Test requirer correctly parses valid provider data."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaIndexerProviderData(
        api_url="http://prowlarr:9696",
        api_key_secret_id="secret://123",
        indexer=MediaIndexer.PROWLARR,
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        remote_app_data={"config": provider_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        retrieved = mgr.charm.requirer.get_provider_data()

    assert retrieved is not None
    assert retrieved.indexer == MediaIndexer.PROWLARR


def test_requirer_get_provider_data_returns_none_no_relation():
    """Test requirer returns None when no relation exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    state_in = State(leader=True, relations=[])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.requirer.get_provider_data() is None


def test_requirer_get_provider_data_returns_none_invalid():
    """Test requirer returns None with invalid provider data."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        remote_app_data={"config": "invalid json"},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.requirer.get_provider_data() is None


def test_requirer_is_ready_with_valid_data():
    """Test requirer is_ready logic when both sides have published."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaIndexerProviderData(
        api_url="http://prowlarr:9696",
        api_key_secret_id="secret://123",
        indexer=MediaIndexer.PROWLARR,
    )
    requirer_data = MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret://456",
        manager=MediaManager.RADARR,
        instance_name="radarr-4k",
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        local_app_data={"config": requirer_data.model_dump_json()},
        remote_app_data={"config": provider_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.requirer.is_ready() is True


def test_requirer_is_ready_false_no_relation():
    """Test requirer is_ready logic with no relation."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    state_in = State(leader=True, relations=[])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_requirer_is_ready_false_no_provider_data():
    """Test requirer is_ready logic when provider hasn't published."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    requirer_data = MediaIndexerRequirerData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret://456",
        manager=MediaManager.RADARR,
        instance_name="radarr-4k",
    )
    relation = Relation(
        endpoint="media-indexer",
        interface="media_indexer",
        local_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_provider_publish_data_non_leader():
    """Test provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="media-indexer", interface="media_indexer")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = MediaIndexerProviderData(
            api_url="http://prowlarr:9696",
            api_key_secret_id="secret://123",
            indexer=MediaIndexer.PROWLARR,
        )
        mgr.charm.provider.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations(relation.endpoint)[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_publish_data_non_leader():
    """Test requirer doesn't publish data when not leader."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="media-indexer", interface="media_indexer")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = MediaIndexerRequirerData(
            api_url="http://radarr:7878",
            api_key_secret_id="secret://456",
            manager=MediaManager.RADARR,
            instance_name="radarr-4k",
        )
        mgr.charm.requirer.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations(relation.endpoint)[0]
    assert "config" not in relation_out.local_app_data
