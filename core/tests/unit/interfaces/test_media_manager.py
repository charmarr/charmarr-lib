# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for media-manager interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core.enums import MediaManager, RequestManager
from charmarr_lib.core.interfaces import (
    MediaManagerProvider,
    MediaManagerProviderData,
    MediaManagerRequirer,
    MediaManagerRequirerData,
    QualityProfile,
)


class ProviderCharm(CharmBase):
    """Minimal charm using MediaManagerProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"media-manager": {"interface": "media_manager"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = MediaManagerProvider(self, "media-manager")


class RequirerCharm(CharmBase):
    """Minimal charm using MediaManagerRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"media-manager": {"interface": "media_manager"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = MediaManagerRequirer(self, "media-manager")


def test_provider_publish_and_get_requirers():
    """Test provider publishes data and retrieves connected requirers."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    requirer_data = MediaManagerRequirerData(
        requester=RequestManager.OVERSEERR,
        instance_name="overseerr",
    )
    relation = Relation(
        endpoint="media-manager",
        interface="media_manager",
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = MediaManagerProviderData(
            api_url="http://radarr-4k:7878",
            api_key_secret_id="secret:abc123",
            manager=MediaManager.RADARR,
            instance_name="radarr-4k",
            quality_profiles=[
                QualityProfile(id=1, name="HD-Bluray+WEB"),
                QualityProfile(id=2, name="UHD-Bluray+WEB"),
            ],
            root_folders=["/data/media/movies"],
            is_4k=True,
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()
        requirers = mgr.charm.provider.get_requirers()

    relation_out = state_out.get_relations("media-manager")[0]
    assert "config" in relation_out.local_app_data
    assert len(requirers) == 1
    assert requirers[0].instance_name == "overseerr"


def test_requirer_get_providers_with_quality_profiles():
    """Test requirer correctly retrieves provider data including quality profiles."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaManagerProviderData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret:xyz",
        manager=MediaManager.RADARR,
        instance_name="radarr-1080p",
        quality_profiles=[
            QualityProfile(id=1, name="HD-Bluray+WEB"),
            QualityProfile(id=2, name="Remux-1080p"),
        ],
        root_folders=["/data/media/movies", "/data/media/movies-remux"],
        is_4k=False,
    )
    relation = Relation(
        endpoint="media-manager",
        interface="media_manager",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        providers = mgr.charm.requirer.get_providers()

    assert len(providers) == 1
    retrieved = providers[0]
    assert retrieved.instance_name == "radarr-1080p"
    assert retrieved.is_4k is False
    assert len(retrieved.quality_profiles) == 2
    assert retrieved.quality_profiles[0].name == "HD-Bluray+WEB"
    assert len(retrieved.root_folders) == 2


def test_requirer_get_multiple_providers():
    """Test requirer correctly handles multiple media manager providers."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)

    # Create two different media manager providers
    radarr_data = MediaManagerProviderData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret:radarr",
        manager=MediaManager.RADARR,
        instance_name="radarr-1080p",
        quality_profiles=[QualityProfile(id=1, name="HD-Bluray+WEB")],
        root_folders=["/data/media/movies"],
        is_4k=False,
    )
    sonarr_data = MediaManagerProviderData(
        api_url="http://sonarr:8989",
        api_key_secret_id="secret:sonarr",
        manager=MediaManager.SONARR,
        instance_name="sonarr",
        quality_profiles=[QualityProfile(id=1, name="HD-Bluray+WEB")],
        root_folders=["/data/media/tv"],
    )

    state_in = State(
        leader=True,
        relations=[
            Relation(
                endpoint="media-manager",
                interface="media_manager",
                remote_app_data={"config": radarr_data.model_dump_json()},
            ),
            Relation(
                endpoint="media-manager",
                interface="media_manager",
                remote_app_data={"config": sonarr_data.model_dump_json()},
            ),
        ],
    )

    with ctx(ctx.on.start(), state_in) as mgr:
        providers = mgr.charm.requirer.get_providers()

    assert len(providers) == 2
    instance_names = {p.instance_name for p in providers}
    assert instance_names == {"radarr-1080p", "sonarr"}


def test_requirer_is_ready_with_provider():
    """Test requirer is_ready returns True when at least one provider exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaManagerProviderData(
        api_url="http://radarr:7878",
        api_key_secret_id="secret:abc",
        manager=MediaManager.RADARR,
        instance_name="radarr",
        quality_profiles=[QualityProfile(id=1, name="HD-Bluray+WEB")],
        root_folders=["/data/media/movies"],
    )
    relation = Relation(
        endpoint="media-manager",
        interface="media_manager",
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
        endpoint="media-manager",
        interface="media_manager",
        remote_app_data={},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_provider_publish_data_non_leader():
    """Test provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="media-manager", interface="media_manager")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = MediaManagerProviderData(
            api_url="http://radarr:7878",
            api_key_secret_id="secret:abc",
            manager=MediaManager.RADARR,
            instance_name="radarr",
            quality_profiles=[QualityProfile(id=1, name="HD-Bluray+WEB")],
            root_folders=["/data/media/movies"],
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("media-manager")[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_publish_data_non_leader():
    """Test requirer doesn't publish data when not leader."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="media-manager", interface="media_manager")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirer_data = MediaManagerRequirerData(
            requester=RequestManager.OVERSEERR,
            instance_name="overseerr",
        )
        mgr.charm.requirer.publish_data(requirer_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("media-manager")[0]
    assert "config" not in relation_out.local_app_data
