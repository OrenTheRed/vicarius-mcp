"""Tools added in 1.1.0, and regression tests for the bugs fixed with them."""
import json

import httpx
import pytest
import respx

from vicarius_mcp.server import (
    _base,
    count_objects,
    delete_asset_group,
    get_asset_attributes,
    get_asset_vulnerabilities,
    get_cve_info,
    get_patch_cve_info,
    group_by,
    list_asset_group_members,
    list_patch_catalog,
    list_top_10,
    update_asset_group,
)

GROUP = {"organizationEndpointGroupId": 7, "organizationEndpointGroupName": "Old",
         "organizationEndpointGroupDescription": "keep me", "organizationEndpointGroupSearchQueries": "[]"}


def _mock_group_lookup(found=True):
    return respx.get(f"{_base()}/organizationEndpointGroup/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [GROUP] if found else []}))


@respx.mock
def test_update_asset_group_merges_changes_into_current_group(vicarius_env):
    lookup = _mock_group_lookup()
    update = respx.post(f"{_base()}/organizationEndpointGroup/update").mock(return_value=httpx.Response(200, json={}))
    update_asset_group("7", {"organizationEndpointGroupName": "New"})
    body = json.loads(update.calls.last.request.content)
    assert body["organizationEndpointGroupName"] == "New"
    assert body["organizationEndpointGroupDescription"] == "keep me"
    assert lookup.calls.last.request.url.params["from"] == "0"


@respx.mock
def test_delete_asset_group_sends_group_in_body(vicarius_env):
    _mock_group_lookup()
    delete = respx.delete(f"{_base()}/organizationEndpointGroup/delete").mock(return_value=httpx.Response(200, json={}))
    delete_asset_group("7")
    assert json.loads(delete.calls.last.request.content)["organizationEndpointGroupId"] == 7


@respx.mock
def test_update_and_delete_refuse_unknown_group(vicarius_env):
    _mock_group_lookup(found=False)
    assert update_asset_group("99", {}).startswith("ERROR")
    assert delete_asset_group("99").startswith("ERROR")


@respx.mock
@pytest.mark.parametrize("object_type, path", [
    ("vulnerabilities", "/vulnerability/count"), ("events", "/incidentEvent/count"),
    ("task_events", "/taskEvent/count"), ("task_endpoint_events", "/taskEndpointsEvent/count"),
])
def test_count_objects(vicarius_env, object_type, path):
    route = respx.get(f"{_base()}{path}").mock(return_value=httpx.Response(200, json={"serverResponseCount": 3}))
    assert json.loads(count_objects(object_type, 'x=="y"'))["serverResponseCount"] == 3
    assert route.calls.last.request.url.params["q"] == 'x=="y"'


def test_count_objects_rejects_unknown_type(vicarius_env):
    assert count_objects("assets").startswith("ERROR")


@respx.mock
def test_group_by(vicarius_env):
    route = respx.get(f"{_base()}/aggregation/searchGroup").mock(return_value=httpx.Response(200, json={}))
    group_by("OrganizationEndpointVulnerabilities", "endpointId", q='a=="b"', size=5, include_original_doc=True)
    p = route.calls.last.request.url.params
    assert (p["objectName"], p["group"], p["from"], p["size"], p["q"], p["includeOriginalDoc"]) == \
        ("OrganizationEndpointVulnerabilities", "endpointId", "0", "5", 'a=="b"', "true")


# --- regressions -------------------------------------------------------------


@respx.mock
def test_single_object_searches_send_from(vicarius_env):
    attrs = respx.get(f"{_base()}/endpointAttributes/search").mock(return_value=httpx.Response(200, json={}))
    cve = respx.get(f"{_base()}/vulnerability/search").mock(return_value=httpx.Response(200, json={}))
    top = respx.get(f"{_base()}/aggregation/searchGroup").mock(return_value=httpx.Response(200, json={}))
    get_asset_attributes("a-1")
    get_cve_info("CVE-1")
    list_top_10("assets")
    for route in (attrs, cve, top):
        assert route.calls.last.request.url.params["from"] == "0"
    assert attrs.calls.last.request.url.params["size"] == "100"


@respx.mock
def test_asset_group_members_lookup_sends_from(vicarius_env):
    lookup = _mock_group_lookup()
    respx.post(f"{_base()}/endpoint/search").mock(return_value=httpx.Response(200, json={"serverResponseObject": []}))
    list_asset_group_members("7")
    assert lookup.calls.last.request.url.params["from"] == "0"


@respx.mock
def test_asset_vulnerabilities_filters_on_nested_endpoint_name(vicarius_env):
    route = respx.get(f"{_base()}/organizationEndpointVulnerabilities/search").mock(return_value=httpx.Response(200, json={}))
    get_asset_vulnerabilities(asset_name="web-01")
    assert route.calls.last.request.url.params["q"] == 'organizationEndpointVulnerabilitiesEndpoint.endpointName=="web-01"'


@respx.mock
def test_patch_catalog_and_cve_info_send_required_params(vicarius_env):
    catalog = respx.get(f"{_base()}/patchManagement/patch").mock(return_value=httpx.Response(200, json={}))
    cve = respx.get(f"{_base()}/patchManagement/patch/p-1/cveInfo").mock(return_value=httpx.Response(200, json={}))
    list_patch_catalog(software_type="OS")
    get_patch_cve_info("p-1")
    assert catalog.calls.last.request.url.params["softwareType"] == "OS"
    assert cve.calls.last.request.url.params["source"] == "VICARIUS"
