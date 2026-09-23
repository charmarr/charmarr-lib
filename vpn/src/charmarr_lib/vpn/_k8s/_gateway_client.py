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
from charmarr_lib.vpn._k8s._kill_switch import KillSwitchConfig, reconcile_kill_switch
from charmarr_lib.vpn._k8s._utils import compute_config_hash
from charmarr_lib.vpn.constants import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)
from charmarr_lib.vpn.interfaces import VPNGatewayProviderData

_CONFIG_VOLUME_NAME = "pod-gateway-config"
_CONFIG_MOUNT_PATH = "/config"
_CONFIG_HASH_ANNOTATION = "charmarr.io/gateway-client-config-hash"


# The upstream init script drops the pod's default route before it creates vxlan0, but
# keys its re-entry check on vxlan0 being present. Anything that fails in between, a DNS
# lookup for the gateway being the likely one, leaves the pod with routes installed, no
# default route and no vxlan0. Every restart then reads an empty gateway from the missing
# default route and cannot recover, turning one transient failure into a permanent
# CrashLoopBackOff. Restoring the route from one the previous attempt installed puts the
# script back on its first-entry path.
# "gateway" is the environment variable the script reads as GATEWAY_NAME, so the
# restored address is held somewhere that cannot shadow it.
_INIT_COMMAND = """\
if ! ip route show default | grep -q .; then
    restored_default_gw=$(ip route show | awk '/ via / {print $3; exit}')
    if [ -n "$restored_default_gw" ]; then
        echo "Restoring default route via $restored_default_gw left by a failed attempt"
        ip route add default via "$restored_default_gw"
    fi
    unset restored_default_gw
fi
exec /bin/client_init.sh
"""


def _build_gateway_client_init_container(gateway_dns_name: str) -> Container:
    """Build vpn-route-init container spec."""
    return Container(
        name=CLIENT_INIT_CONTAINER_NAME,
        image=POD_GATEWAY_IMAGE,
        command=["/bin/sh", "-c", _INIT_COMMAND],
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


def _build_configmap_data(data: VPNGatewayProviderData) -> dict[str, str]:
    """Build ConfigMap data for gateway client pod-gateway settings."""
    cidrs_normalized = " ".join(c.strip() for c in data.cluster_cidrs.replace(",", " ").split())
    settings = "\n".join(
        [
            f'K8S_DNS_IPS="{data.cluster_dns_ip}"',
            f'NOT_ROUTED_TO_GATEWAY_CIDRS="{cidrs_normalized}"',
            f'VXLAN_ID="{data.vxlan_id}"',
            f'VXLAN_IP_NETWORK="{data.vxlan_ip_network}"',
            f'VXLAN_PORT="{data.vxlan_port}"',
        ]
    )
    return {"settings.sh": settings}


def _reconcile_configmap(
    manager: K8sResourceManager,
    configmap_name: str,
    namespace: str,
    data: VPNGatewayProviderData | None,
) -> None:
    """Reconcile ConfigMap for gateway client pod-gateway settings.

    When data is provided, creates or updates the ConfigMap. When data is None,
    deletes the ConfigMap if it exists.
    """
    if data is None:
        if manager.exists(ConfigMap, configmap_name, namespace):
            manager.delete(ConfigMap, configmap_name, namespace)
        return

    cm_data = _build_configmap_data(data)

    configmap = ConfigMap(
        metadata=ObjectMeta(name=configmap_name, namespace=namespace),
        data=cm_data,
    )

    manager.apply(configmap)


def _build_patch(
    data: VPNGatewayProviderData,
    configmap_name: str,
    config_hash: str,
) -> dict[str, Any]:
    """Build strategic merge patch for gateway client StatefulSet."""
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
    *,
    killswitch: bool = False,
) -> ReconcileResult:
    """Reconcile pod-gateway client on a StatefulSet.

    Handles all resources needed for VPN gateway client routing:
    - ConfigMap with pod-gateway settings
    - StatefulSet patch with init container and sidecar
    - NetworkPolicy kill switch (optional)

    When data is provided, creates/updates all resources. When data is None,
    cleans up all resources.

    Args:
        manager: K8sResourceManager instance.
        statefulset_name: Name of the StatefulSet (usually self.app.name).
        namespace: Kubernetes namespace (usually self.model.name).
        data: VPN gateway provider data from relation, or None to clean up.
        killswitch: If True, creates a NetworkPolicy that blocks egress except
            to cluster CIDRs. Prevents traffic leaks if VXLAN routing fails.

    Returns:
        ReconcileResult indicating if changes were made.

    Raises:
        ApiError: If the StatefulSet doesn't exist or patch fails.
    """
    configmap_name = f"{statefulset_name}-gateway-client-config"

    _reconcile_configmap(manager, configmap_name, namespace, data)

    if data:
        cm_data = _build_configmap_data(data)
        config_hash = compute_config_hash(cm_data)
        patch = _build_patch(data, configmap_name, config_hash)
    else:
        patch = _build_gateway_client_cleanup_patch()

    manager.patch(StatefulSet, statefulset_name, patch, namespace)

    if killswitch:
        if data:
            cidrs = [c.strip() for c in data.cluster_cidrs.replace(",", " ").split()]
            kill_config = KillSwitchConfig(
                app_name=statefulset_name,
                namespace=namespace,
                cluster_cidrs=cidrs,
            )
            reconcile_kill_switch(manager, statefulset_name, namespace, kill_config)
        else:
            reconcile_kill_switch(manager, statefulset_name, namespace, config=None)

    return ReconcileResult(
        changed=True,
        message=f"Reconciled pod-gateway client on {statefulset_name}",
    )
