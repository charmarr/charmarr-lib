# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Shared BDD step definitions for Charmarr integration tests.

Usage in charm conftest.py:

    pytest_plugins = [
        "charmarr_lib.testing.steps.multimeter",
        "charmarr_lib.testing.steps.storage",
        "charmarr_lib.testing.steps.gluetun",
        "charmarr_lib.testing.steps.mesh",
    ]
"""
