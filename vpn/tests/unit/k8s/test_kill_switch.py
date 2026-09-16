# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for VPN kill switch NetworkPolicy."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from httpx import Response
from lightkube.core.exceptions import ApiError
from lightkube.resources.networking_v1 import NetworkPolicy

from charmarr_lib.krm import K8sResourceManager
from charmarr_lib.vpn._k8s._kill_switch import (
    CILIUM_CRD_NAME,
    CiliumNetworkPolicy,
    KillSwitchConfig,
    _build_cilium_apiserver_policy,  # pyright: ignore[reportPrivateUsage]
    _build_kill_switch_policy,  # pyright: ignore[reportPrivateUsage]
    _cnp_name,  # pyright: ignore[reportPrivateUsage]
    _policy_name,  # pyright: ignore[reportPrivateUsage]
    reconcile_kill_switch,
)


def _not_found() -> ApiError:
    return ApiError(response=Response(404, json={"code": 404, "message": "not found"}))


@pytest.fixture
def mock_client():
    """Mock lightkube client toggling Cilium CRD and NetworkPolicy presence."""
    m = MagicMock()
    m.cilium_installed = False
    m.networkpolicy_exists = False

    def _get(resource: Any, name: str, namespace: str | None = None) -> Any:
        cls_name = getattr(resource, "__name__", "")
        if cls_name == "CustomResourceDefinition":
            if m.cilium_installed:
                return MagicMock()
            raise _not_found()
        if m.networkpolicy_exists:
            return MagicMock()
        raise _not_found()

    def _delete(resource: Any, name: str, namespace: str | None = None, **_: Any) -> None:
        cls_name = getattr(resource, "__name__", "")
        if cls_name == "NetworkPolicy" and not m.networkpolicy_exists:
            raise _not_found()
        if cls_name == "CiliumNetworkPolicy" and not m.cilium_installed:
            raise _not_found()

    m.get.side_effect = _get
    m.delete.side_effect = _delete
    return m


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


def test_cnp_name():
    assert _cnp_name("qbittorrent") == "qbittorrent-vpn-killswitch-cilium"


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
    assert len(policy.spec.egress) == 4


def test_build_policy_egress_cidrs(config):
    """Egress rules include each cluster CIDR."""
    policy = _build_kill_switch_policy(config)
    assert policy.spec is not None
    assert policy.spec.egress is not None
    cidrs = [
        r.to[0].ipBlock.cidr  # type: ignore[union-attr]
        for r in policy.spec.egress
        if r.to and r.to[0].ipBlock is not None
    ]

    assert set(cidrs) == {"10.42.0.0/16", "10.96.0.0/12"}


def test_build_policy_allows_every_in_cluster_pod(config):
    """Cilium ignores ipBlock for pod destinations, so an all-namespace rule is needed."""
    policy = _build_kill_switch_policy(config)
    assert policy.spec is not None
    assert policy.spec.egress is not None

    rules = [
        r
        for r in policy.spec.egress
        if r.ports is None
        and r.to
        and r.to[0].namespaceSelector is not None
        and not r.to[0].namespaceSelector.matchLabels
    ]

    assert len(rules) == 1


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


def test_build_cilium_policy_targets_apiserver(config):
    """CiliumNetworkPolicy grants egress only to the kube-apiserver identity."""
    cnp = _build_cilium_apiserver_policy(config)

    assert cnp.metadata is not None
    assert cnp.metadata.name == "qbittorrent-vpn-killswitch-cilium"
    assert cnp.metadata.namespace == "downloads"
    assert cnp.spec == {
        "endpointSelector": {"matchLabels": {"app.kubernetes.io/name": "qbittorrent"}},
        "egress": [{"toEntities": ["kube-apiserver"]}],
    }


def test_reconcile_applies_policy(manager, mock_client, config):
    """Applies NetworkPolicy via server-side apply when Cilium is absent."""
    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config)

    assert result.changed is True
    assert "Reconciled" in result.message
    mock_client.apply.assert_called_once()


def test_reconcile_applies_cnp_when_cilium_installed(manager, mock_client, config):
    """Layers a CiliumNetworkPolicy alongside the NetworkPolicy when Cilium is present."""
    mock_client.cilium_installed = True

    reconcile_kill_switch(manager, "qbittorrent", "downloads", config)

    assert mock_client.apply.call_count == 2
    applied_types = {type(c.args[0]).__name__ for c in mock_client.apply.call_args_list}
    assert applied_types == {"NetworkPolicy", "CiliumNetworkPolicy"}


def test_reconcile_uses_cilium_crd_probe(manager, mock_client, config):
    """Cilium presence is probed via the CiliumNetworkPolicy CRD."""
    reconcile_kill_switch(manager, "qbittorrent", "downloads", config)

    crd_probes = [
        c
        for c in mock_client.get.call_args_list
        if getattr(c.args[0], "__name__", "") == "CustomResourceDefinition"
        and c.args[1] == CILIUM_CRD_NAME
    ]
    assert len(crd_probes) == 1


def test_reconcile_deletes_policy_when_config_none(manager, mock_client):
    """Deletes NetworkPolicy when config is None and it exists."""
    mock_client.networkpolicy_exists = True

    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)

    assert result.changed is True
    assert "Deleted" in result.message
    deleted_classes = {c.args[0] for c in mock_client.delete.call_args_list}
    assert deleted_classes == {NetworkPolicy}


def test_reconcile_deletes_both_when_config_none_and_cilium(manager, mock_client):
    """Deletes NetworkPolicy and CiliumNetworkPolicy on cleanup under Cilium."""
    mock_client.networkpolicy_exists = True
    mock_client.cilium_installed = True

    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)

    assert result.changed is True
    deleted_classes = {c.args[0] for c in mock_client.delete.call_args_list}
    assert deleted_classes == {NetworkPolicy, CiliumNetworkPolicy}


def test_reconcile_noop_when_config_none_and_not_exists(manager, mock_client):
    """No-op when config is None and neither policy exists."""
    result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)

    assert result.changed is False
