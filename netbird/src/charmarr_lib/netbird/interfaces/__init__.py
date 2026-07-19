# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""NetBird relation interface implementations."""

from charmarr_lib.netbird.interfaces._netbird_enrollment import (
    NetbirdEnrollmentCredentials,
    NetbirdEnrollmentProvider,
    NetbirdEnrollmentProviderData,
    NetbirdEnrollmentRequirer,
    NetbirdEnrollmentRequirerData,
)

__all__ = [
    "NetbirdEnrollmentCredentials",
    "NetbirdEnrollmentProvider",
    "NetbirdEnrollmentProviderData",
    "NetbirdEnrollmentRequirer",
    "NetbirdEnrollmentRequirerData",
]
