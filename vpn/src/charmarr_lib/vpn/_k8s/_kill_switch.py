# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""NetworkPolicy kill switch for VPN gateway clients.

Creates a NetworkPolicy that blocks all egress traffic EXCEPT:
- Traffic to cluster pod CIDR (VXLAN-encapsulated traffic)
- Traffic to cluster service CIDR (K8s services)
- Traffic to any in-cluster pod, selected by namespace rather than CIDR
- DNS traffic to kube-system (CoreDNS)

This is Layer 1 of the two-layer VPN kill switch. If VXLAN routing fails
(init container error, interface down, routes deleted), traffic cannot escape
to the internet because the destination IP isn't in the allowed cluster CIDRs.

Why VXLAN traffic passes through:
- VXLAN encapsulates external traffic with outer destination = gateway pod IP
- Gateway pod IP is in the cluster pod CIDR
- NetworkPolicy evaluates outer packet headers, sees cluster CIDR → ALLOWED

On Cilium the standard NetworkPolicy above cannot cover the kube-apiserver:
Cilium tags in-cluster destinations with security identities (host,
remote-node, kube-apiserver) rather than CIDRs, so an ipBlock rule for the
node CIDR never matches. We layer a small CiliumNetworkPolicy alongside the
NetworkPolicy that grants egress to the kube-apiserver identity only, so
lightkube calls from the charm survive. On non-Cilium CNIs the CRD is absent
and the layer is skipped; Calico/Antrea/etc. already honor ipBlock for node
IPs via the operator-supplied cluster-cidrs.

