# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Pod-gateway constants and defaults."""

# Pod-gateway container image
POD_GATEWAY_IMAGE = "ghcr.io/angelnu/pod-gateway:v1.13.0"

# VXLAN defaults
DEFAULT_VXLAN_ID = 42
DEFAULT_VXLAN_IP_NETWORK = "172.16.0"
DEFAULT_VXLAN_GATEWAY_FIRST_DYNAMIC_IP = 20

# Gateway environment variable defaults
DEFAULT_VPN_INTERFACE = "tun0"
DEFAULT_VPN_BLOCK_OTHER_TRAFFIC = True

# Container names for StatefulSet patching
GATEWAY_INIT_CONTAINER_NAME = "gateway-init"
GATEWAY_SIDECAR_CONTAINER_NAME = "gateway-sidecar"
CLIENT_INIT_CONTAINER_NAME = "vpn-route-init"
CLIENT_SIDECAR_CONTAINER_NAME = "vpn-route-sidecar"

# Gateway service ports (pod-gateway DHCP and DNS)
# These must be exposed via Juju set_ports() for client connectivity
GATEWAY_DHCP_PORT = 67
GATEWAY_DNS_PORT = 53

# Istio ambient mode ztunnel link-local address.
# ztunnel uses SNAT with this address for pod communication (probes, mesh traffic).
# VPN providers should include this in cluster_cidrs so client responses reach ztunnel.
# See ADR: networking/adr-005-istio-mesh-vpn-integration.md
ISTIO_ZTUNNEL_LINK_LOCAL = "169.254.7.127/32"
