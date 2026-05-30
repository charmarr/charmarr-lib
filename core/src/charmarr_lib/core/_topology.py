# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Topology publisher for charmarr-crowsnest-k8s consumption.

Charms instantiate `CharmarrTopology` with the list of relations they want
to surface, then call `topology.reconcile()` from their own reconcile method.
On each reconcile the helper:

1. Writes a Prometheus exposition file under /tmp with two metric families:
   - `charmarr_relation_bound{relation, role, required}` (0/1) - is the relation bound at all
   - `charmarr_relation_edge{relation, from_app, to_app}` (1) - one series per bound peer

2. Ensures a tiny detached HTTP server is running in the charm container,
   serving that file at `/metrics` on the configured port (9099 by default).

The charm registers the helper's `scrape_job` with its MetricsEndpointProvider
and adds the topology port to its mesh UnitPolicy. Prometheus/otelcol scrapes
both the workload exporter sidecar AND this topology endpoint.

The helper does not observe any Juju events itself - lifecycle is owned by
the charm's reconciler, which already runs on the right set of events
(pebble_ready, config_changed, install, all relation events, etc.).
"""

import dataclasses
import logging
import os
import subprocess
import sys
from pathlib import Path

import ops

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CharmarrTopologyRelation:
    """One Juju relation the charm wants to surface for topology checks."""

    name: str
    role: str  # "requires" or "provides"
    required: bool


class CharmarrTopology(ops.Object):
    """Publishes charmarr_relation_bound + charmarr_relation_edge metrics.

    Hosted from inside the charm container - which always has Python - via a
    detached subprocess. The metrics file is regenerated on each `reconcile()`
    call; the HTTP server reads it on each scrape.

    Example::

        self._topology = CharmarrTopology(
            self,
            relations=[
                CharmarrTopologyRelation("download-client", role="requires", required=True),
                CharmarrTopologyRelation("media-storage", role="requires", required=True),
                CharmarrTopologyRelation("metrics-endpoint", role="provides", required=False),
            ],
        )

        # Add the topology endpoint to MetricsEndpointProvider's jobs list:
        MetricsEndpointProvider(
            self,
            jobs=[
                {"static_configs": [{"targets": [f"*:{METRICS_PORT}"]}]},
                self._topology.scrape_job,
            ],
            ...,
        )

        # Add the topology port to the mesh UnitPolicy alongside the exporter port:
        UnitPolicy(
            relation="metrics-endpoint",
            ports=[METRICS_PORT, self._topology.port],
        )

        # From the charm reconciler:
        def _reconcile(self, _event):
            ...
            self._topology.reconcile()
    """

    DEFAULT_PORT = 9099
    PID_FILE = Path("/tmp/charmarr-topology.pid")
    METRICS_FILE = Path("/tmp/charmarr-topology.prom")
    SERVER_SCRIPT = Path("/tmp/charmarr-topology-server.py")

    def __init__(
        self,
        charm: ops.CharmBase,
        relations: list[CharmarrTopologyRelation],
        port: int = DEFAULT_PORT,
    ):
        super().__init__(charm, f"charmarr-topology-{port}")
        self._charm = charm
        self._relations = list(relations)
        self._port = port

    @property
    def port(self) -> int:
        return self._port

    @property
    def scrape_job(self) -> dict:
        """Return the static scrape job spec to add to MetricsEndpointProvider."""
        return {"static_configs": [{"targets": [f"*:{self._port}"]}]}

    def reconcile(self) -> None:
        """Refresh the metrics file and ensure the daemon is running.

        Idempotent. Safe to call from any reconcile path.
        """
        self._write_metrics_file()
        self._ensure_server_running()

    def _write_metrics_file(self) -> None:
        lines: list[str] = [
            "# HELP charmarr_relation_bound Is the named relation currently bound (1) or unbound (0)",
            "# TYPE charmarr_relation_bound gauge",
        ]
        for rel in self._relations:
            bound = 1 if self._charm.model.relations.get(rel.name) else 0
            labels = (
                f'relation="{rel.name}",role="{rel.role}",required="{str(rel.required).lower()}"'
            )
            lines.append(f"charmarr_relation_bound{{{labels}}} {bound}")

        lines.append(
            "# HELP charmarr_relation_edge One series per bound (relation, from_app, to_app) peer"
        )
        lines.append("# TYPE charmarr_relation_edge gauge")
        for rel in self._relations:
            for relation in self._charm.model.relations.get(rel.name, []):
                if rel.role == "provides":
                    from_app, to_app = relation.app.name, self._charm.app.name
                else:
                    from_app, to_app = self._charm.app.name, relation.app.name
                labels = f'relation="{rel.name}",from_app="{from_app}",to_app="{to_app}"'
                lines.append(f"charmarr_relation_edge{{{labels}}} 1")

        self.METRICS_FILE.write_text("\n".join(lines) + "\n")

    def _ensure_server_running(self) -> None:
        pid = self._read_pid()
        if pid is not None and self._pid_alive(pid):
            return

        if not self.SERVER_SCRIPT.exists():
            self.SERVER_SCRIPT.write_text(_TOPOLOGY_SERVER_SCRIPT)

        proc = subprocess.Popen(
            [sys.executable, str(self.SERVER_SCRIPT), str(self._port), str(self.METRICS_FILE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.PID_FILE.write_text(str(proc.pid))
        logger.info(
            "Spawned charmarr-topology HTTP server on port %d (pid=%d)", self._port, proc.pid
        )

    def _read_pid(self) -> int | None:
        try:
            return int(self.PID_FILE.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True


_TOPOLOGY_SERVER_SCRIPT = '''#!/usr/bin/env python3
"""Detached HTTP server serving a single Prometheus exposition file."""
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


METRICS_FILE = sys.argv[2]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, _fmt, *_args):
        return

    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return
        try:
            with open(METRICS_FILE, "rb") as fh:
                body = fh.read()
        except FileNotFoundError:
            body = b""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(sys.argv[1])), _Handler).serve_forever()
'''
