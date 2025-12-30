# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Arr family charm testing utilities."""

import json
import logging
import os
from pathlib import Path

import jubilant
from pydantic import BaseModel
from pytest_jubilant import pack

from charmarr_lib.testing._charmcraft import get_oci_resources
from charmarr_lib.testing._juju import wait_for_active_idle

logger = logging.getLogger(__name__)

ARR_CHARMS = ["prowlarr-k8s", "radarr-k8s"]


class ArrCredentials(BaseModel):
    """API credentials retrieved from a Juju secret."""

    api_key: str
    secret_id: str
    base_url: str = ""


def pack_arr_charms(charms_dir: Path) -> dict[str, Path]:
    """Pack all arr family charms for cross-integration testing.

    Args:
        charms_dir: Path to the charms directory (e.g., charmarr/charms/).

    Returns:
        Dictionary mapping charm name to packed .charm file path.
    """
    if env_paths := os.environ.get("ARR_CHARM_PATHS"):
        return {k: Path(v) for k, v in json.loads(env_paths).items()}

    return {name: pack(charms_dir / name) for name in ARR_CHARMS}


def deploy_arr_charm(
    juju: jubilant.Juju,
    charm_path: Path,
    app_name: str,
    charm_dir: Path,
    *,
    with_storage: bool = True,
) -> None:
    """Deploy an arr charm with common configuration.

    Args:
        juju: Juju instance.
        charm_path: Path to the packed .charm file.
        app_name: Application name for deployment.
        charm_dir: Path to the charm source directory (for OCI resources).
        with_storage: Whether to integrate with charmarr-storage.
    """
    juju.deploy(
        str(charm_path),
        app=app_name,
        trust=True,
        resources=get_oci_resources(charm_dir),
    )

    if with_storage:
        juju.integrate(f"{app_name}:media-storage", "charmarr-storage:media-storage")

    wait_for_active_idle(juju)


def get_arr_credentials(
    juju: jubilant.Juju,
    app_name: str,
    secret_label: str,
) -> ArrCredentials | None:
    """Get API credentials from an arr charm's app-owned secret.

    Args:
        juju: Juju instance.
        app_name: Application name that owns the secret.
        secret_label: Label of the secret to retrieve.

    Returns:
        ArrCredentials if found, None otherwise.
    """
    try:
        output = juju.cli("list-secrets", "--format=json")
        secrets = json.loads(output)

        for secret_id, info in secrets.items():
            if info.get("owner") == app_name and info.get("label") == secret_label:
                content_output = juju.cli("show-secret", secret_id, "--reveal", "--format=json")
                content_data = json.loads(content_output)
                content = content_data[secret_id]["content"]["Data"]
                return ArrCredentials(
                    api_key=content.get("api-key", ""),
                    secret_id=secret_id,
                )
        return None
    except Exception as e:
        logger.warning("Failed to get credentials for %s: %s", app_name, e)
        return None
