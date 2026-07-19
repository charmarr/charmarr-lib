# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Scenario tests for the netbird-enrollment interface."""

import json
from typing import ClassVar

from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.netbird.interfaces import (
    NetbirdEnrollmentCredentials,
    NetbirdEnrollmentProvider,
    NetbirdEnrollmentProviderData,
    NetbirdEnrollmentRequirer,
    NetbirdEnrollmentRequirerData,
)


class ProviderCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "provider-charm",
        "provides": {"netbird-enrollment": {"interface": "netbird_enrollment"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.provider = NetbirdEnrollmentProvider(self, "netbird-enrollment")


class RequirerCharm(CharmBase):
    META: ClassVar[dict[str, object]] = {
        "name": "requirer-charm",
        "requires": {"netbird-enrollment": {"interface": "netbird_enrollment"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.requirer = NetbirdEnrollmentRequirer(self, "netbird-enrollment")


def test_provider_publishes_flat_databag_keys():
    """Provider writes each field as a top-level databag key (not a JSON blob)."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="netbird-enrollment", interface="netbird_enrollment")

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        rel = mgr.charm.model.get_relation("netbird-enrollment")
        assert rel is not None
        mgr.charm.provider.publish(
            rel,
            NetbirdEnrollmentProviderData(
                management_url="https://netbird.example.com",
                credentials_secret_id="secret:abc123",
            ),
        )
        state_out = mgr.run()

    databag = state_out.get_relations("netbird-enrollment")[0].local_app_data
    assert json.loads(databag["management_url"]) == "https://netbird.example.com"
    assert json.loads(databag["credentials_secret_id"]) == "secret:abc123"
    assert "config" not in databag


def test_requirer_publishes_flat_databag_keys():
    """Requirer writes its instance name as a top-level databag key."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(endpoint="netbird-enrollment", interface="netbird_enrollment")

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        mgr.charm.requirer.publish(NetbirdEnrollmentRequirerData(instance_name="router-a"))
        state_out = mgr.run()

    databag = state_out.get_relations("netbird-enrollment")[0].local_app_data
    assert json.loads(databag["instance_name"]) == "router-a"
    assert "config" not in databag


def test_provider_reads_requirer_instances():
    """Provider deserialises each requirer's flat databag."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(
        endpoint="netbird-enrollment",
        interface="netbird_enrollment",
        remote_app_data={"instance_name": json.dumps("router-a")},
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        instances = mgr.charm.provider.get_requested_instances()

    assert [d.instance_name for d in instances.values()] == ["router-a"]


def test_requirer_reads_provider_enrollment():
    """Requirer deserialises the provider's flat databag."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(
        endpoint="netbird-enrollment",
        interface="netbird_enrollment",
        remote_app_data={
            "management_url": json.dumps("https://netbird.example.com"),
            "credentials_secret_id": json.dumps("secret:abc123"),
        },
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        enrollment = mgr.charm.requirer.get_enrollment()

    assert enrollment is not None
    assert enrollment.management_url == "https://netbird.example.com"
    assert enrollment.credentials_secret_id == "secret:abc123"


def test_requirer_tolerates_unknown_provider_keys():
    """Forward-compat: extra databag keys added by a newer provider are ignored."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)
    relation = Relation(
        endpoint="netbird-enrollment",
        interface="netbird_enrollment",
        remote_app_data={
            "management_url": json.dumps("https://netbird.example.com"),
            "credentials_secret_id": json.dumps("secret:abc123"),
            "future_field": json.dumps("ignored"),
        },
    )

    with ctx(ctx.on.start(), State(leader=True, relations=[relation])) as mgr:
        enrollment = mgr.charm.requirer.get_enrollment()

    assert enrollment is not None
    assert enrollment.management_url == "https://netbird.example.com"


def test_requirer_get_enrollment_none_without_relation():
    """Requirer returns None when no relation is present."""
    ctx = Context(RequirerCharm, meta=RequirerCharm.META)

    with ctx(ctx.on.start(), State(leader=True, relations=[])) as mgr:
        assert mgr.charm.requirer.get_enrollment() is None


def test_provider_non_leader_does_not_write():
    """Leader guard: a non-leader provider must not mutate the databag."""
    ctx = Context(ProviderCharm, meta=ProviderCharm.META)
    relation = Relation(endpoint="netbird-enrollment", interface="netbird_enrollment")

    with ctx(ctx.on.start(), State(leader=False, relations=[relation])) as mgr:
        rel = mgr.charm.model.get_relation("netbird-enrollment")
        assert rel is not None
        mgr.charm.provider.publish(
            rel,
            NetbirdEnrollmentProviderData(
                management_url="https://netbird.example.com",
                credentials_secret_id="secret:abc123",
            ),
        )
        state_out = mgr.run()

    assert dict(state_out.get_relations("netbird-enrollment")[0].local_app_data) == {}


def test_credentials_secret_content_roundtrip():
    """Credentials serialise to and from Juju secret content without loss."""
    creds = NetbirdEnrollmentCredentials(
        setup_key="AAAA-BBBB",
        api_token="nbp_token",
        api_token_expires_at="2027-07-19T00:00:00Z",
    )
    content = creds.to_secret_content()

    assert content == {
        "setup-key": "AAAA-BBBB",
        "api-token": "nbp_token",
        "api-token-expires-at": "2027-07-19T00:00:00Z",
    }
    assert NetbirdEnrollmentCredentials.from_secret_content(content) == creds


def test_credentials_secret_content_omits_absent_expiry():
    """Expiry is omitted from secret content when unset."""
    creds = NetbirdEnrollmentCredentials(setup_key="AAAA-BBBB", api_token="nbp_token")
    content = creds.to_secret_content()

    assert "api-token-expires-at" not in content
    assert NetbirdEnrollmentCredentials.from_secret_content(content) == creds
