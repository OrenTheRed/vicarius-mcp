import json
import sys

import pytest

from vicarius_v2_mcp.client import _resolve_tenant
from vicarius_v2_mcp.tools_tenants import (
    add_configured_tenant,
    remove_configured_tenant,
    list_configured_tenants,
)


@pytest.fixture
def file_tenants(monkeypatch, tmp_path):
    """Tenants come from a (not yet existing) file only - no VICARIUS_V2_TENANTS env var."""
    tenants_file = tmp_path / "tenants.json"
    monkeypatch.setenv("VICARIUS_V2_TENANTS_FILE", str(tenants_file))
    monkeypatch.delenv("VICARIUS_V2_TENANTS", raising=False)
    monkeypatch.delenv("VICARIUS_V2_DEFAULT_TENANT", raising=False)
    return tenants_file


def test_add_configured_tenant_persists_and_is_usable(file_tenants):
    tenants_file = file_tenants

    result = json.loads(add_configured_tenant("newco", "newco-key", host="vicarius.cloud"))
    assert "newco" in result["tenants"]
    assert tenants_file.exists()

    on_disk = json.loads(tenants_file.read_text())
    assert on_disk["newco"] == {"api_key": "newco-key", "host": "vicarius.cloud"}

    name, host, key = _resolve_tenant("newco")
    assert (name, host, key) == ("newco", "vicarius.cloud", "newco-key")


def test_tenants_file_takes_priority_over_env_var(vicarius_v2_env, monkeypatch, tmp_path):
    tenants_file = tmp_path / "tenants.json"
    tenants_file.write_text(json.dumps({"fileonly": {"api_key": "file-key"}}))
    monkeypatch.setenv("VICARIUS_V2_TENANTS_FILE", str(tenants_file))

    # VICARIUS_V2_TENANTS env var (set by the autouse fixture) has "acme"/"beta" - the file
    # should win entirely once it exists, not merge with the env var.
    tenants = json.loads(list_configured_tenants())["tenants"]
    assert tenants == ["fileonly"]


def test_add_then_remove_configured_tenant(file_tenants):
    add_configured_tenant("temp-tenant", "temp-key")
    assert "temp-tenant" in json.loads(list_configured_tenants())["tenants"]

    result = json.loads(remove_configured_tenant("temp-tenant"))
    assert result["removed"] is True
    assert "temp-tenant" not in result["tenants"]


def test_remove_unknown_tenant_returns_false(file_tenants):
    add_configured_tenant("keepme", "k")
    result = json.loads(remove_configured_tenant("does-not-exist"))
    assert result["removed"] is False
    assert result["tenants"] == ["keepme"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_add_configured_tenant_sets_restrictive_permissions(file_tenants):
    import stat

    tenants_file = file_tenants
    add_configured_tenant("secure", "k")
    mode = stat.S_IMODE(tenants_file.stat().st_mode)
    assert mode == 0o600


def test_tenants_file_with_utf8_bom_is_accepted(monkeypatch, tmp_path):
    tenants_file = tmp_path / "tenants.json"
    tenants_file.write_bytes(b"\xef\xbb\xbf" + json.dumps({"bom": {"api_key": "k"}}).encode())
    monkeypatch.setenv("VICARIUS_V2_TENANTS_FILE", str(tenants_file))
    assert _resolve_tenant("bom") == ("bom", "vicarius.cloud", "k")


def test_add_does_not_silently_overwrite(file_tenants):
    add_configured_tenant("acme", "first-key")
    assert add_configured_tenant("acme", "second-key").startswith("ERROR")
    assert _resolve_tenant("acme")[2] == "first-key"
    json.loads(add_configured_tenant("acme", "second-key", overwrite=True))
    assert _resolve_tenant("acme")[2] == "second-key"


def test_add_refuses_non_vicarius_host_by_default(file_tenants, monkeypatch):
    assert add_configured_tenant("x", "k", host="attacker.example.com").startswith("ERROR")
    assert add_configured_tenant("x", "k", host="169.254.169.254").startswith("ERROR")
    assert not file_tenants.exists()
    monkeypatch.setenv("VICARIUS_V2_ALLOW_CUSTOM_HOSTS", "true")
    assert "x" in json.loads(add_configured_tenant("x", "k", host="onprem.example.com"))["tenants"]


def test_add_refuses_when_tenants_come_from_env_var(vicarius_v2_env):
    # Creating a file would hide the env-var tenants (acme, beta) - refuse instead.
    assert add_configured_tenant("newco", "k").startswith("ERROR")
    assert sorted(json.loads(list_configured_tenants())["tenants"]) == ["acme", "beta"]
