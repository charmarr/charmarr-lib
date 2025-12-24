# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""StatefulSet patching and NetworkPolicy for pod-gateway VPN routing.

This module provides functions to patch Kubernetes StatefulSets with
pod-gateway containers for VXLAN overlay VPN routing, plus NetworkPolicy
kill switch for traffic protection.

Gateway-side patching (for gluetun-k8s):
- gateway-init: Creates VXLAN tunnel, sets up iptables forwarding
- gateway-sidecar: Runs DHCP and DNS server for client pods

Gateway client patching (for qbittorrent-k8s, sabnzbd-k8s):
- vpn-route-init: Creates VXLAN interface, gets IP via DHCP
- vpn-route-sidecar: Monitors gateway connectivity

Kill switch (for qbittorrent-k8s, sabnzbd-k8s):
- NetworkPolicy that blocks egress except cluster CIDRs + DNS
- Prevents traffic leaks if VXLAN routing fails

See ADRs:
- lib/adr-002-charmarr-vpn.md
- networking/adr-004-vpn-kill-switch.md
"""

from charmarr_lib.vpn._k8s._gateway import (
    build_gateway_patch,
    get_cluster_dns_ip,
    reconcile_gateway,
)
from charmarr_lib.vpn._k8s._gateway_client import (
    build_gateway_client_configmap_data,
    build_gateway_client_patch,
    reconcile_gateway_client,
    reconcile_gateway_client_configmap,
)
from charmarr_lib.vpn._k8s._kill_switch import (
    KillSwitchConfig,
    reconcile_kill_switch,
)

__all__ = [
    "KillSwitchConfig",
    "build_gateway_client_configmap_data",
    "build_gateway_client_patch",
    "build_gateway_patch",
    "get_cluster_dns_ip",
    "reconcile_gateway",
    "reconcile_gateway_client",
    "reconcile_gateway_client_configmap",
    "reconcile_kill_switch",
]
