# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for CharmarrTopology helper."""

from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import pytest
from ops import CharmBase
from scenario import Context, Relation, State

from charmarr_lib.core import CharmarrTopology, CharmarrTopologyRelation


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
    ctx.run(ctx.on.update_status(), state_in)

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
    """First event spawns; a subsequent event with a live pid does NOT respawn."""
    ctx = Context(TopologyCharm, meta=TopologyCharm.META)
    state = State(leader=True)

    state_after_first = ctx.run(ctx.on.update_status(), state)

    assert fake_popen.call_count == 1
    assert fake_popen.call_args.kwargs["start_new_session"] is True
    assert (_isolate_tmp_paths / "server.py").exists()
    assert (_isolate_tmp_paths / "topology.pid").read_text() == "12345"

    monkeypatch.setattr("charmarr_lib.core._topology.os.kill", lambda *_a, **_k: None)
    ctx.run(ctx.on.update_status(), state_after_first)

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
    ctx.run(ctx.on.update_status(), State(leader=True))

    assert fake_popen.call_count == 1
    assert (_isolate_tmp_paths / "topology.pid").read_text() == "12345"
