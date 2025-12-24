# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""NetworkPolicy kill switch for VPN gateway clients.

Creates a NetworkPolicy that blocks all egress traffic EXCEPT:
- Traffic to cluster pod CIDR (VXLAN-encapsulated traffic)
- Traffic to cluster service CIDR (K8s services)
- DNS traffic to kube-system (CoreDNS)

This is Layer 1 of the two-layer VPN kill switch. If VXLAN routing fails
(init container error, interface down, routes deleted), traffic cannot escape
to the internet because the destination IP isn't in the allowed cluster CIDRs.

Why VXLAN traffic passes through:
- VXLAN encapsulates external traffic with outer destination = gateway pod IP
- Gateway pod IP is in the cluster pod CIDR
- NetworkPolicy evaluates outer packet headers, sees cluster CIDR → ALLOWED

See ADR: networking/adr-004-vpn-kill-switch.md
Validated: vxlan-validation-plan.md (2025-12-11)
"""

from lightkube.models.meta_v1 import LabelSelector, ObjectMeta
from lightkube.models.networking_v1 import (
    IPBlock,
    NetworkPolicyEgressRule,
    NetworkPolicyPeer,
    NetworkPolicyPort,
    NetworkPolicySpec,
)
from lightkube.resources.networking_v1 import NetworkPolicy
from pydantic import BaseModel, Field

from charmarr_lib.krm import K8sResourceManager, ReconcileResult


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


def _build_kill_switch_policy(config: KillSwitchConfig) -> NetworkPolicy:
    """Build egress-only NetworkPolicy allowing cluster CIDRs and DNS to kube-system."""
    egress_rules: list[NetworkPolicyEgressRule] = []

    for cidr in config.cluster_cidrs:
        egress_rules.append(
            NetworkPolicyEgressRule(
                to=[NetworkPolicyPeer(ipBlock=IPBlock(cidr=cidr))],
            )
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

    if config is None:
        if not manager.exists(NetworkPolicy, policy_name, namespace):
            return ReconcileResult(
                changed=False,
                message=f"Kill switch NetworkPolicy {policy_name} not present",
            )
        manager.delete(NetworkPolicy, policy_name, namespace)
        return ReconcileResult(
            changed=True,
            message=f"Deleted kill switch NetworkPolicy {policy_name}",
        )

    policy = _build_kill_switch_policy(config)
    manager.apply(policy)

    return ReconcileResult(
        changed=True,
        message=f"Reconciled kill switch NetworkPolicy {policy_name}",
    )
