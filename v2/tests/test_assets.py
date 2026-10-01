import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_assets import (
    search_assets,
    get_asset,
    get_asset_risk_distribution,
    list_asset_groups,
    create_asset_group,
    update_asset_group,
    delete_asset_group,
    search_software,
    get_software,
    list_software_groups,
    create_software_group,
    update_software_group,
    delete_software_group,
)


@respx.mock
def test_search_assets(vicarius_v2_env):
    route = respx.post(f"{_base('acme')}/assets/search").mock(
        return_value=httpx.Response(200, json=[{"id": "a-1", "name": "host1"}])
    )
    result = json.loads(search_assets(filters={"typeIn": ["MANAGED"]}))
    assert result[0]["name"] == "host1"
    assert json.loads(route.calls.last.request.content) == {"typeIn": ["MANAGED"]}


@respx.mock
def test_get_asset(vicarius_v2_env):
    respx.get(f"{_base('acme')}/asset/a-1").mock(return_value=httpx.Response(200, json={"id": "a-1"}))
    assert json.loads(get_asset("a-1"))["id"] == "a-1"


@respx.mock
def test_get_asset_risk_distribution(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/assets/risk-distribution").mock(
        return_value=httpx.Response(200, json={"critical": 1, "high": 2})
    )
    result = json.loads(get_asset_risk_distribution("s-1"))
    assert result["critical"] == 1
    assert route.calls.last.request.url.params["siteId"] == "s-1"


@respx.mock
def test_asset_groups_crud(vicarius_v2_env):
    respx.get(f"{_base('acme')}/assetGroups").mock(return_value=httpx.Response(200, json=[{"id": "g-1"}]))
    respx.post(f"{_base('acme')}/assetGroups").mock(return_value=httpx.Response(200, json={"id": "g-2"}))
    respx.put(f"{_base('acme')}/assetGroups/g-1").mock(return_value=httpx.Response(200, json={"id": "g-1", "name": "Servers"}))
    respx.delete(f"{_base('acme')}/assetGroups/g-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(list_asset_groups())[0]["id"] == "g-1"
    assert json.loads(create_asset_group({"name": "Servers", "type": "STATIC", "assetIds": ["a-1"]}))["id"] == "g-2"
    assert json.loads(update_asset_group("g-1", {"name": "Servers"}))["name"] == "Servers"
    assert json.loads(delete_asset_group("g-1")) is True


@respx.mock
def test_software(vicarius_v2_env):
    respx.get(f"{_base('acme')}/software").mock(return_value=httpx.Response(200, json=[{"productId": "p-1"}]))
    respx.get(f"{_base('acme')}/software/p-1").mock(return_value=httpx.Response(200, json={"productId": "p-1"}))
    assert json.loads(search_software())[0]["productId"] == "p-1"
    assert json.loads(get_software("p-1"))["productId"] == "p-1"


@respx.mock
def test_software_groups_crud(vicarius_v2_env):
    respx.get(f"{_base('acme')}/softwareGroups").mock(return_value=httpx.Response(200, json=[{"id": "sg-1"}]))
    respx.post(f"{_base('acme')}/softwareGroups").mock(return_value=httpx.Response(200, json={"id": "sg-2"}))
    respx.put(f"{_base('acme')}/softwareGroups/sg-1").mock(return_value=httpx.Response(200, json={"id": "sg-1"}))
    respx.delete(f"{_base('acme')}/softwareGroups/sg-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(list_software_groups())[0]["id"] == "sg-1"
    assert json.loads(create_software_group({"name": "Browsers"}))["id"] == "sg-2"
    assert json.loads(update_software_group("sg-1", {"name": "Browsers"}))["id"] == "sg-1"
    assert json.loads(delete_software_group("sg-1")) is True
