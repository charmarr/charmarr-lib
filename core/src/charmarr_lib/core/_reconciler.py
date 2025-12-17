# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Reconciler utilities for Juju charm event observation.

This module provides utilities for implementing the reconciler pattern in Juju charms.
The key insight is that most charm logic can be expressed as a reconcile function that
brings actual state in line with desired state, and this function should run on most
events.

Key components:
- observe_events(): Register a handler for multiple event types at once
- reconcilable_events_k8s: Default event set for K8s charms
- reconcilable_events_k8s_workloadless: Event set for charms without containers

Usage:
    class MyCharm(ops.CharmBase):
        def __init__(self, framework: ops.Framework):
            super().__init__(framework)
            observe_events(self, reconcilable_events_k8s, self._reconcile)

        def _reconcile(self, event: ops.EventBase) -> None:
            # Your reconciliation logic here
            pass

Based on: https://github.com/canonical/cos-lib/blob/main/src/cosl/reconciler.py
"""

import inspect
import itertools
from collections.abc import Callable, Iterable
from typing import Any, Final, cast

import ops

_CTR = itertools.count()

all_events: Final[set[type[ops.EventBase]]] = {
    ops.charm.PebbleCheckRecoveredEvent,
    ops.charm.PebbleCheckFailedEvent,
    ops.charm.ConfigChangedEvent,
    ops.charm.UpdateStatusEvent,
    ops.charm.PreSeriesUpgradeEvent,
    ops.charm.PostSeriesUpgradeEvent,
    ops.charm.LeaderElectedEvent,
    ops.charm.LeaderSettingsChangedEvent,
    ops.charm.RelationCreatedEvent,
    ops.charm.PebbleReadyEvent,
    ops.charm.RelationJoinedEvent,
    ops.charm.RelationChangedEvent,
    ops.charm.RelationDepartedEvent,
    ops.charm.RelationBrokenEvent,
    ops.charm.StorageAttachedEvent,
    ops.charm.StorageDetachingEvent,
    ops.charm.SecretChangedEvent,
    ops.charm.SecretRotateEvent,
    ops.charm.SecretRemoveEvent,
    ops.charm.SecretExpiredEvent,
    ops.charm.InstallEvent,
    ops.charm.StartEvent,
    ops.charm.RemoveEvent,
    ops.charm.StopEvent,
    ops.charm.UpgradeCharmEvent,
    ops.charm.PebbleCustomNoticeEvent,
}

reconcilable_events_k8s: Final[set[type[ops.EventBase]]] = all_events.difference(
    {
        # Custom notices often need specific handling
        ops.charm.PebbleCustomNoticeEvent,
        # Reconciling towards "up" state during removal is harmful
        ops.charm.RemoveEvent,
        # This is the only chance to detect upgrades and perform migration logic
        ops.charm.UpgradeCharmEvent,
    }
)

reconcilable_events_k8s_workloadless: Final[set[type[ops.EventBase]]] = (
    reconcilable_events_k8s.difference(
        {
            # Workload-less charms don't have Pebble containers
            ops.charm.PebbleCheckRecoveredEvent,
            ops.charm.PebbleCheckFailedEvent,
            ops.charm.PebbleReadyEvent,
        }
    )
)


def observe_events[EventT: type[ops.EventBase]](
    charm: ops.CharmBase,
    events: Iterable[EventT],
    handler: Callable[[Any], None] | Callable[[], None],
) -> None:
    """Observe all events that are subtypes of a given list using the provided handler.

    This function simplifies the common pattern of observing many event types with
    the same handler (reconcile function).

    Args:
        charm: The charm instance.
        events: Event types to observe (e.g., reconcilable_events_k8s).
        handler: The handler function. Can be either:
            - A method of an ops.Object that takes an event parameter
            - A zero-argument callable (a proxy will be created)

    Examples:
        # Observe all reconcilable events with a method
        observe_events(self, reconcilable_events_k8s, self._reconcile)

        # Observe specific events
        observe_events(self, {ops.StartEvent, ops.ConfigChangedEvent}, self._on_config_event)

        # For workload-less charms (no Pebble events)
        observe_events(self, reconcilable_events_k8s_workloadless, self._reconcile)
    """
    evthandler: Callable[[Any], None]

    if not inspect.signature(handler).parameters:

        class _Observer(ops.Object):
            _key = f"_observer_proxy_{next(_CTR)}"

            def __init__(self) -> None:
                super().__init__(charm, key=self._key)
                setattr(charm.framework, self._key, self)

            def evt_handler(self, _: ops.EventBase) -> None:
                handler()  # type: ignore[call-arg]

        evthandler = _Observer().evt_handler
    else:
        evthandler = cast(Callable[[Any], None], handler)

    for bound_evt in charm.on.events().values():
        if any(issubclass(bound_evt.event_type, include_type) for include_type in events):
            charm.framework.observe(bound_evt, evthandler)
