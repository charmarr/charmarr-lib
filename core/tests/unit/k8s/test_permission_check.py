# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Unit tests for the storage permission check Job."""

import httpx
import pytest
from lightkube import ApiError
from lightkube.models.batch_v1 import JobStatus
from lightkube.resources.batch_v1 import Job

from charmarr_lib.core import check_storage_permissions


@pytest.fixture
def applied_job(manager, mock_client):
    """The Job the check submits when none exists yet."""
    response = httpx.Response(404, json={"message": "not found", "code": 404})
    mock_client.get.side_effect = [
        ApiError(response=response),
        Job(status=JobStatus(succeeded=1)),
    ]

    check_storage_permissions(
        manager=manager,
        namespace="charmarr",
        pvc_name="charmarr-shared-media",
        puid=1000,
        pgid=1000,
    )

    return mock_client.apply.call_args.args[0].spec.template.spec


def test_job_runs_as_the_configured_user(applied_job):
    security_context = applied_job.containers[0].securityContext

    assert security_context.runAsUser == 1000
    assert security_context.runAsGroup == 1000


def test_job_sets_fs_group(applied_job):
    """Block-backed CSI volumes arrive root-owned; fsGroup makes them writable."""
    assert applied_job.securityContext.fsGroup == 1000
