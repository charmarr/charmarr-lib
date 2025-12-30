# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Charmarr-storage deployment step definitions."""

import os

import jubilant
from pytest_bdd import given, then

from charmarr_lib.testing import assert_app_active, wait_for_active_idle

STORAGE_CHARM = "charmarr-storage-k8s"
STORAGE_CHANNEL = os.environ.get("CHARMARR_STORAGE_CHANNEL", "latest/edge")


@given("charmarr-storage is deployed")
def deploy_storage_from_charmhub(juju: jubilant.Juju) -> None:
    """Deploy charmarr-storage from Charmhub with storage-class backend."""
    status = juju.status()
    if "charmarr-storage" in status.apps:
        return
    config = {
        "backend-type": "storage-class",
        "storage-class": "microk8s-hostpath",
        "size": "1Gi",
        "puid": "1000",
        "pgid": "1000",
    }
    juju.deploy(
        STORAGE_CHARM, app="charmarr-storage", channel=STORAGE_CHANNEL, trust=True, config=config
    )
    wait_for_active_idle(juju)


@then("the storage charm should be active")
def storage_active(juju: jubilant.Juju) -> None:
    """Assert storage charm is active."""
    assert_app_active(juju, "charmarr-storage")
