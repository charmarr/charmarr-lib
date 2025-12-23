# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Gateway client StatefulSet patching for pod-gateway.

Adds init container and sidecar to download client StatefulSets (qbittorrent-k8s,
sabnzbd-k8s) to route traffic through the VPN gateway via VXLAN overlay.

These are the "client" containers that connect TO the gateway - not to be confused
with API clients or download clients.

Based on validated configuration from vxlan-validation-plan.md.

Note: Client containers use a ConfigMap for settings (K8S_DNS_IPS,
NOT_ROUTED_TO_GATEWAY_CIDRS) with SPACE-separated CIDRs, unlike gateway
which uses COMMA-separated. This is a pod-gateway quirk.
"""

from typing import Any

from lightkube.models.apps_v1 import StatefulSet
from lightkube.models.core_v1 import (
    Capabilities,
    ConfigMap,
    ConfigMapVolumeSource,
    Container,
    EnvVar,
    SecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import ConfigMap as ConfigMapResource

from charmarr_lib.krm import K8sResourceManager, ReconcileResult
from charmarr_lib.vpn.constants import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData

_CONFIG_VOLUME_NAME = "pod-gateway-config"
_CONFIG_MOUNT_PATH = "/config"


def _build_gateway_client_init_container(gateway_dns_name: str) -> Container:
    """Build vpn-route-init container spec."""
    return Container(
        name=CLIENT_INIT_CONTAINER_NAME,
        image=POD_GATEWAY_IMAGE,
        command=["/bin/client_init.sh"],
        securityContext=SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"])),
        env=[EnvVar(name="gateway", value=gateway_dns_name)],
        volumeMounts=[VolumeMount(name=_CONFIG_VOLUME_NAME, mountPath=_CONFIG_MOUNT_PATH)],
    )


def _build_gateway_client_sidecar_container(gateway_dns_name: str) -> Container:
    """Build vpn-route-sidecar container spec."""
    return Container(
        name=CLIENT_SIDECAR_CONTAINER_NAME,
        image=POD_GATEWAY_IMAGE,
        command=["/bin/client_sidecar.sh"],
        securityContext=SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"])),
        env=[EnvVar(name="gateway", value=gateway_dns_name)],
        volumeMounts=[VolumeMount(name=_CONFIG_VOLUME_NAME, mountPath=_CONFIG_MOUNT_PATH)],
    )


def _build_config_volume(configmap_name: str) -> Volume:
    """Build ConfigMap volume for gateway client settings."""
    return Volume(
        name=_CONFIG_VOLUME_NAME,
        configMap=ConfigMapVolumeSource(name=configmap_name),
    )


def build_gateway_client_configmap_data(
    dns_server_ip: str,
    cluster_cidrs: str,
) -> dict[str, str]:
    """Build ConfigMap data for gateway client pod-gateway settings.

    Args:
        dns_server_ip: Kubernetes DNS server IP (e.g., "10.152.183.10").
        cluster_cidrs: Space-separated cluster CIDRs for bypass.
                       Note: Must be SPACE-separated for client, not comma!

    Returns:
        Dict with settings.sh content for ConfigMap data field.
    """
    settings = f'K8S_DNS_IPS="{dns_server_ip}"\nNOT_ROUTED_TO_GATEWAY_CIDRS="{cluster_cidrs}"'
    return {"settings.sh": settings}


def reconcile_gateway_client_configmap(
    manager: K8sResourceManager,
    configmap_name: str,
    namespace: str,
    dns_server_ip: str,
    cluster_cidrs: str,
) -> ReconcileResult:
    """Reconcile ConfigMap for gateway client pod-gateway settings.

    Creates or updates the ConfigMap containing settings for pod-gateway
    client containers (K8S_DNS_IPS, NOT_ROUTED_TO_GATEWAY_CIDRS).

    Args:
        manager: K8sResourceManager instance.
        configmap_name: Name for the ConfigMap.
        namespace: Kubernetes namespace.
        dns_server_ip: Kubernetes DNS server IP (e.g., "10.152.183.10").
        cluster_cidrs: Space-separated cluster CIDRs for bypass.

    Returns:
        ReconcileResult indicating if changes were made.
    """
    data = build_gateway_client_configmap_data(dns_server_ip, cluster_cidrs)

    configmap = ConfigMap(
        metadata=ObjectMeta(name=configmap_name, namespace=namespace),
        data=data,
    )

    existed = manager.exists(ConfigMapResource, configmap_name, namespace)
    manager.apply(configmap)

    if existed:
        return ReconcileResult(
            changed=True,
            message=f"Updated gateway client ConfigMap {configmap_name}",
        )
    return ReconcileResult(
        changed=True,
        message=f"Created gateway client ConfigMap {configmap_name}",
    )


def build_gateway_client_patch(
    data: VPNGatewayProviderData,
    configmap_name: str,
) -> dict[str, Any]:
    """Build strategic merge patch for gateway client StatefulSet."""
    init_container = _build_gateway_client_init_container(data.gateway_dns_name)
    sidecar = _build_gateway_client_sidecar_container(data.gateway_dns_name)
    config_volume = _build_config_volume(configmap_name)

    return {
        "spec": {
            "template": {
                "spec": {
                    "initContainers": [init_container.to_dict()],
                    "containers": [sidecar.to_dict()],
                    "volumes": [config_volume.to_dict()],
                }
            }
        }
    }


def is_gateway_client_patched(sts: StatefulSet) -> bool:
    """Check if StatefulSet already has pod-gateway client containers."""
    if sts.spec is None or sts.spec.template.spec is None:
        return False

    spec = sts.spec.template.spec

    has_init = False
    if spec.initContainers:
        has_init = any(c.name == CLIENT_INIT_CONTAINER_NAME for c in spec.initContainers)

    has_sidecar = False
    if spec.containers:
        has_sidecar = any(c.name == CLIENT_SIDECAR_CONTAINER_NAME for c in spec.containers)

    return has_init and has_sidecar


def reconcile_gateway_client(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    data: VPNGatewayProviderData,
    configmap_name: str,
) -> ReconcileResult:
    """Reconcile pod-gateway client containers on a StatefulSet.

    This function ensures the download client StatefulSet has the required
    pod-gateway containers to route traffic through the VPN gateway.

    Idempotent - if containers are already present, no changes are made.

    Note: The charm must create a ConfigMap with settings BEFORE calling this.
    Use build_gateway_client_configmap_data() to generate ConfigMap content.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        data: VPN gateway provider data from relation.
        configmap_name: Name of the ConfigMap containing pod-gateway settings.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.
    """
    sts = manager.get(StatefulSet, statefulset_name, namespace)

    if is_gateway_client_patched(sts):
        return ReconcileResult(changed=False, message="Gateway client containers already present")

    patch = build_gateway_client_patch(data, configmap_name)
    manager.patch(StatefulSet, statefulset_name, patch, namespace)

    return ReconcileResult(
        changed=True,
        message=f"Added pod-gateway client containers to {statefulset_name}",
    )
