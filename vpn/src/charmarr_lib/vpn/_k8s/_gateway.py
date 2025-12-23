# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Gateway-side StatefulSet patching for pod-gateway.

Adds init container and sidecar to the VPN gateway (gluetun-k8s) StatefulSet
to handle VXLAN tunnel creation and DHCP/DNS services for client pods.

Based on validated configuration from vxlan-validation-plan.md.
"""

from typing import Any

from lightkube.models.core_v1 import (
    Capabilities,
    Container,
    ContainerPort,
    EnvVar,
    SecurityContext,
)
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.resources.core_v1 import Service

from charmarr_lib.krm import K8sResourceManager, ReconcileResult
from charmarr_lib.vpn.constants import (
    DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP,
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData


def _build_gateway_env_vars(data: VPNGatewayProviderData, pod_cidr: str) -> list[EnvVar]:
    """Build environment variables for gateway containers.

    Args:
        data: VPN gateway provider data from relation.
        pod_cidr: Pod network CIDR for iptables rule (e.g., "10.1.0.0/16").
    """
    return [
        EnvVar(name="VXLAN_ID", value=str(data.vxlan_id)),
        EnvVar(name="VXLAN_IP_NETWORK", value=data.vxlan_ip_network),
        EnvVar(
            name="VXLAN_GATEWAY_FIRST_DYNAMIC_IP",
            value=str(DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP),
        ),
        EnvVar(name="VPN_INTERFACE", value="tun0"),
        EnvVar(name="VPN_BLOCK_OTHER_TRAFFIC", value="true"),
        EnvVar(name="NOT_ROUTED_TO_GATEWAY_CIDRS", value=data.cluster_cidrs),
        EnvVar(name="POD_CIDR", value=pod_cidr),
    ]


def _build_gateway_init_container(
    data: VPNGatewayProviderData,
    pod_cidr: str,
    input_cidrs: list[str],
) -> Container:
    """Build gateway-init container spec.

    The init container:
    - Creates VXLAN tunnel interface
    - Sets up iptables forwarding rules
    - Adds iptables rules to accept INPUT from specified CIDRs
    - Requires privileged mode for sysctl ip_forward

    Args:
        data: VPN gateway provider data from relation.
        pod_cidr: Pod network CIDR for env vars (e.g., "10.1.0.0/16").
        input_cidrs: List of CIDRs to allow INPUT from (pod, service, node CIDRs).
            Pass empty list if VPN solution handles INPUT rules natively
            (e.g., gluetun's /iptables/post-rules.txt).
    """
    if input_cidrs:
        iptables_cmds = " && ".join(
            f"iptables -I INPUT -i eth0 -s {cidr} -j ACCEPT" for cidr in input_cidrs
        )
        command_args = f"/bin/gateway_init.sh && {iptables_cmds}"
    else:
        command_args = "/bin/gateway_init.sh"

    return Container(
        name=GATEWAY_INIT_CONTAINER_NAME,
        image=POD_GATEWAY_IMAGE,
        command=["/bin/sh", "-c"],
        args=[command_args],
        securityContext=SecurityContext(privileged=True),
        env=_build_gateway_env_vars(data, pod_cidr),
    )


def _build_gateway_sidecar_container(data: VPNGatewayProviderData, pod_cidr: str) -> Container:
    """Build gateway-sidecar container spec.

    The sidecar container:
    - Runs DHCP server for client IP allocation
    - Runs DNS server for client pods
    - Requires NET_ADMIN capability (not full privileged)
    """
    return Container(
        name=GATEWAY_SIDECAR_CONTAINER_NAME,
        image=POD_GATEWAY_IMAGE,
        command=["/bin/gateway_sidecar.sh"],
        securityContext=SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"])),
        env=_build_gateway_env_vars(data, pod_cidr),
        ports=[
            ContainerPort(name="dhcp", containerPort=67, protocol="UDP"),
            ContainerPort(name="dns", containerPort=53, protocol="UDP"),
        ],
    )


def build_gateway_patch(
    data: VPNGatewayProviderData,
    pod_cidr: str,
    input_cidrs: list[str],
) -> dict[str, Any]:
    """Build strategic merge patch for gateway StatefulSet.

    Adds pod-gateway init container and sidecar to the VPN gateway StatefulSet.

    Args:
        data: VPN gateway provider data containing VXLAN config.
        pod_cidr: Pod network CIDR for env vars (e.g., "10.1.0.0/16").
        input_cidrs: List of CIDRs to allow INPUT from (pod, service, node CIDRs).
            Pass empty list if VPN solution handles INPUT rules natively.

    Returns:
        Strategic merge patch dict for StatefulSet.

    Example:
        cidrs = ["10.1.0.0/16", "10.152.183.0/24", "192.168.0.0/24"]
        patch = build_gateway_patch(provider_data, "10.1.0.0/16", cidrs)
        manager.patch(StatefulSet, "gluetun", patch, "vpn-gateway")
    """
    init_container = _build_gateway_init_container(data, pod_cidr, input_cidrs)
    sidecar = _build_gateway_sidecar_container(data, pod_cidr)

    return {
        "spec": {
            "template": {
                "spec": {
                    "initContainers": [init_container.to_dict()],
                    "containers": [sidecar.to_dict()],
                }
            }
        }
    }


def is_gateway_patched(sts: StatefulSet) -> bool:
    """Check if gateway StatefulSet already has pod-gateway containers.

    Args:
        sts: The StatefulSet to check.

    Returns:
        True if both gateway-init and gateway-sidecar are present.
    """
    if sts.spec is None or sts.spec.template.spec is None:
        return False

    spec = sts.spec.template.spec

    has_init = False
    if spec.initContainers:
        has_init = any(c.name == GATEWAY_INIT_CONTAINER_NAME for c in spec.initContainers)

    has_sidecar = False
    if spec.containers:
        has_sidecar = any(c.name == GATEWAY_SIDECAR_CONTAINER_NAME for c in spec.containers)

    return has_init and has_sidecar


def reconcile_gateway(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    data: VPNGatewayProviderData,
    pod_cidr: str,
    input_cidrs: list[str],
) -> ReconcileResult:
    """Reconcile pod-gateway containers on a VPN gateway StatefulSet.

    This function ensures the VPN gateway StatefulSet has the required
    pod-gateway containers for VXLAN tunnel and DHCP/DNS services.

    Idempotent - if containers are already present, no changes are made.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        data: VPN gateway provider data containing VXLAN config.
        pod_cidr: Pod network CIDR for env vars (e.g., "10.1.0.0/16").
        input_cidrs: List of CIDRs to allow INPUT from (pod, service, node CIDRs).
            Pass empty list if VPN solution handles INPUT rules natively.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.
    """
    sts = manager.get(StatefulSet, statefulset_name, namespace)

    if is_gateway_patched(sts):
        return ReconcileResult(changed=False, message="Gateway containers already present")

    patch = build_gateway_patch(data, pod_cidr, input_cidrs)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)

    return ReconcileResult(
        changed=True,
        message=f"Added pod-gateway containers to {statefulset_name}",
    )


def get_cluster_dns_ip(manager: K8sResourceManager) -> str:
    """Get the cluster DNS server IP from kube-dns service.

    Discovers the ClusterIP of the kube-dns service in kube-system namespace.
    This is needed for pod-gateway client settings to resolve the gateway hostname.

    Args:
        manager: K8sResourceManager instance.

    Returns:
        The kube-dns service ClusterIP (e.g., "10.152.183.10").

    Raises:
        ApiError: If kube-dns service doesn't exist or can't be accessed.
        ValueError: If kube-dns service has no ClusterIP.
    """
    svc = manager.get(Service, "kube-dns", "kube-system")

    if svc.spec is None or not svc.spec.clusterIP:
        raise ValueError("kube-dns service has no ClusterIP")

    return svc.spec.clusterIP
