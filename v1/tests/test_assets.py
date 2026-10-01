import json
import respx
import httpx
from vicarius_mcp.server import (
    list_assets, get_asset_attributes, get_asset_ip_addresses,
    get_asset_applications, list_assets_with_cve, delete_asset,
    _base,
)

ASSET_STUB = {"endpointId": "id-1", "endpointName": "host1", "endpointAlive": True}


@respx.mock
def test_list_assets(vicarius_env):
    respx.get(f"{_base()}/endpoint/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [ASSET_STUB], "serverResponseCount": 1})
    )
    result = json.loads(list_assets())
    assert result["serverResponseObject"][0]["endpointName"] == "host1"


@respx.mock
def test_list_assets_with_filter(vicarius_env):
    route = respx.get(f"{_base()}/endpoint/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [], "serverResponseCount": 0})
    )
    list_assets(q='endpointName=="host1"')
    assert route.called


@respx.mock
def test_get_asset_attributes(vicarius_env):
    respx.get(f"{_base()}/endpointAttributes/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [{"endpointId": "id-1"}]})
    )
    result = json.loads(get_asset_attributes("id-1"))
    assert result["serverResponseObject"][0]["endpointId"] == "id-1"


@respx.mock
def test_get_asset_ip_addresses(vicarius_env):
    respx.get(f"{_base()}/endpointAttributes/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [{"ipAddresses": ["10.0.0.1"]}]})
    )
    result = json.loads(get_asset_ip_addresses("id-1"))
    assert "serverResponseObject" in result


@respx.mock
def test_get_asset_applications(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointPublisherProductVersions/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(get_asset_applications("id-1"))
    assert "serverResponseObject" in result


@respx.mock
def test_list_assets_with_cve(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointVulnerabilities/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [ASSET_STUB]})
    )
    result = json.loads(list_assets_with_cve("CVE-2024-1234"))
    assert len(result["serverResponseObject"]) == 1


@respx.mock
def test_delete_asset(vicarius_env):
    respx.delete(f"{_base()}/endpoint/delete").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    result = json.loads(delete_asset("id-1"))
    assert result["deleted"] is True

from vicarius_mcp.server import list_asset_groups, list_asset_group_members, create_asset_group

GROUP_STUB = {
    "organizationEndpointGroupId": "grp-1",
    "organizationEndpointGroupName": "Servers",
    "organizationEndpointGroupSearchQueries": '[{"searchQueryName":"assetQuery","searchQueryObjectName":"Endpoint","searchQueryObjectJoinByFieldName":"endpointId","searchQueryObjectJoinByForeignFieldName":"endpointId","searchQueryQuery":"endpointAlive=in=(true)"}]',
}


@respx.mock
def test_list_asset_groups(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointGroup/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [GROUP_STUB]})
    )
    result = json.loads(list_asset_groups())
    assert result["serverResponseObject"][0]["organizationEndpointGroupName"] == "Servers"


@respx.mock
def test_list_asset_group_members(vicarius_env):
    # Step 1: fetch group
    respx.get(f"{_base()}/organizationEndpointGroup/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [GROUP_STUB]})
    )
    # Step 2: POST members search
    respx.post(f"{_base()}/endpoint/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [{"endpointId": "id-1", "endpointName": "host1", "endpointAlive": True}]})
    )
    result = json.loads(list_asset_group_members("grp-1"))
    assert result["serverResponseObject"][0]["endpointName"] == "host1"


@respx.mock
def test_create_asset_group(vicarius_env):
    respx.put(f"{_base()}/organizationEndpointGroup/insert").mock(
        return_value=httpx.Response(200, json={"organizationEndpointGroupId": "new-grp"})
    )
    result = json.loads(create_asset_group("New Group", "desc"))
    assert result["organizationEndpointGroupId"] == "new-grp"
