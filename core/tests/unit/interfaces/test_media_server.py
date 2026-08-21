# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for media-server interface."""

from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core import MediaServer
from charmarr_lib.core.interfaces import (
    MediaServerProvider,
    MediaServerProviderData,
    MediaServerRequirer,
)


class ProviderCharm(CharmBase):
    """Minimal charm using MediaServerProvider."""

    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"media-server": {"interface": "media-server"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = MediaServerProvider(self, "media-server")


class RequirerCharm(CharmBase):
    """Minimal charm using MediaServerRequirer."""

    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"media-server": {"interface": "media-server", "limit": 1}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = MediaServerRequirer(self, "media-server")


def test_server_and_credentials_default_to_none():
    """Plex publishes without the new fields and stays valid."""
    data = MediaServerProviderData(name="plex", api_url="http://plex:32400")

    assert data.server is None
    assert data.credentials_secret_id is None


def test_provider_publishes_server_and_credentials():
    """Jellyfin publishes its type and the admin credentials secret ID."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="media-server", interface="media-server")

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        mgr.charm.provider.publish_data(
            MediaServerProviderData(
                name="jellyfin",
                api_url="http://jellyfin:8096",
                server=MediaServer.JELLYFIN,
                credentials_secret_id="secret://456",
            )
        )
        state_out = mgr.run()

    published = MediaServerProviderData.model_validate_json(
        state_out.get_relations("media-server")[0].local_app_data["config"]
    )
    assert published.server == MediaServer.JELLYFIN
    assert published.credentials_secret_id == "secret://456"


def test_requirer_reads_provider_data():
    """Requirer round-trips the provider payload."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    provider_data = MediaServerProviderData(
        name="jellyfin",
        api_url="http://jellyfin:8096",
        server=MediaServer.JELLYFIN,
        credentials_secret_id="secret://456",
    )
    relation = Relation(
        endpoint="media-server",
        interface="media-server",
        remote_app_data={"config": provider_data.model_dump_json()},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        assert mgr.charm.requirer.is_ready() is True
        provider = mgr.charm.requirer.get_provider()

    assert provider is not None
    assert provider.server == MediaServer.JELLYFIN
    assert provider.api_url == "http://jellyfin:8096"


def test_requirer_not_ready_without_relation():
    """No media server related means no provider data."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)

    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.is_ready() is False
        assert mgr.charm.requirer.get_provider() is None
