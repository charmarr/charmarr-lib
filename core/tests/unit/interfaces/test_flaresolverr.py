# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for flaresolverr interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core.interfaces import (
    FlareSolverrProvider,
    FlareSolverrProviderData,
    FlareSolverrRequirer,
)


class ProviderCharm(CharmBase):
    """Minimal charm using FlareSolverrProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "flaresolverr-k8s",
        "provides": {"flaresolverr": {"interface": "flaresolverr"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = FlareSolverrProvider(self, "flaresolverr")


class RequirerCharm(CharmBase):
    """Minimal charm using FlareSolverrRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "prowlarr-k8s",
        "requires": {"flaresolverr": {"interface": "flaresolverr"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = FlareSolverrRequirer(self, "flaresolverr")


def test_provider_publish_data():
    """Test provider publishes FlareSolverr URL with 'config' key."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="flaresolverr", interface="flaresolverr")
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = FlareSolverrProviderData(url="http://flaresolverr-k8s:8191")
        mgr.charm.provider.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("flaresolverr")[0]
    assert "config" in relation_out.local_app_data


def test_provider_publish_data_non_leader():
    """Test provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="flaresolverr", interface="flaresolverr")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        data = FlareSolverrProviderData(url="http://flaresolverr-k8s:8191")
        mgr.charm.provider.publish_data(data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("flaresolverr")[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_get_provider():
    """Test requirer retrieves FlareSolverr URL from provider."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = FlareSolverrProviderData(url="http://flaresolverr-k8s:8191")
    relation = Relation(
        endpoint="flaresolverr",
        interface="flaresolverr",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        retrieved = mgr.charm.requirer.get_provider()

    assert retrieved is not None
    assert retrieved.url == "http://flaresolverr-k8s:8191"


def test_requirer_is_ready_with_provider():
    """Test requirer is_ready returns True when provider data exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = FlareSolverrProviderData(url="http://flaresolverr-k8s:8191")
    relation = Relation(
        endpoint="flaresolverr",
        interface="flaresolverr",
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
        endpoint="flaresolverr",
        interface="flaresolverr",
        remote_app_data={},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is False
