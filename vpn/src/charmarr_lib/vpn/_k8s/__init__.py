# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""StatefulSet patching for pod-gateway VPN routing.

This module provides functions to patch Kubernetes StatefulSets with
pod-gateway containers for VXLAN overlay VPN routing.

Gateway-side patching (for gluetun-k8s):
- gateway-init: Creates VXLAN tunnel, sets up iptables forwarding
- gateway-sidecar: Runs DHCP and DNS server for client pods

Gateway client patching (for qbittorrent-k8s, sabnzbd-k8s):
- vpn-route-init: Creates VXLAN interface, gets IP via DHCP
- vpn-route-sidecar: Monitors gateway connectivity

See ADR: lib/adr-002-charmarr-vpn.md
"""

from charmarr_lib.vpn._k8s._gateway import (
    build_gateway_patch,
    is_gateway_patched,
    reconcile_gateway,
)
from charmarr_lib.vpn._k8s._gateway_client import (
    build_gateway_client_configmap_data,
    build_gateway_client_patch,
    is_gateway_client_patched,
    reconcile_gateway_client,
)

__all__ = [
    "build_gateway_client_configmap_data",
    "build_gateway_client_patch",
    "build_gateway_patch",
    "is_gateway_client_patched",
    "is_gateway_patched",
    "reconcile_gateway",
    "reconcile_gateway_client",
]
