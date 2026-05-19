"""Tests for the Linux VM Bicep template."""

from __future__ import annotations

from typing import Any

from tests.conftest import (
    BICEP_FILE,
    EXPECTED_RESOURCE_TYPES,
    PARAMETERS_FILE,
    REQUIRED_PARAMETERS,
)

# --- Static checks (no Bicep CLI required) ---


def test_infra_files_exist() -> None:
    assert BICEP_FILE.is_file()
    assert PARAMETERS_FILE.is_file()


def test_bicep_declares_linux_vm_and_ssh_only(bicep_source: str) -> None:
    assert "targetScope = 'resourceGroup'" in bicep_source
    assert "Microsoft.Compute/virtualMachines@" in bicep_source
    assert "linuxConfiguration:" in bicep_source
    assert "disablePasswordAuthentication: true" in bicep_source
    assert "sshPublicKey" in bicep_source


def test_bicep_declares_network_stack(bicep_source: str) -> None:
    for fragment in (
        "Microsoft.Network/networkSecurityGroups@",
        "Microsoft.Network/virtualNetworks@",
        "Microsoft.Network/publicIPAddresses@",
        "Microsoft.Network/networkInterfaces@",
        "destinationPortRange: '22'",
        "0001-com-ubuntu-server-jammy",
    ):
        assert fragment in bicep_source


def test_bicep_declares_outputs(bicep_source: str) -> None:
    for name in ("vmName", "publicIpAddress", "sshCommand"):
        assert f"output {name}" in bicep_source


def test_parameters_file_is_valid_json(parameters_doc: dict[str, Any]) -> None:
    assert parameters_doc.get("contentVersion")
    params = parameters_doc.get("parameters")
    assert isinstance(params, dict)


def test_parameters_include_required_keys(parameters_doc: dict[str, Any]) -> None:
    keys = set(parameters_doc["parameters"])
    missing = REQUIRED_PARAMETERS - keys
    assert not missing, f"Missing parameters: {sorted(missing)}"


def test_parameters_ssh_key_is_placeholder(parameters_doc: dict[str, Any]) -> None:
    value = parameters_doc["parameters"]["sshPublicKey"]["value"]
    assert "REPLACE_WITH_YOUR_SSH_PUBLIC_KEY" in value


def test_parameters_admin_username_not_empty(parameters_doc: dict[str, Any]) -> None:
    assert parameters_doc["parameters"]["adminUsername"]["value"]


# --- Compiled template checks (require Bicep CLI) ---


def _resource_types(template: dict[str, Any]) -> set[str]:
    resources = template.get("resources", [])
    return {r["type"] for r in resources if "type" in r}


def _find_resource(template: dict[str, Any], resource_type: str) -> dict[str, Any]:
    for resource in template.get("resources", []):
        if resource.get("type") == resource_type:
            return resource
    raise AssertionError(f"Resource type not found: {resource_type}")


def test_bicep_compiles_to_arm(compiled_arm_template: dict[str, Any]) -> None:
    assert compiled_arm_template.get("$schema")
    assert compiled_arm_template.get("resources")


def test_compiled_template_has_expected_resources(compiled_arm_template: dict[str, Any]) -> None:
    types = _resource_types(compiled_arm_template)
    missing = EXPECTED_RESOURCE_TYPES - types
    assert not missing, f"Missing resource types: {sorted(missing)}"


def test_compiled_linux_vm_uses_ssh_keys(compiled_arm_template: dict[str, Any]) -> None:
    vm = _find_resource(compiled_arm_template, "Microsoft.Compute/virtualMachines")
    linux_cfg = vm["properties"]["osProfile"]["linuxConfiguration"]
    assert linux_cfg["disablePasswordAuthentication"] is True
    public_keys = linux_cfg["ssh"]["publicKeys"]
    assert len(public_keys) >= 1
    assert public_keys[0]["keyData"] == "[parameters('sshPublicKey')]"


def test_compiled_nsg_allows_ssh(compiled_arm_template: dict[str, Any]) -> None:
    nsg = _find_resource(compiled_arm_template, "Microsoft.Network/networkSecurityGroups")
    rules = nsg["properties"]["securityRules"]
    ssh_rules = [r for r in rules if r["properties"].get("destinationPortRange") == "22"]
    assert ssh_rules, "Expected an inbound SSH rule on port 22"


def test_compiled_template_exposes_outputs(compiled_arm_template: dict[str, Any]) -> None:
    outputs = compiled_arm_template.get("outputs", {})
    for name in ("vmName", "publicIpAddress", "sshCommand"):
        assert name in outputs, f"Missing output: {name}"


def test_compiled_parameters_include_ssh_key(compiled_arm_template: dict[str, Any]) -> None:
    parameters = compiled_arm_template.get("parameters", {})
    assert "sshPublicKey" in parameters
    assert parameters["sshPublicKey"].get("type") == "securestring"
