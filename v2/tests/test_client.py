import json

import httpx
import pytest
import respx

from vicarius_v2_mcp.client import _base, _get, _resolve_tenant


def test_resolve_default_tenant(vicarius_v2_env):
    name, host, key = _resolve_tenant(None)
    assert name == "acme"
    assert host == "acme.vicarius.cloud"
    assert key == "dummy-acme"


def test_resolve_named_tenant(vicarius_v2_env):
    name, host, key = _resolve_tenant("beta")
    assert name == "beta"
    assert host == "vicarius.cloud"
    assert key == "dummy-beta"


def test_resolve_unknown_tenant_errors(vicarius_v2_env):
    with pytest.raises(RuntimeError, match="Unknown tenant"):
        _resolve_tenant("nope")


def test_resolve_no_tenants_configured(monkeypatch):
    monkeypatch.delenv("VICARIUS_V2_TENANTS", raising=False)
    with pytest.raises(RuntimeError, match="VICARIUS_V2_TENANTS"):
        _resolve_tenant(None)


@respx.mock
def test_get_routes_to_correct_tenant_host_and_key(vicarius_v2_env):
    route_acme = respx.get(f"{_base('acme')}/sites").mock(
        return_value=httpx.Response(200, json={"ok": "acme"})
    )
    route_beta = respx.get(f"{_base('beta')}/sites").mock(
        return_value=httpx.Response(200, json={"ok": "beta"})
    )
    result_acme = json.loads(_get("/sites", tenant="acme"))
    assert result_acme["ok"] == "acme"
    assert route_acme.calls.last.request.headers["x-api-key"] == "dummy-acme"

    result_beta = json.loads(_get("/sites", tenant="beta"))
    assert result_beta["ok"] == "beta"
    assert route_beta.calls.last.request.headers["x-api-key"] == "dummy-beta"


@respx.mock
def test_get_defaults_to_default_tenant(vicarius_v2_env):
    respx.get(f"{_base('acme')}/sites").mock(return_value=httpx.Response(200, json={"ok": True}))
    result = json.loads(_get("/sites"))
    assert result["ok"] is True


@respx.mock
def test_error_response_surfaces_as_string(vicarius_v2_env):
    respx.get(f"{_base('acme')}/sites").mock(return_value=httpx.Response(404, text="not found"))
    result = _get("/sites")
    assert result.startswith("ERROR 404")


def test_exception_surfaces_as_error_string(vicarius_v2_env):
    result = _get("/sites", tenant="does-not-exist")
    assert result.startswith("ERROR:")
