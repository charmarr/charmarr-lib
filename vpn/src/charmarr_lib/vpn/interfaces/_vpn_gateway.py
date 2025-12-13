# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""VPN gateway interface for VXLAN overlay routing through a VPN gateway."""

from typing import Any

from ops import EventBase, EventSource, Object, ObjectEvents
from pydantic import BaseModel, Field, ValidationError

from charmarr_lib.vpn.constants import DEFAULT_VXLAN_ID, DEFAULT_VXLAN_IP_NETWORK


class VPNGatewayProviderData(BaseModel):
    """Data published by VPN gateway provider."""

    routing_method: str = Field(
        default="pod-gateway",
        description="Routing method: 'pod-gateway' (VXLAN overlay)",
    )
    gateway_dns_name: str = Field(
        description="Service FQDN for client DNS resolution",
    )
    vxlan_id: int = Field(
        default=DEFAULT_VXLAN_ID,
        ge=1,
        le=16777215,
        description="VXLAN tunnel ID (1-16777215)",
    )
    vxlan_ip_network: str = Field(
        default=DEFAULT_VXLAN_IP_NETWORK,
        description="First 3 octets of VXLAN subnet",
    )
    cluster_cidrs: str = Field(
        description="Comma-separated CIDRs to NOT route through VPN",
    )
    vpn_connected: bool = Field(
        default=False,
        description="Whether VPN tunnel is established",
    )
    external_ip: str | None = Field(
        default=None,
        description="Current VPN exit IP for verification",
    )
    instance_name: str = Field(
        description="Juju application name of the gateway",
    )


class VPNGatewayRequirerData(BaseModel):
    """Data published by VPN gateway requirers."""

    instance_name: str = Field(
        description="Juju application name of the requirer",
    )


class VPNGatewayChangedEvent(EventBase):
    """Event emitted when vpn-gateway relation state changes."""

    pass


class VPNGatewayProvider(Object):
    """Provider side of vpn-gateway interface (passive - no events)."""

    def __init__(self, charm: Any, relation_name: str = "vpn-gateway") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish_data(self, data: VPNGatewayProviderData) -> None:
        """Publish provider data to all relations."""
        if not self._charm.unit.is_leader():
            return

        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_connected_clients(self) -> list[str]:
        """Get list of connected requirer application names."""
        clients = []
        for relation in self._charm.model.relations.get(self._relation_name, []):
            try:
                app_data = relation.data[relation.app]
                if app_data and "config" in app_data:
                    data = VPNGatewayRequirerData.model_validate_json(app_data["config"])
                    clients.append(data.instance_name)
            except (ValidationError, KeyError):
                continue
        return clients

    def is_ready(self) -> bool:
        """Check if provider has any relations."""
        return len(self._charm.model.relations.get(self._relation_name, [])) > 0


class VPNGatewayRequirerEvents(ObjectEvents):
    """Events emitted by VPNGatewayRequirer."""

    changed = EventSource(VPNGatewayChangedEvent)


class VPNGatewayRequirer(Object):
    """Requirer side of vpn-gateway interface."""

    on = VPNGatewayRequirerEvents()  # type: ignore[assignment]

    def __init__(self, charm: Any, relation_name: str = "vpn-gateway") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name
        events = charm.on[relation_name]
        self.framework.observe(events.relation_changed, self._emit_changed)
        self.framework.observe(events.relation_broken, self._emit_changed)

    def _emit_changed(self, event: EventBase) -> None:
        self.on.changed.emit()

    def publish_data(self, data: VPNGatewayRequirerData) -> None:
        """Publish requirer data to the relation."""
        if not self._charm.unit.is_leader():
            return

        relation = self._charm.model.get_relation(self._relation_name)
        if relation:
            relation.data[self._charm.app]["config"] = data.model_dump_json()

    def get_gateway(self) -> VPNGatewayProviderData | None:
        """Get gateway provider data if available."""
        relation = self._charm.model.get_relation(self._relation_name)
        if not relation:
            return None

        try:
            provider_app = relation.app
            if provider_app:
                provider_data = relation.data[provider_app]
                if provider_data and "config" in provider_data:
                    return VPNGatewayProviderData.model_validate_json(provider_data["config"])
        except (ValidationError, KeyError):
            pass
        return None

    def is_ready(self) -> bool:
        """Check if gateway is available and VPN is connected."""
        gateway = self.get_gateway()
        return gateway is not None and gateway.vpn_connected
