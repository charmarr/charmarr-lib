# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Testing utilities for Charmarr charms."""

from charmarr_lib.testing._arr import (
    ArrCredentials,
    deploy_arr_charm,
    get_arr_credentials,
    pack_arr_charms,
)
from charmarr_lib.testing._charmcraft import get_oci_resources
from charmarr_lib.testing._http import HttpResponse, http_from_unit, http_request
from charmarr_lib.testing._juju import (
    assert_app_active,
    create_vpn_secret,
    deploy_multimeter,
    ensure_related,
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
    "ArrCredentials",
    "ContainerInfo",
    "HttpResponse",
    "TFManager",
    "assert_app_active",
    "create_vpn_secret",
    "deploy_arr_charm",
    "deploy_multimeter",
    "ensure_related",
    "get_app_relation_data",
    "get_arr_credentials",
    "get_container_info",
    "get_ingress_ip",
    "get_node_cidr",
    "get_oci_resources",
    "grant_secret_to_app",
    "http_from_unit",
    "http_request",
    "pack_arr_charms",
    "run_multimeter_action",
    "vpn_creds_available",
    "wait_for_active_idle",
]
