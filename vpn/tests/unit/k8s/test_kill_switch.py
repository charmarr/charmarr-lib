# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for VPN kill switch NetworkPolicy."""

from unittest.mock import MagicMock

import pytest
from httpx import Response
from lightkube.core.exceptions import ApiError

from charmarr_lib.krm import K8sResourceManager
from charmarr_lib.vpn._k8s import KillSwitchConfig, reconcile_kill_switch
from charmarr_lib.vpn._k8s._kill_switch import (
    _build_kill_switch_policy,  # pyright: ignore[reportPrivateUsage]
    _policy_name,  # pyright: ignore[reportPrivateUsage]
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def manager(mock_client):
    return K8sResourceManager(client=mock_client)


@pytest.fixture
def config():
    return KillSwitchConfig(
        app_name="qbittorrent",
        namespace="downloads",
        cluster_cidrs=["10.42.0.0/16", "10.96.0.0/12"],
    )


def test_policy_name():
    assert _policy_name("qbittorrent") == "qbittorrent-vpn-killswitch"


def test_build_policy_structure(config):
    """Policy has correct metadata, selector, and egress rules."""
    policy = _build_kill_switch_policy(config)

    assert policy.metadata is not None
    assert policy.metadata.name == "qbittorrent-vpn-killswitch"
    assert policy.metadata.namespace == "downloads"
    assert policy.spec is not None
    assert policy.spec.podSelector is not None
    assert policy.spec.podSelector.matchLabels == {"app.kubernetes.io/name": "qbittorrent"}
    assert policy.spec.policyTypes == ["Egress"]
    assert policy.spec.egress is not None
    assert len(policy.spec.egress) == 3


def test_build_policy_egress_cidrs(config):
    """Egress rules include each cluster CIDR."""
    policy = _build_kill_switch_policy(config)
    assert policy.spec is not None
    assert policy.spec.egress is not None
    cidr_rules = [r for r in policy.spec.egress if r.ports is None]
    cidrs = [r.to[0].ipBlock.cidr for r in cidr_rules if r.to]  # type: ignore[union-attr]

    assert set(cidrs) == {"10.42.0.0/16", "10.96.0.0/12"}


def test_build_policy_egress_dns(config):
    """Egress rules include DNS to kube-system on port 53."""
    policy = _build_kill_switch_policy(config)
    assert policy.spec is not None
    assert policy.spec.egress is not None
    dns_rules = [r for r in policy.spec.egress if r.ports is not None]

    assert len(dns_rules) == 1
    assert dns_rules[0].to is not None
    assert dns_rules[0].to[0].namespaceSelector is not None
    assert dns_rules[0].to[0].namespaceSelector.matchLabels == {
        "kubernetes.io/metadata.name": "kube-system"
    }
    assert dns_rules[0].ports is not None
    ports = {(p.protocol, p.port) for p in dns_rules[0].ports}
    assert ports == {("UDP", 53), ("TCP", 53)}


def test_reconcile_applies_policy(manager, mock_client, config):
    """Applies policy via server-side apply."""
    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config)

    assert result.changed is True
    assert "Reconciled" in result.message
    mock_client.apply.assert_called_once()


def test_reconcile_deletes_policy_when_config_none(manager, mock_client):
    """Deletes policy when config is None and it exists."""
    mock_client.get.return_value = MagicMock()

    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)

    assert result.changed is True
    assert "Deleted" in result.message
    mock_client.delete.assert_called_once()


def test_reconcile_noop_when_config_none_and_not_exists(manager, mock_client):
    """No-op when config is None and policy doesn't exist."""
    mock_client.get.side_effect = ApiError(
        response=Response(404, json={"code": 404, "message": "not found"})
    )

    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)

    assert result.changed is False
    mock_client.delete.assert_not_called()
