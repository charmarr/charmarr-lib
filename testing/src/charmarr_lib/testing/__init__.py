# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Testing utilities for Charmarr charms. Dummy text"""

from charmarr_lib.testing._juju import wait_for_active_idle
from charmarr_lib.testing._terraform import TFManager

__all__ = [
    "TFManager",
    "wait_for_active_idle",
]