See ADR: networking/adr-004-vpn-kill-switch.md
Validated: vxlan-validation-plan.md (2025-12-11)
"""

from typing import Any

from lightkube.generic_resource import create_namespaced_resource
from lightkube.models.meta_v1 import LabelSelector, ObjectMeta
from lightkube.models.networking_v1 import (
    IPBlock,
    NetworkPolicyEgressRule,
    NetworkPolicyPeer,
    NetworkPolicyPort,
    NetworkPolicySpec,
)
from lightkube.resources.apiextensions_v1 import CustomResourceDefinition
from lightkube.resources.networking_v1 import NetworkPolicy
from pydantic import BaseModel, Field

from charmarr_lib.krm import K8sResourceManager, ReconcileResult

CILIUM_CRD_NAME = "ciliumnetworkpolicies.cilium.io"

CiliumNetworkPolicy = create_namespaced_resource(
    group="cilium.io",
    version="v2",
    kind="CiliumNetworkPolicy",
    plural="ciliumnetworkpolicies",
)


class KillSwitchConfig(BaseModel):
    """Configuration for VPN kill switch NetworkPolicy."""

    app_name: str = Field(
        description="Application name for pod selector (app.kubernetes.io/name label)",
    )
    namespace: str = Field(
        description="Kubernetes namespace for the NetworkPolicy",
    )
    cluster_cidrs: list[str] = Field(
        description="List of cluster CIDRs to allow (pod CIDR, service CIDR)",
    )
    dns_namespace: str = Field(
        default="kube-system",
        description="Namespace containing DNS service (usually kube-system)",
    )


def _policy_name(app_name: str) -> str:
    """Generate NetworkPolicy name for an application."""
    return f"{app_name}-vpn-killswitch"


def _cnp_name(app_name: str) -> str:
    """Generate CiliumNetworkPolicy name for an application."""
    return f"{app_name}-vpn-killswitch-cilium"


def _cilium_available(manager: K8sResourceManager) -> bool:
    """Return True if the CiliumNetworkPolicy CRD is installed."""
    return manager.exists(CustomResourceDefinition, CILIUM_CRD_NAME)


def _build_cilium_apiserver_policy(config: KillSwitchConfig) -> Any:
    """CiliumNetworkPolicy granting egress to the kube-apiserver identity."""
    return CiliumNetworkPolicy(
        metadata=ObjectMeta(name=_cnp_name(config.app_name), namespace=config.namespace),
        spec={
            "endpointSelector": {
                "matchLabels": {"app.kubernetes.io/name": config.app_name},
            },
            "egress": [{"toEntities": ["kube-apiserver"]}],
        },
    )


def _build_kill_switch_policy(config: KillSwitchConfig) -> NetworkPolicy:
    """Build egress-only NetworkPolicy allowing cluster CIDRs and DNS to kube-system."""
    egress_rules: list[NetworkPolicyEgressRule] = []

    for cidr in config.cluster_cidrs:
        egress_rules.append(
            NetworkPolicyEgressRule(
                to=[NetworkPolicyPeer(ipBlock=IPBlock(cidr=cidr))],
            )
        )

    # Cilium resolves in-cluster destinations by security identity and does not
    # match ipBlock CIDRs against pod IPs, so the pod-CIDR rule above is a no-op
    # there and VXLAN traffic to the gateway is dropped. Selecting every namespace
    # expresses the same intent by identity. Calico already covered this via
    # ipBlock, so this grants nothing extra: external egress stays denied.
    egress_rules.append(
        NetworkPolicyEgressRule(to=[NetworkPolicyPeer(namespaceSelector=LabelSelector())])
    )

    egress_rules.append(
        NetworkPolicyEgressRule(
            to=[
                NetworkPolicyPeer(
                    namespaceSelector=LabelSelector(
                        matchLabels={"kubernetes.io/metadata.name": config.dns_namespace}
                    )
                )
            ],
            ports=[
                NetworkPolicyPort(protocol="UDP", port=53),
                NetworkPolicyPort(protocol="TCP", port=53),
            ],
        )
    )

    return NetworkPolicy(
        metadata=ObjectMeta(
            name=_policy_name(config.app_name),
            namespace=config.namespace,
        ),
        spec=NetworkPolicySpec(
            podSelector=LabelSelector(matchLabels={"app.kubernetes.io/name": config.app_name}),
            policyTypes=["Egress"],
            egress=egress_rules,
        ),
    )


def reconcile_kill_switch(
    manager: K8sResourceManager,
    app_name: str,
    namespace: str,
    config: KillSwitchConfig | None = None,
) -> ReconcileResult:
    """Reconcile VPN kill switch NetworkPolicy.

    When config is provided, creates or updates the NetworkPolicy.
    When config is None, deletes the NetworkPolicy if it exists.

    Uses server-side apply for clean ownership and idempotent updates.

    Args:
        manager: K8sResourceManager instance.
        app_name: Application name (used to derive policy name).
        namespace: Kubernetes namespace.
        config: Kill switch configuration, or None to remove the policy.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If NetworkPolicy creation/update/deletion fails.

    Example - create/update:
        config = KillSwitchConfig(
            app_name="qbittorrent",
            namespace="downloads",
            cluster_cidrs=["10.42.0.0/16", "10.96.0.0/12"],
        )
        result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config)

    Example - remove (when VPN relation is broken):
        result = reconcile_kill_switch(manager, "qbittorrent", "downloads", config=None)
    """
    policy_name = _policy_name(app_name)
    cnp_name = _cnp_name(app_name)
    cilium = _cilium_available(manager)

    if config is None:
        np_deleted = manager.delete(NetworkPolicy, policy_name, namespace)
        cnp_deleted = manager.delete(CiliumNetworkPolicy, cnp_name, namespace) if cilium else False
        if not np_deleted and not cnp_deleted:
            return ReconcileResult(
                changed=False,
                message=f"Kill switch for {app_name} not present",
            )
        return ReconcileResult(
            changed=True,
            message=f"Deleted kill switch for {app_name}",
        )

    manager.apply(_build_kill_switch_policy(config))
    if cilium:
        manager.apply(_build_cilium_apiserver_policy(config))

    return ReconcileResult(
        changed=True,
        message=f"Reconciled kill switch for {app_name}",
    )
