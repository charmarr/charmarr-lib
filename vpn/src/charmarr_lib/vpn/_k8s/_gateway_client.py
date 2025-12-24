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

import hashlib
from typing import Any

from lightkube.models.core_v1 import (
    Capabilities,
    ConfigMapVolumeSource,
    Container,
    EnvVar,
    SecurityContext,
    Volume,
    VolumeMount,
)
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.resources.core_v1 import ConfigMap

from charmarr_lib.krm import K8sResourceManager, ReconcileResult
from charmarr_lib.vpn.constants import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData

_CONFIG_VOLUME_NAME = "pod-gateway-config"
_CONFIG_MOUNT_PATH = "/config"
_CONFIG_HASH_ANNOTATION = "charmarr.io/gateway-client-config-hash"


def _compute_config_hash(cm_data: dict[str, str]) -> str:
    """Compute short hash of ConfigMap data for pod restart triggering."""
    content = "".join(f"{k}={v}" for k, v in sorted(cm_data.items()))
    return hashlib.sha256(content.encode()).hexdigest()[:8]


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
    vxlan_id: int,
    vxlan_ip_network: str,
) -> dict[str, str]:
    """Build ConfigMap data for gateway client pod-gateway settings.

    Args:
        dns_server_ip: Kubernetes DNS server IP (e.g., "10.152.183.10").
        cluster_cidrs: Cluster CIDRs for bypass (comma or space-separated).
                       Will be normalized to space-separated for pod-gateway.
        vxlan_id: VXLAN tunnel ID (must match gateway).
        vxlan_ip_network: First 3 octets of VXLAN subnet (must match gateway).

    Returns:
        Dict with settings.sh content for ConfigMap data field.
    """
    cidrs_normalized = " ".join(c.strip() for c in cluster_cidrs.replace(",", " ").split())
    settings = "\n".join(
        [
            f'K8S_DNS_IPS="{dns_server_ip}"',
            f'NOT_ROUTED_TO_GATEWAY_CIDRS="{cidrs_normalized}"',
            f'VXLAN_ID="{vxlan_id}"',
            f'VXLAN_IP_NETWORK="{vxlan_ip_network}"',
        ]
    )
    return {"settings.sh": settings}


def reconcile_gateway_client_configmap(
    manager: K8sResourceManager,
    configmap_name: str,
    namespace: str,
    data: VPNGatewayProviderData | None,
) -> ReconcileResult:
    """Reconcile ConfigMap for gateway client pod-gateway settings.

    When data is provided, creates or updates the ConfigMap. When data is None,
    deletes the ConfigMap if it exists.

    Args:
        manager: K8sResourceManager instance.
        configmap_name: Name for the ConfigMap.
        namespace: Kubernetes namespace.
        data: VPN gateway provider data, or None to delete the ConfigMap.

    Returns:
        ReconcileResult indicating if changes were made.
    """
    if data is None:
        if not manager.exists(ConfigMap, configmap_name, namespace):
            return ReconcileResult(
                changed=False,
                message=f"Gateway client ConfigMap {configmap_name} not present",
            )
        manager.delete(ConfigMap, configmap_name, namespace)
        return ReconcileResult(
            changed=True,
            message=f"Deleted gateway client ConfigMap {configmap_name}",
        )

    cm_data = build_gateway_client_configmap_data(
        data.cluster_dns_ip, data.cluster_cidrs, data.vxlan_id, data.vxlan_ip_network
    )

    configmap = ConfigMap(
        metadata=ObjectMeta(name=configmap_name, namespace=namespace),
        data=cm_data,
    )

    manager.apply(configmap)

    return ReconcileResult(
        changed=True,
        message=f"Reconciled gateway client ConfigMap {configmap_name}",
    )


def build_gateway_client_patch(
    data: VPNGatewayProviderData,
    configmap_name: str,
    config_hash: str,
) -> dict[str, Any]:
    """Build strategic merge patch for gateway client StatefulSet.

    Includes a config hash annotation to trigger pod restart when settings change.
    """
    init_container = _build_gateway_client_init_container(data.gateway_dns_name)
    sidecar = _build_gateway_client_sidecar_container(data.gateway_dns_name)
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


def _build_gateway_client_cleanup_patch() -> dict[str, Any]:
    """Build patch to remove gateway client containers, volume, and annotation."""
    return {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        _CONFIG_HASH_ANNOTATION: None,
                    }
                },
                "spec": {
                    "initContainers": [{"$patch": "delete", "name": CLIENT_INIT_CONTAINER_NAME}],
                    "containers": [{"$patch": "delete", "name": CLIENT_SIDECAR_CONTAINER_NAME}],
                    "volumes": [{"$patch": "delete", "name": _CONFIG_VOLUME_NAME}],
                },
            }
        }
    }


def reconcile_gateway_client(
    manager: K8sResourceManager,
    statefulset_name: str,
    namespace: str,
    data: VPNGatewayProviderData | None,
    configmap_name: str,
) -> ReconcileResult:
    """Reconcile pod-gateway client containers on a StatefulSet.

    When data is provided, ensures the download client StatefulSet has the required
    pod-gateway containers. When data is None, removes containers, volume, and annotation.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        data: VPN gateway provider data from relation, or None to clean up.
        configmap_name: Name of the ConfigMap containing pod-gateway settings.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.
    """
    cm_data = (
        build_gateway_client_configmap_data(
            data.cluster_dns_ip, data.cluster_cidrs, data.vxlan_id, data.vxlan_ip_network
        )
        if data
        else {}
    )
    config_hash = _compute_config_hash(cm_data) if cm_data else None

    patch = (
        build_gateway_client_patch(data, configmap_name, config_hash)  # pyright: ignore[reportArgumentType]
        if data
        else _build_gateway_client_cleanup_patch()
    )
    manager.patch(StatefulSet, statefulset_name, patch, namespace)

    return ReconcileResult(
        changed=True,
        message=f"Reconciled pod-gateway client on {statefulset_name}",
    )
