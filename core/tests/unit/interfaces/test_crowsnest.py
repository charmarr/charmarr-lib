# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for crowsnest interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core.interfaces import (
    CrowsnestProvider,
    CrowsnestProviderData,
    CrowsnestRequirer,
)


class ProviderCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "radarr-k8s",
        "provides": {"crowsnest": {"interface": "crowsnest"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = CrowsnestProvider(self, "crowsnest")


class RequirerCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "charmarr-crowsnest-k8s",
        "requires": {"crowsnest": {"interface": "crowsnest"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = CrowsnestRequirer(self, "crowsnest")


def test_provider_publish_data():
    """Provider publishes the topology URL into the relation app-data."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="crowsnest", interface="crowsnest")
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        mgr.charm.provider.publish_data(
            CrowsnestProviderData(topology_url="http://radarr.charmarr.svc:9099/metrics")
        )
        state_out = mgr.run()

    relation_out = state_out.get_relations("crowsnest")[0]
    assert "config" in relation_out.local_app_data


def test_requirer_aggregates_multiple_providers():
    """Requirer returns one entry per related provider charm."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relations = [
        Relation(
            endpoint="crowsnest",
            interface="crowsnest",
            remote_app_name=app,
            remote_app_data={
                "config": CrowsnestProviderData(
                    topology_url=f"http://{app}.charmarr.svc:9099/metrics"
                ).model_dump_json()
            },
        )
        for app in ("radarr", "sonarr", "qbittorrent")
    ]

    with ctx(ctx.on.start(), State(leader=True, relations=relations)) as mgr:
        providers = mgr.charm.requirer.get_providers()
        ready = mgr.charm.requirer.is_ready()

    urls = {p.topology_url for p in providers}
    assert ready is True
    assert urls == {
        "http://radarr.charmarr.svc:9099/metrics",
        "http://sonarr.charmarr.svc:9099/metrics",
        "http://qbittorrent.charmarr.svc:9099/metrics",
    }


def test_requirer_not_ready_without_providers():
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.is_ready() is False
