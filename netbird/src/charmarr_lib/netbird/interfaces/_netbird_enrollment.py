# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""netbird-enrollment interface (1:N).

The provider (core control-plane charm) hands each requirer the Management URL and a
Juju secret carrying a mesh setup key plus a scoped `network_admin` service-user token.
Requirers (routing peers, onboarders) use the setup key to join the mesh and the token
to drive the Management REST API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Self

from ops.framework import Object
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from ops import CharmBase, Relation

logger = logging.getLogger(__name__)


class NetbirdEnrollmentProviderData(BaseModel):
    """Provider (core) application databag — flat, one key per field."""

    model_config = ConfigDict(frozen=True)

    management_url: str = Field(description="Management API/gRPC URL agents connect to")
    credentials_secret_id: str = Field(
        description="Juju secret ID holding the setup key and scoped API token"
    )


class NetbirdEnrollmentRequirerData(BaseModel):
    """Requirer application databag — flat, one key per field."""

    model_config = ConfigDict(frozen=True)

    instance_name: str = Field(
        description="Requirer Juju app name; the provider names the service user after it"
    )


class NetbirdEnrollmentCredentials(BaseModel):
    """Payload stored inside the Juju secret referenced by the databag.

    Kept out of the relation databag because these are secrets. The provider charm
    owns the secret lifecycle; this model only (de)serialises its content.
    """

    model_config = ConfigDict(frozen=True)

    setup_key: str = Field(description="Mesh setup key for peer registration")
    api_token: str = Field(description="Scoped network_admin service-user PAT")
    api_token_expires_at: str | None = Field(
        default=None, description="ISO-8601 token expiry, for rotation tracking"
    )

    def to_secret_content(self) -> dict[str, str]:
        """Render as Juju secret content (all values are strings)."""
        content = {"setup-key": self.setup_key, "api-token": self.api_token}
        if self.api_token_expires_at is not None:
            content["api-token-expires-at"] = self.api_token_expires_at
        return content

    @classmethod
    def from_secret_content(cls, content: dict[str, str]) -> Self:
        """Parse Juju secret content back into credentials."""
        return cls(
            setup_key=content["setup-key"],
            api_token=content["api-token"],
            api_token_expires_at=content.get("api-token-expires-at"),
        )


class NetbirdEnrollmentProvider(Object):
    """Provider side of the netbird-enrollment interface (passive — no events)."""

    def __init__(self, charm: CharmBase, relation_name: str = "netbird-enrollment") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish(self, relation: Relation, data: NetbirdEnrollmentProviderData) -> None:
        """Publish enrollment data to a single relation (per-requirer credentials)."""
        if not self._charm.unit.is_leader():
            logger.debug("Not leader, skipping enrollment publish")
            return
        relation.save(data, self._charm.app)

    def get_requested_instances(self) -> dict[str, NetbirdEnrollmentRequirerData]:
        """Return each connected requirer's data, keyed by relation id as a string."""
        result: dict[str, NetbirdEnrollmentRequirerData] = {}
        for relation in self._charm.model.relations.get(self._relation_name, []):
            if not relation.app:
                continue
            try:
                result[str(relation.id)] = relation.load(
                    NetbirdEnrollmentRequirerData, relation.app
                )
            except Exception as e:
                logger.warning("Failed to load requirer databag on %s: %s", relation.id, e)
        return result


class NetbirdEnrollmentRequirer(Object):
    """Requirer side of the netbird-enrollment interface (passive — no events)."""

    def __init__(self, charm: CharmBase, relation_name: str = "netbird-enrollment") -> None:
        super().__init__(charm, relation_name)
        self._charm = charm
        self._relation_name = relation_name

    def publish(self, data: NetbirdEnrollmentRequirerData) -> None:
        """Publish requirer data to all relations."""
        if not self._charm.unit.is_leader():
            logger.debug("Not leader, skipping enrollment request publish")
            return
        for relation in self._charm.model.relations.get(self._relation_name, []):
            relation.save(data, self._charm.app)

    def get_enrollment(self) -> NetbirdEnrollmentProviderData | None:
        """Return the provider's enrollment data, or None if not yet available."""
        relation = self._charm.model.get_relation(self._relation_name)
        if relation is None:
            return None
        try:
            return relation.load(NetbirdEnrollmentProviderData, relation.app)
        except Exception as e:
            logger.warning("Failed to load provider enrollment databag: %s", e)
            return None
