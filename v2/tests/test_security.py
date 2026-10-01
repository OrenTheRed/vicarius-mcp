import asyncio
import json
import subprocess
import sys

import httpx
import pytest
import respx

from vicarius_v2_mcp import __version__
from vicarius_v2_mcp.app import WRITE_TAG, enforce_read_only, mcp
from vicarius_v2_mcp.client import _base, _resolve_tenant, normalize_host, seg
from vicarius_v2_mcp.server import main  # noqa: F401  (registers every tool)
from vicarius_v2_mcp.tools_reports import delete_report
from vicarius_v2_mcp.tools_tenants import add_configured_tenant


def _tools():
    return asyncio.run(mcp.list_tools())


# ---------------------------------------------------------------------------
# Path-segment encoding
# ---------------------------------------------------------------------------


def test_seg_encodes_path_separators():
    assert seg("../apiKeys/k-1") == "..%2FapiKeys%2Fk-1"
    assert seg("abc-123") == "abc-123"


@pytest.mark.parametrize("bad", ["", " ", ".", ".."])
def test_seg_rejects_ids_that_collapse_onto_the_parent_path(bad):
    with pytest.raises(ValueError):
        seg(bad)


@respx.mock
def test_id_cannot_traverse_to_another_endpoint(vicarius_v2_env):
    # Without encoding, httpx would normalize this to DELETE /api/apiKeys/k-1.
    api_keys = respx.delete(f"{_base('acme')}/apiKeys/k-1").mock(return_value=httpx.Response(200, json={}))
    reports = respx.delete(url__startswith=f"{_base('acme')}/reports/").mock(return_value=httpx.Response(200, json={}))
    delete_report("../apiKeys/k-1")
    assert not api_keys.called
    assert reports.called


# ---------------------------------------------------------------------------
# Host validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw, expected", [
    (None, "vicarius.cloud"),
    ("vicarius.cloud", "vicarius.cloud"),
    ("https://Acme.Vicarius.Cloud/", "acme.vicarius.cloud"),
    ("vicarius.cloud/api", "vicarius.cloud"),
    ("onprem.example.com:8443", "onprem.example.com:8443"),
])
def test_normalize_host_accepts_hostnames(raw, expected):
    assert normalize_host(raw) == expected


@pytest.mark.parametrize("raw", [
    "http://vicarius.cloud",
    "evil.example.com/steal?x=",
    "user:pass@vicarius.cloud",
    "vicarius.cloud#frag",
    "-bad-.example.com",
    "evil.example.com\n/api",
])
def test_normalize_host_rejects_non_hostnames(raw):
    with pytest.raises(ValueError):
        normalize_host(raw)


def test_invalid_host_in_config_is_refused(monkeypatch):
    monkeypatch.setenv("VICARIUS_V2_TENANTS", json.dumps({"x": {"api_key": "k", "host": "evil.example.com/a?"}}))
    with pytest.raises(RuntimeError, match="Invalid host"):
        _resolve_tenant("x")


def test_add_configured_tenant_rejects_bad_host(monkeypatch, tmp_path):
    tenants_file = tmp_path / "tenants.json"
    monkeypatch.setenv("VICARIUS_V2_TENANTS_FILE", str(tenants_file))
    assert add_configured_tenant("x", "k", host="evil.example.com/path").startswith("ERROR")
    assert not tenants_file.exists()


def test_errors_never_echo_api_keys(monkeypatch):
    monkeypatch.setenv("VICARIUS_V2_TENANTS", json.dumps({"x": {"api_key": "super-secret-value", "host": "bad host"}}))
    with pytest.raises(RuntimeError) as exc:
        _resolve_tenant("x")
    assert "super-secret-value" not in str(exc.value)


# ---------------------------------------------------------------------------
# Tool annotations & read-only mode
# ---------------------------------------------------------------------------


def test_every_tool_is_annotated():
    for tool in _tools():
        assert tool.annotations is not None, tool.name
        assert tool.annotations.readOnlyHint is not None, tool.name
        if not tool.annotations.readOnlyHint:
            assert WRITE_TAG in tool.tags, tool.name


def test_destructive_tools_are_flagged():
    by_name = {t.name: t for t in _tools()}
    for name in ("delete_site", "delete_api_key", "remove_org_member", "update_scan_policy"):
        assert by_name[name].annotations.destructiveHint is True, name
    for name in ("list_sites", "search_findings", "get_asset"):
        assert by_name[name].annotations.readOnlyHint is True, name


@pytest.fixture
def read_only(monkeypatch):
    monkeypatch.setenv("VICARIUS_READ_ONLY", "true")
    enforce_read_only()
    yield
    mcp.enable(tags={WRITE_TAG})


def test_read_only_mode_hides_write_tools(read_only):
    names = {t.name for t in _tools()}
    assert "list_sites" in names
    assert "delete_site" not in names
    assert "add_configured_tenant" not in names
    assert all(t.annotations.readOnlyHint for t in _tools())


def test_read_only_mode_blocks_calls_to_write_tools(read_only):
    with pytest.raises(Exception):
        asyncio.run(mcp.call_tool("delete_site", {"site_id": "s-1"}))


def test_read_only_off_by_default(monkeypatch):
    monkeypatch.delenv("VICARIUS_READ_ONLY", raising=False)
    enforce_read_only()
    assert "delete_site" in {t.name for t in _tools()}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_version_flag():
    out = subprocess.run([sys.executable, "-m", "vicarius_v2_mcp.server", "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == f"vicarius-v2-mcp {__version__}"


def test_optional_arguments_accept_null():
    tool = {t.name: t for t in _tools()}["search_findings"]
    for arg in ("params", "tenant"):
        types = {s.get("type") for s in tool.parameters["properties"][arg].get("anyOf", [])}
        assert "null" in types, arg


def test_policy_state_tools_are_destructive():
    by_name = {t.name: t for t in _tools()}
    for name in ("set_scan_policy_state", "set_patch_policy_state", "set_script_policy_state"):
        assert by_name[name].annotations.destructiveHint is True, name
