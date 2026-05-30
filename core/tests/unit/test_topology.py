# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for CharmarrTopology helper."""

from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core import (
    CharmarrChargedTopology,
    CharmarrTopology,
    CharmarrTopologyRelation,
    MetricFamily,
    MetricSample,
)


class TopologyCharm(CharmBase):
    """Minimal charm wiring CharmarrTopology with one of each role/required combination."""

    META: ClassVar[dict[str, object]] = {
        "name": "radarr",
        "requires": {
            "download-client": {"interface": "download_client"},
            "media-storage": {"interface": "media_storage"},
        },
        "provides": {
            "metrics-endpoint": {"interface": "prometheus_scrape"},
        },
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.topology = CharmarrTopology(
            self,
            relations=[
                CharmarrTopologyRelation("download-client", role="requires", required=True),
                CharmarrTopologyRelation("media-storage", role="requires", required=True),
                CharmarrTopologyRelation("metrics-endpoint", role="provides", required=False),
            ],
        )


@pytest.fixture(autouse=True)
def _isolate_tmp_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect topology paths into tmp_path so tests never touch /tmp."""
    monkeypatch.setattr(CharmarrTopology, "PID_FILE", tmp_path / "topology.pid")
    monkeypatch.setattr(CharmarrTopology, "METRICS_FILE", tmp_path / "topology.prom")
    monkeypatch.setattr(CharmarrTopology, "SERVER_SCRIPT", tmp_path / "server.py")
    return tmp_path


@pytest.fixture
def fake_popen(monkeypatch: pytest.MonkeyPatch):
    """Replace subprocess.Popen so tests never spawn a real daemon."""
    proc = MagicMock()
    proc.pid = 12345
    factory = MagicMock(return_value=proc)
    monkeypatch.setattr("charmarr_lib.core._topology.subprocess.Popen", factory)
    return factory


def test_metrics_output_shape(_isolate_tmp_paths: Path, fake_popen: MagicMock):
    """One required relation bound, one required unbound, one provides bound.

    Asserts all four contract claims in one go: bound=1/0 gauge, edge series for
    bound relations only, and the from_app/to_app flip for `provides` vs `requires`.
    """
    ctx = Context(TopologyCharm, meta=TopologyCharm.META)
    state_in = State(
        leader=True,
        relations=[
            Relation(
                endpoint="download-client",
                interface="download_client",
                remote_app_name="qbittorrent",
            ),
            Relation(
                endpoint="metrics-endpoint",
                interface="prometheus_scrape",
                remote_app_name="otelcol",
            ),
        ],
    )
    with ctx(ctx.on.update_status(), state_in) as mgr:
        mgr.charm.topology.reconcile()
        mgr.run()

    text = (_isolate_tmp_paths / "topology.prom").read_text()

    assert (
        'charmarr_relation_bound{relation="download-client",role="requires",required="true"} 1'
        in text
    )
    assert (
        'charmarr_relation_bound{relation="media-storage",role="requires",required="true"} 0'
        in text
    )
    assert (
        'charmarr_relation_bound{relation="metrics-endpoint",role="provides",required="false"} 1'
        in text
    )

    assert (
        'charmarr_relation_edge{relation="download-client",from_app="radarr",to_app="qbittorrent"} 1'
        in text
    )
    assert (
        'charmarr_relation_edge{relation="metrics-endpoint",from_app="otelcol",to_app="radarr"} 1'
        in text
    )
    assert "media-storage" not in text.split("charmarr_relation_edge")[1]


def test_daemon_spawn_is_idempotent(
    _isolate_tmp_paths: Path, fake_popen: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """First reconcile spawns; a subsequent reconcile with a live pid does NOT respawn."""
    monkeypatch.setattr("charmarr_lib.core._topology.os.kill", lambda *_a, **_k: None)
    ctx = Context(TopologyCharm, meta=TopologyCharm.META)

    with ctx(ctx.on.update_status(), State(leader=True)) as mgr:
        mgr.charm.topology.reconcile()
        mgr.charm.topology.reconcile()
        mgr.run()

    assert fake_popen.call_count == 1
    assert fake_popen.call_args.kwargs["start_new_session"] is True
    assert (_isolate_tmp_paths / "server.py").exists()
    assert (_isolate_tmp_paths / "topology.pid").read_text() == "12345"


class ChargedTopologyCharm(CharmBase):
    """Wraps CharmarrChargedTopology with a callback that emits two extra families."""

    META: ClassVar[dict[str, object]] = {
        "name": "storage",
        "provides": {"media-storage": {"interface": "media_storage"}},
    }

    def __init__(self, framework):
        super().__init__(framework)
        self.topology = CharmarrChargedTopology(
            self,
            relations=[
                CharmarrTopologyRelation("media-storage", role="provides", required=False),
            ],
            extra_exposition=self._extras,
        )

    def _extras(self) -> list[MetricFamily]:
        return [
            MetricFamily(
                name="charmarr_storage_consumers_total",
                help="Number of consumers currently bound via media-storage",
                samples=[MetricSample(value=2)],
            ),
            MetricFamily(
                name="charmarr_storage_pvc_mounted",
                help="Is the PVC mounted on each consumer (1/0)",
                samples=[
                    MetricSample(labels={"consumer": "radarr"}, value=1),
                    MetricSample(labels={"consumer": "sonarr"}, value=0),
                ],
            ),
        ]


def test_charged_topology_appends_extra_families(_isolate_tmp_paths: Path, fake_popen: MagicMock):
    """Subclass emits topology + extra families on the same endpoint."""
    ctx = Context(ChargedTopologyCharm, meta=ChargedTopologyCharm.META)
    with ctx(ctx.on.update_status(), State(leader=True)) as mgr:
        mgr.charm.topology.reconcile()
        mgr.run()

    text = (_isolate_tmp_paths / "topology.prom").read_text()

    assert "charmarr_relation_bound{" in text
    assert "# HELP charmarr_storage_consumers_total" in text
    assert "# TYPE charmarr_storage_consumers_total gauge" in text
    assert "charmarr_storage_consumers_total 2" in text
    assert 'charmarr_storage_pvc_mounted{consumer="radarr"} 1' in text
    assert 'charmarr_storage_pvc_mounted{consumer="sonarr"} 0' in text


def test_charged_topology_swallows_callback_errors(
    _isolate_tmp_paths: Path, fake_popen: MagicMock
):
    """If the callback raises, topology metrics still ship and the daemon still starts."""

    class BrokenCharm(CharmBase):
        META: ClassVar[dict[str, object]] = {
            "name": "broken",
            "provides": {"media-storage": {"interface": "media_storage"}},
        }

        def __init__(self, framework):
            super().__init__(framework)
            self.topology = CharmarrChargedTopology(
                self,
                relations=[
                    CharmarrTopologyRelation("media-storage", role="provides", required=False),
                ],
                extra_exposition=self._boom,
            )

        def _boom(self) -> list[MetricFamily]:
            raise RuntimeError("storage state unavailable")

    ctx = Context(BrokenCharm, meta=BrokenCharm.META)
    with ctx(ctx.on.update_status(), State(leader=True)) as mgr:
        mgr.charm.topology.reconcile()
        mgr.run()

    text = (_isolate_tmp_paths / "topology.prom").read_text()
    assert "charmarr_relation_bound{" in text
    assert "charmarr_storage" not in text
    assert fake_popen.call_count == 1


def test_daemon_respawns_when_pid_stale(
    _isolate_tmp_paths: Path, fake_popen: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """Stale pidfile (process no longer exists) triggers a respawn."""
    (_isolate_tmp_paths / "topology.pid").write_text("999")

    def _dead(*_a, **_k):
        raise ProcessLookupError

    monkeypatch.setattr("charmarr_lib.core._topology.os.kill", _dead)

    ctx = Context(TopologyCharm, meta=TopologyCharm.META)
    with ctx(ctx.on.update_status(), State(leader=True)) as mgr:
        mgr.charm.topology.reconcile()
        mgr.run()

    assert fake_popen.call_count == 1
    assert (_isolate_tmp_paths / "topology.pid").read_text() == "12345"
