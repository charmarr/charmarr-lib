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

--------------------------------------------------------------------------
Why not a Pebble-managed service? (preempting the obvious question)
--------------------------------------------------------------------------

We considered making this a Pebble service. We cannot:

1. The CHARM container's Pebble plan (where this helper runs) is reserved
   for Juju's dispatch and is not user-extensible. Charm code can only add
   layers to containers declared in `containers:` in charmcraft.yaml.
2. Workloadless charms (e.g. `charmarr-storage-k8s`) have NO container at
   all to host a Pebble service. The charm container is the only option.
3. Pebble has no built-in static-file / Prometheus exposition server.
   See https://github.com/canonical/pebble/issues/118 (open, "needs design",
   filed 2022). Even that issue targets Pebble's own health-check state,
   not arbitrary application metrics.

So the alternative would be: declare a dedicated `charmarr-topology`
sidecar container in every charmarr charm, image pinned, Pebble layer
pushed. That adds ~20MB of RAM per pod x N charms and one Renovate-tracked
image per charm for what is structurally a 25-line static file server. Not
worth the cost.

If Pebble #118 lands, or if Juju ever exposes the charm container's
Pebble for user layers, swap the implementation here. The PUBLIC API
(`CharmarrTopology`, `reconcile()`, `scrape_job`, `port`) is intentionally
small and stays unchanged - the charms that consume this helper do not
need to be touched.
"""

import dataclasses
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

import ops
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class CharmarrTopologyRelation:
    """One Juju relation the charm wants to surface for topology checks."""

    name: str
    role: str  # "requires" or "provides"
    required: bool


class MetricSample(BaseModel):
    """A single Prometheus metric sample - labels + value."""

    labels: dict[str, str] = Field(default_factory=dict)
    value: float


class MetricFamily(BaseModel):
    """A Prometheus metric family - one HELP, one TYPE, N samples.

    The helper formats this into valid Prometheus exposition format. Use this
    via `CharmarrChargedTopology` when a charm wants to ship arbitrary
    charm-state metrics alongside topology on the same daemon endpoint.
    """

    name: str
    help: str
    type: Literal["gauge", "counter"] = "gauge"
    samples: list[MetricSample] = Field(default_factory=list)


ExtraExpositionCallback = Callable[[], Iterable[MetricFamily]]


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
        lines = list(self._exposition_lines())
        self.METRICS_FILE.write_text("\n".join(lines) + "\n")

    def _exposition_lines(self) -> Iterable[str]:
        """Yield every line written to the metrics file.

        Subclasses override this to inject additional series after the
        standard topology output.
        """
        yield from self._topology_lines()

    def _topology_lines(self) -> Iterable[str]:
        yield "# HELP charmarr_relation_bound Is the named relation currently bound (1) or unbound (0)"
        yield "# TYPE charmarr_relation_bound gauge"
        for rel in self._relations:
            bound = 1 if self._charm.model.relations.get(rel.name) else 0
            labels = (
                f'relation="{rel.name}",role="{rel.role}",required="{str(rel.required).lower()}"'
            )
            yield f"charmarr_relation_bound{{{labels}}} {bound}"

        yield "# HELP charmarr_relation_edge One series per bound (relation, from_app, to_app) peer"
        yield "# TYPE charmarr_relation_edge gauge"
        for rel in self._relations:
            for relation in self._charm.model.relations.get(rel.name, []):
                if rel.role == "provides":
                    from_app, to_app = relation.app.name, self._charm.app.name
                else:
                    from_app, to_app = self._charm.app.name, relation.app.name
                labels = f'relation="{rel.name}",from_app="{from_app}",to_app="{to_app}"'
                yield f"charmarr_relation_edge{{{labels}}} 1"

    def _ensure_server_running(self) -> None:
        pid = self._read_pid()
        if pid is not None and self._pid_alive(pid):
            return

        if not self.SERVER_SCRIPT.exists():
            self.SERVER_SCRIPT.write_text(_TOPOLOGY_SERVER_SCRIPT)

        # `start_new_session=True` is LOAD-BEARING: it places the child in a
        # new session/process group so it is detached from the charm hook's
        # process group. Without it, the daemon dies when the hook exits and
        # topology metrics vanish until the next reconcile event. Do NOT
        # remove this when refactoring (e.g. to asyncio or contextmanager-
        # based patterns) without a replacement detach mechanism.
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


class CharmarrChargedTopology(CharmarrTopology):
    """CharmarrTopology + arbitrary charm-state metrics on the same daemon.

    Use this when a charm wants to publish charm-internal state alongside
    the standard topology metrics on a single `metrics-endpoint` relation.
    Example: `charmarr-storage-k8s` ships consumer mount state and hardware
    device mount state via `extra_exposition`, served on the same port (9099)
    as the topology metrics.

    The callback returns an iterable of `MetricFamily` models. Each call is
    wrapped: any exception is logged and topology metrics still ship for
    that cycle - the extras are silently dropped.

    Example::

        self._topology = CharmarrChargedTopology(
            self,
            relations=[
                CharmarrTopologyRelation(
                    "media-storage", role="provides", required=False
                ),
            ],
            extra_exposition=self._build_storage_gauges,
        )

        def _build_storage_gauges(self) -> list[MetricFamily]:
            return [
                MetricFamily(
                    name="charmarr_storage_consumers_total",
                    help="Number of consumers currently bound via media-storage",
                    samples=[MetricSample(value=len(self._get_consumers()))],
                ),
            ]
    """

    def __init__(
        self,
        charm: ops.CharmBase,
        relations: list[CharmarrTopologyRelation],
        extra_exposition: ExtraExpositionCallback,
        port: int = CharmarrTopology.DEFAULT_PORT,
    ):
        super().__init__(charm, relations, port)
        self._extra_exposition = extra_exposition

    def _exposition_lines(self) -> Iterable[str]:
        yield from super()._exposition_lines()
        try:
            families = list(self._extra_exposition())
        except Exception:
            logger.exception("extra_exposition callback raised; topology metrics still shipped")
            return
        for family in families:
            yield from _format_metric_family(family)


def _format_metric_family(family: MetricFamily) -> Iterable[str]:
    yield f"# HELP {family.name} {family.help}"
    yield f"# TYPE {family.name} {family.type}"
    for sample in family.samples:
        if sample.labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sample.labels.items())
            yield f"{family.name}{{{label_str}}} {sample.value}"
        else:
            yield f"{family.name} {sample.value}"


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
