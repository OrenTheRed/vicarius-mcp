import asyncio
import subprocess
import sys

import httpx
import pytest
import respx

from vicarius_mcp import __version__
from vicarius_mcp.server import (
    WRITE_TAG,
    _base,
    _dashboard,
    enforce_read_only,
    get_automation,
    get_cve_info,
    list_event_log,
    mcp,
    _seg,
    set_automation_state,
)


def _tools():
    return asyncio.run(mcp.list_tools())


@pytest.mark.parametrize("raw", ["acme", "ACME", "acme.vicarius.cloud", "https://acme.vicarius.cloud/dashboard"])
def test_dashboard_normalization(monkeypatch, raw):
    monkeypatch.setenv("VICARIUS_DASHBOARD", raw)
    assert _dashboard() == "acme"


@pytest.mark.parametrize("raw", ["evil.example.com/x?", "acme.evil.com", "a b", "-acme"])
def test_dashboard_rejects_non_subdomains(monkeypatch, raw):
    monkeypatch.setenv("VICARIUS_DASHBOARD", raw)
    with pytest.raises(RuntimeError, match="subdomain"):
        _dashboard()


@respx.mock
def test_rsql_values_cannot_break_out_of_quotes(vicarius_env):
    route = respx.get(f"{_base()}/vulnerability/search").mock(return_value=httpx.Response(200, json={}))
    get_cve_info('CVE-1";vulnerabilityId=="*')
    assert route.calls.last.request.url.params["q"] == 'vulnerabilityId=="CVE-1\\";vulnerabilityId==\\"*"'


@respx.mock
def test_path_ids_are_encoded(vicarius_env):
    route = respx.get(url__startswith=f"{_base()}/v1/automations/").mock(return_value=httpx.Response(200, json={}))
    get_automation("../../user/search")
    assert route.calls.last.request.url.raw_path.endswith(b"/v1/automations/..%2F..%2Fuser%2Fsearch")


@respx.mock
def test_event_log_sort_is_not_double_encoded(vicarius_env):
    route = respx.get(f"{_base()}/incidentEvent/filter").mock(return_value=httpx.Response(200, json={}))
    list_event_log()
    assert b"sort=%2BanalyticsEventCreatedAtNano" in route.calls.last.request.url.query


def test_every_tool_is_annotated():
    for tool in _tools():
        assert tool.annotations.readOnlyHint is not None, tool.name
        if not tool.annotations.readOnlyHint:
            assert WRITE_TAG in tool.tags, tool.name


@pytest.fixture
def read_only(monkeypatch):
    monkeypatch.setenv("VICARIUS_READ_ONLY", "true")
    enforce_read_only()
    yield
    mcp.enable(tags={WRITE_TAG})


def test_read_only_mode_hides_write_tools(read_only):
    names = {t.name for t in _tools()}
    assert "list_assets" in names
    assert not names & {"delete_asset", "create_automation", "invite_user"}
    with pytest.raises(Exception):
        asyncio.run(mcp.call_tool("delete_asset", {"asset_id": "a-1"}))


def test_version_flag():
    out = subprocess.run([sys.executable, "-m", "vicarius_mcp.server", "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == f"vicarius-mcp {__version__}"


@pytest.mark.parametrize("bad", ["", ".", ".."])
def test_seg_rejects_ids_that_collapse_onto_the_parent_path(bad):
    with pytest.raises(ValueError):
        _seg(bad)


@respx.mock
def test_empty_success_response_is_not_an_error(vicarius_env):
    respx.put(f"{_base()}/v1/automations/a-1/updateState").mock(return_value=httpx.Response(204))
    assert set_automation_state("a-1", True).startswith("{")
