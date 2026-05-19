"""Shared pytest fixtures for IaC validation."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_DIR = REPO_ROOT / "infra"
BICEP_FILE = INFRA_DIR / "main.bicep"
PARAMETERS_EXAMPLE_FILE = INFRA_DIR / "main.parameters.example.json"
PARAMETERS_FILE = INFRA_DIR / "main.parameters.json"

EXPECTED_RESOURCE_TYPES = frozenset(
    {
        "Microsoft.Network/networkSecurityGroups",
        "Microsoft.Network/virtualNetworks",
        "Microsoft.Network/publicIPAddresses",
        "Microsoft.Network/networkInterfaces",
        "Microsoft.Compute/virtualMachines",
    }
)

REQUIRED_PARAMETERS = frozenset(
    {
        "location",
        "namePrefix",
        "adminUsername",
        "sshPublicKey",
        "vmSize",
        "osDiskSizeGB",
        "installOllama",
        "allowSshFromInternet",
        "sshSourceAddressPrefix",
    }
)


def _run_build(cmd: list[str], cwd: Path, out_file: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return result
    if not out_file.is_file():
        return result
    return result


def build_bicep_command(out_file: Path) -> list[str] | None:
    """Return a full bicep build command, or None if no CLI is available."""
    bicep = shutil.which("bicep")
    if bicep:
        return [bicep, "build", str(BICEP_FILE), "--outfile", str(out_file)]

    az = shutil.which("az")
    if az:
        return [
            az,
            "bicep",
            "build",
            "--file",
            str(BICEP_FILE),
            "--outfile",
            str(out_file),
        ]

    return None


def bicep_cli_available() -> bool:
    return shutil.which("bicep") is not None or shutil.which("az") is not None


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def bicep_source(repo_root: Path) -> str:
    return BICEP_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def parameters_example_doc() -> dict[str, Any]:
    return json.loads(PARAMETERS_EXAMPLE_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def local_parameters_doc() -> dict[str, Any] | None:
    if not PARAMETERS_FILE.is_file():
        return None
    return json.loads(PARAMETERS_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def bicep_build_available() -> bool:
    return bicep_cli_available()


@pytest.fixture(scope="session")
def compiled_arm_template(bicep_build_available: bool) -> dict[str, Any]:
    if not bicep_build_available:
        pytest.skip("Bicep CLI not found (install Azure CLI or standalone bicep)")

    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "main.json"
        cmd = build_bicep_command(out_file)
        assert cmd is not None
        result = _run_build(cmd, REPO_ROOT, out_file)
        if result is None:
            pytest.skip("Bicep CLI not executable")
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            pytest.fail(f"Bicep build failed:\n{stderr}")

        return json.loads(out_file.read_text(encoding="utf-8"))
