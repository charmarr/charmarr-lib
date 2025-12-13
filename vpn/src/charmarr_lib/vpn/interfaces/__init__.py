# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Juju relation interface implementations for VPN gateway."""

from charmarr_lib.vpn.interfaces._vpn_gateway import (
    VPNGatewayChangedEvent,
    VPNGatewayProvider,
    VPNGatewayProviderData,
    VPNGatewayRequirer,
    VPNGatewayRequirerData,
)

__all__ = [
    "VPNGatewayChangedEvent",
    "VPNGatewayProvider",
    "VPNGatewayProviderData",
    "VPNGatewayRequirer",
    "VPNGatewayRequirerData",
]
