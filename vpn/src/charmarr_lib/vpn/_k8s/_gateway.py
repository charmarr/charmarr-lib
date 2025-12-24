# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Gateway-side StatefulSet patching for pod-gateway.

Adds init container and sidecar to the VPN gateway (gluetun-k8s) StatefulSet
to handle VXLAN tunnel creation and DHCP/DNS services for client pods.

Based on validated configuration from vxlan-validation-plan.md.

Note: Gateway containers use a ConfigMap mounted at /config with settings.sh
and nat.conf. The pod-gateway scripts source /config/settings.sh, so
environment variables alone are not sufficient.
"""

import hashlib
from typing import Any

from lightkube.models.core_v1 import (
    Capabilities,
    ConfigMapVolumeSource,
    Container,
    ContainerPort,
    SecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.resources.core_v1 import ConfigMap, Service

from charmarr_lib.krm import K8sResourceManager, ReconcileResult
from charmarr_lib.vpn.constants import (
    DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP,
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData

_CONFIG_VOLUME_NAME = "gateway-config"
_CONFIG_MOUNT_PATH = "/config"
_CONFIG_HASH_ANNOTATION = "charmarr.io/gateway-config-hash"


def _compute_config_hash(cm_data: dict[str, str]) -> str:
    """Compute short hash of ConfigMap data for pod restart triggering."""
    content = "".join(f"{k}={v}" for k, v in sorted(cm_data.items()))
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def _build_config_volume(configmap_name: str) -> Volume:
    """Build ConfigMap volume for gateway settings."""
    return Volume(
        name=_CONFIG_VOLUME_NAME,
        configMap=ConfigMapVolumeSource(name=configmap_name),
    )


def _build_gateway_init_container(input_cidrs: list[str]) -> Container:
    """Build gateway-init container spec.

    The init container:
    - Creates VXLAN tunnel interface
    - Sets up iptables forwarding rules
    - Adds iptables rules to accept INPUT from specified CIDRs
    - Requires privileged mode for sysctl ip_forward

    Args:
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
        volumeMounts=[VolumeMount(name=_CONFIG_VOLUME_NAME, mountPath=_CONFIG_MOUNT_PATH)],
    )


def _build_gateway_sidecar_container() -> Container:
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
        volumeMounts=[VolumeMount(name=_CONFIG_VOLUME_NAME, mountPath=_CONFIG_MOUNT_PATH)],
        ports=[
            ContainerPort(name="dhcp", containerPort=67, protocol="UDP"),
            ContainerPort(name="dns", containerPort=53, protocol="UDP"),
        ],
    )


def _build_gateway_configmap_data(data: VPNGatewayProviderData) -> dict[str, str]:
    """Build ConfigMap data for gateway pod-gateway settings."""
    settings = "\n".join(
        [
            f'VXLAN_ID="{data.vxlan_id}"',
            f'VXLAN_IP_NETWORK="{data.vxlan_ip_network}"',
            f'VXLAN_GATEWAY_FIRST_DYNAMIC_IP="{DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP}"',
        ]
    )
    return {
        "settings.sh": settings,
        "nat.conf": "",
    }


def _reconcile_gateway_configmap(
    manager: K8sResourceManager,
    configmap_name: str,
    namespace: str,
    data: VPNGatewayProviderData,
) -> None:
    """Reconcile ConfigMap for gateway pod-gateway settings."""
    cm_data = _build_gateway_configmap_data(data)

    configmap = ConfigMap(
        metadata=ObjectMeta(name=configmap_name, namespace=namespace),
        data=cm_data,
    )

    manager.apply(configmap)


def build_gateway_patch(
    configmap_name: str,
    input_cidrs: list[str],
    config_hash: str,
) -> dict[str, Any]:
    """Build strategic merge patch for gateway StatefulSet.

    Adds pod-gateway init container and sidecar to the VPN gateway StatefulSet.
    Includes a config hash annotation to trigger pod restart when ConfigMap changes.

    Args:
        configmap_name: Name of the ConfigMap containing pod-gateway settings.
        input_cidrs: List of CIDRs to allow INPUT from (pod, service, node CIDRs).
            Pass empty list if VPN solution handles INPUT rules natively.
        config_hash: Hash of ConfigMap data for pod restart triggering.

    Returns:
        Strategic merge patch dict for StatefulSet.

    Example:
        patch = build_gateway_patch("gluetun-gateway-settings", [], "abc12345")
        manager.patch(StatefulSet, "gluetun", patch, "vpn-gateway")
    """
    init_container = _build_gateway_init_container(input_cidrs)
    sidecar = _build_gateway_sidecar_container()
    config_volume = _build_config_volume(configmap_name)

    return {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        _CONFIG_HASH_ANNOTATION: config_hash,
                    }
                },
                "spec": {
                    "initContainers": [init_container.to_dict()],
                    "containers": [sidecar.to_dict()],
                    "volumes": [config_volume.to_dict()],
                },
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
    input_cidrs: list[str],
) -> ReconcileResult:
    """Reconcile pod-gateway containers on a VPN gateway StatefulSet.

    Ensures the VPN gateway StatefulSet has the required pod-gateway containers
    for VXLAN tunnel and DHCP/DNS services. Creates/updates a ConfigMap with
    pod-gateway settings and patches the StatefulSet with a config hash annotation
    to trigger pod restart when settings change.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        data: VPN gateway provider data containing VXLAN config.
        input_cidrs: List of CIDRs to allow INPUT from (pod, service, node CIDRs).
            Pass empty list if VPN solution handles INPUT rules natively
            (e.g., gluetun's /iptables/post-rules.txt).

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.
    """
    configmap_name = f"{statefulset_name}-gateway-settings"
    cm_data = _build_gateway_configmap_data(data)
    config_hash = _compute_config_hash(cm_data)

    _reconcile_gateway_configmap(manager, configmap_name, namespace, data)

    patch = build_gateway_patch(configmap_name, input_cidrs, config_hash)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)

    return ReconcileResult(
        changed=True,
        message=f"Reconciled pod-gateway on {statefulset_name}",
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
