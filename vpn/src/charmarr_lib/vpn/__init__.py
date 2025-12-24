# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""VPN gateway charm library for Kubernetes."""

from charmarr_lib.vpn._k8s import (
    get_cluster_dns_ip,
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
    GATEWAY_DHCP_PORT,
    GATEWAY_DNS_PORT,
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
    "GATEWAY_DHCP_PORT",
    "GATEWAY_DNS_PORT",
    "GATEWAY_INIT_CONTAINER_NAME",
    "GATEWAY_SIDECAR_CONTAINER_NAME",
    "POD_GATEWAY_IMAGE",
    "get_cluster_dns_ip",
    "reconcile_gateway",
    "reconcile_gateway_client",
]
