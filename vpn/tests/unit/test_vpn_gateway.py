# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for vpn-gateway interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.vpn.interfaces import (
    VPNGatewayProvider,
    VPNGatewayProviderData,
    VPNGatewayRequirer,
    VPNGatewayRequirerData,
)


class ProviderCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"vpn-gateway": {"interface": "vpn_gateway"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = VPNGatewayProvider(self, "vpn-gateway")


class RequirerCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"vpn-gateway": {"interface": "vpn_gateway"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = VPNGatewayRequirer(self, "vpn-gateway")


def test_provider_publish_and_get_connected_clients():
    """Provider publishes data and retrieves connected clients."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    requirer_data = VPNGatewayRequirerData(instance_name="qbittorrent")
    relation = Relation(
        endpoint="vpn-gateway",
        interface="vpn_gateway",
        remote_app_data={"config": requirer_data.model_dump_json()},
    )
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = VPNGatewayProviderData(
            gateway_dns_name="gluetun.media.svc.cluster.local",
            cluster_cidrs="10.42.0.0/16,10.43.0.0/16",
            cluster_dns_ip="10.43.0.10",
            instance_name="gluetun",
            vpn_connected=True,
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()
        connected = mgr.charm.provider.get_connected_clients()

    relation_out = state_out.get_relations("vpn-gateway")[0]
    assert "config" in relation_out.local_app_data
    assert len(connected) == 1
    assert connected[0] == "qbittorrent"


def test_requirer_get_gateway():
    """Requirer retrieves gateway data when available."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = VPNGatewayProviderData(
        gateway_dns_name="gluetun.media.svc.cluster.local",
        cluster_cidrs="10.42.0.0/16,10.43.0.0/16",
        cluster_dns_ip="10.43.0.10",
        instance_name="gluetun",
        vpn_connected=True,
        external_ip="185.112.34.56",
        vxlan_id=42,
    )
    relation = Relation(
        endpoint="vpn-gateway",
        interface="vpn_gateway",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        retrieved = mgr.charm.requirer.get_gateway()

    assert retrieved is not None
    assert retrieved.gateway_dns_name == "gluetun.media.svc.cluster.local"
    assert retrieved.vpn_connected is True
    assert retrieved.external_ip == "185.112.34.56"


def test_requirer_is_ready_when_vpn_connected():
    """Requirer is_ready returns True when VPN is connected."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = VPNGatewayProviderData(
        gateway_dns_name="gluetun.media.svc.cluster.local",
        cluster_cidrs="10.42.0.0/16,10.43.0.0/16",
        cluster_dns_ip="10.43.0.10",
        instance_name="gluetun",
        vpn_connected=True,
    )
    relation = Relation(
        endpoint="vpn-gateway",
        interface="vpn_gateway",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is True


def test_requirer_is_ready_false_when_vpn_not_connected():
    """Requirer is_ready returns False when VPN is not connected."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = VPNGatewayProviderData(
        gateway_dns_name="gluetun.media.svc.cluster.local",
        cluster_cidrs="10.42.0.0/16,10.43.0.0/16",
        cluster_dns_ip="10.43.0.10",
        instance_name="gluetun",
        vpn_connected=False,
    )
    relation = Relation(
        endpoint="vpn-gateway",
        interface="vpn_gateway",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_requirer_is_ready_false_without_relation():
    """Requirer is_ready returns False when no relation exists."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)

    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_requirer_is_ready_false_without_provider_data():
    """Requirer is_ready returns False when provider hasn't published data."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(
        endpoint="vpn-gateway",
        interface="vpn_gateway",
        remote_app_data={},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is False


def test_provider_publish_data_non_leader():
    """Provider doesn't publish data when not leader."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="vpn-gateway", interface="vpn_gateway")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        provider_data = VPNGatewayProviderData(
            gateway_dns_name="gluetun.media.svc.cluster.local",
            cluster_cidrs="10.42.0.0/16,10.43.0.0/16",
            cluster_dns_ip="10.43.0.10",
            instance_name="gluetun",
        )
        mgr.charm.provider.publish_data(provider_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("vpn-gateway")[0]
    assert "config" not in relation_out.local_app_data


def test_requirer_publish_data_non_leader():
    """Requirer doesn't publish data when not leader."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="vpn-gateway", interface="vpn_gateway")
    state_in = State(leader=False, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        requirer_data = VPNGatewayRequirerData(instance_name="qbittorrent")
        mgr.charm.requirer.publish_data(requirer_data)
        state_out = mgr.run()

    relation_out = state_out.get_relations("vpn-gateway")[0]
    assert "config" not in relation_out.local_app_data


def test_provider_is_ready_with_relations():
    """Provider is_ready returns True when relations exist."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="vpn-gateway", interface="vpn_gateway")
    state_in = State(leader=True, relations=[relation])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.provider.is_ready() is True


def test_provider_is_ready_without_relations():
    """Provider is_ready returns False when no relations exist."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    state_in = State(leader=True, relations=[])

    with ctx(ctx.on.start(), state_in) as mgr:
        assert mgr.charm.provider.is_ready() is False
