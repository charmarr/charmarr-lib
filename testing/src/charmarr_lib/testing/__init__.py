# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Testing utilities for Charmarr charms."""

from charmarr_lib.testing._charmcraft import get_oci_resources
from charmarr_lib.testing._http import HttpResponse, http_request
from charmarr_lib.testing._juju import (
    create_vpn_secret,
    deploy_multimeter,
    get_app_relation_data,
    get_node_cidr,
    grant_secret_to_app,
    vpn_creds_available,
    wait_for_active_idle,
)
from charmarr_lib.testing._k8s import (
    ContainerInfo,
    get_container_info,
    get_ingress_ip,
    run_multimeter_action,
)
from charmarr_lib.testing._terraform import TFManager

__all__ = [
    "ContainerInfo",
    "HttpResponse",
    "TFManager",
    "create_vpn_secret",
    "deploy_multimeter",
    "get_app_relation_data",
    "get_container_info",
    "get_ingress_ip",
    "get_node_cidr",
    "get_oci_resources",
    "grant_secret_to_app",
    "http_request",
    "run_multimeter_action",
    "vpn_creds_available",
    "wait_for_active_idle",
]
