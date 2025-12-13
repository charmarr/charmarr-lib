"""VPN gateway charm library for Kubernetes.

This package provides:
- VPN gateway Juju relation interface (from charmarr_lib.vpn.interfaces)
- StatefulSet patching utilities for pod-gateway integration
- NetworkPolicy kill switch implementation
"""

from charmarr_lib.vpn._k8s import (
    build_gateway_client_configmap_data,
    build_gateway_client_patch,
    build_gateway_patch,
    is_gateway_client_patched,
    is_gateway_patched,
    reconcile_gateway,
    reconcile_gateway_client,
)
from charmarr_lib.vpn.constants import (
    CLIENT_INIT_CONTAINER_NAME,
    CLIENT_SIDECAR_CONTAINER_NAME,
    DEFAULT_VPN_BLOCK_OTHER_TRAFFIC,
    DEFAULT_VPN_INTERFACE,
    DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP,
    DEFAULT_VXLAN_ID,
    DEFAULT_VXLAN_IP_NETWORK,
    GATEWAY_INIT_CONTAINER_NAME,
    GATEWAY_SIDECAR_CONTAINER_NAME,
    POD_GATEWAY_IMAGE,
)

__all__ = [
    "CLIENT_INIT_CONTAINER_NAME",
    "CLIENT_SIDECAR_CONTAINER_NAME",
    "DEFAULT_VPN_BLOCK_OTHER_TRAFFIC",
    "DEFAULT_VPN_INTERFACE",
    "DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP",
    "DEFAULT_VXLAN_ID",
    "DEFAULT_VXLAN_IP_NETWORK",
    "GATEWAY_INIT_CONTAINER_NAME",
    "GATEWAY_SIDECAR_CONTAINER_NAME",
    "POD_GATEWAY_IMAGE",
    "build_gateway_client_configmap_data",
    "build_gateway_client_patch",
    "build_gateway_patch",
    "is_gateway_client_patched",
    "is_gateway_patched",
    "reconcile_gateway",
    "reconcile_gateway_client",
]
