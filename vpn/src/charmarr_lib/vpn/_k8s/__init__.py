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
- Optional kill switch NetworkPolicy (via killswitch=True parameter)

See ADRs:
- lib/adr-002-charmarr-vpn.md
- networking/adr-004-vpn-kill-switch.md
"""

from charmarr_lib.vpn._k8s._gateway import get_cluster_dns_ip, reconcile_gateway
from charmarr_lib.vpn._k8s._gateway_client import reconcile_gateway_client

__all__ = [
    "get_cluster_dns_ip",
    "reconcile_gateway",
    "reconcile_gateway_client",
]
