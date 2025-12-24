# Copyright 2025 The Charmarr Project
# See LICENSE file for licensing details.

"""Terraform/OpenTofu wrapper for integration testing."""

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class TFManager:
    """Simplified Terraform/OpenTofu API for integration tests.

    Prefers OpenTofu (tofu) over Terraform if both are available.
    """

    def __init__(self, terraform_dir: Path, state_file: Path | None = None) -> None:
        binary = shutil.which("tofu") or shutil.which("terraform")
        if not binary:
            raise RuntimeError("Terraform or OpenTofu binary not found in PATH.")
        if not terraform_dir.is_dir():
            raise FileNotFoundError(f"Terraform directory not found: {terraform_dir}")
        self._binary = binary
        self._terraform_dir = terraform_dir
        self._state_file = state_file

    def _run(
        self, cmd: list[str], env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        full_cmd = [self._binary, *cmd]
        result = subprocess.run(
            full_cmd,
            cwd=self._terraform_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            binary_name = Path(self._binary).name
            subcommand = cmd[0] if cmd else "unknown"
            logger.error(
                "%s %s failed:\nSTDOUT: %s\nSTDERR: %s",
                binary_name,
                subcommand,
                result.stdout,
                result.stderr,
            )
            raise RuntimeError(f"{binary_name} {subcommand} failed with code {result.returncode}")
        return result

    def init(self) -> None:
        """Initialize terraform directory."""
        self._run(["init"])

    def apply(self, env: dict[str, str] | None = None) -> None:
        """Apply terraform configuration."""
        cmd = ["apply", "-auto-approve"]
        if self._state_file:
            cmd.append(f"-state={self._state_file}")
        self._run(cmd, env)

    def output(self, name: str) -> str:
        """Get output value from terraform state."""
        cmd = ["output", "-raw"]
        if self._state_file:
            cmd.append(f"-state={self._state_file}")
        cmd.append(name)
        return self._run(cmd).stdout.strip()

    def destroy(self, env: dict[str, str] | None = None) -> None:
        """Destroy all terraform-managed resources."""
        cmd = ["destroy", "-auto-approve"]
        if self._state_file:
            cmd.append(f"-state={self._state_file}")
        self._run(cmd, env)
