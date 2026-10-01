import json
import pytest
import respx
import httpx
from vicarius_mcp.server import _get, _post, _delete, _base, _headers


def test_base_url(vicarius_env):
    assert _base() == "https://testdash.vicarius.cloud/vicarius-external-data-api"


def test_headers(vicarius_env):
    assert _headers() == {"vicarius-token": "dummy"}


@respx.mock
def test_get_success(vicarius_env):
    url = f"{_base()}/endpoint/search"
    respx.get(url).mock(return_value=httpx.Response(200, json={"serverResponseObject": [{"endpointName": "host1"}]}))
    result = _get("/endpoint/search", params={"from": 0, "size": 10})
    data = json.loads(result)
    assert data["serverResponseObject"][0]["endpointName"] == "host1"


@respx.mock
def test_get_http_error(vicarius_env):
    url = f"{_base()}/endpoint/search"
    respx.get(url).mock(return_value=httpx.Response(401, text="Unauthorized"))
    result = _get("/endpoint/search")
    assert result.startswith("ERROR 401")


@respx.mock
def test_post_success(vicarius_env):
    url = f"{_base()}/endpoint/search"
    respx.post(url).mock(return_value=httpx.Response(200, json={"serverResponseObject": []}))
    result = _post("/endpoint/search", body=[{"key": "val"}])
    data = json.loads(result)
    assert data["serverResponseObject"] == []


@respx.mock
def test_delete_success(vicarius_env):
    url = f"{_base()}/endpoint/delete"
    respx.delete(url).mock(return_value=httpx.Response(200, json={"deleted": True}))
    result = _delete("/endpoint/delete", params={"id": "abc"})
    assert json.loads(result)["deleted"] is True


def test_missing_dashboard(monkeypatch):
    monkeypatch.delenv("VICARIUS_DASHBOARD", raising=False)
    monkeypatch.setenv("VICARIUS_API_KEY", "key")
    with pytest.raises(RuntimeError, match="VICARIUS_DASHBOARD"):
        _base()


def test_missing_api_key(monkeypatch):
    monkeypatch.setenv("VICARIUS_DASHBOARD", "dash")
    monkeypatch.delenv("VICARIUS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="VICARIUS_API_KEY"):
        _headers()
