import json
import respx
import httpx
from vicarius_mcp.server import (
    list_patch_catalog, get_patch_cve_info, list_endpoint_patch_packages,
    list_publisher_products, list_endpoint_vulnerabilities, _base,
)

PATCH_STUB = {"patchId": "p-1", "patchName": "KB12345"}
PRODUCT_STUB = {"publisherName": "Microsoft", "productName": "Office"}


@respx.mock
def test_list_patch_catalog(vicarius_env):
    respx.get(f"{_base()}/patchManagement/patch").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [PATCH_STUB]})
    )
    result = json.loads(list_patch_catalog())
    assert result["serverResponseObject"][0]["patchId"] == "p-1"


@respx.mock
def test_get_patch_cve_info(vicarius_env):
    respx.get(f"{_base()}/patchManagement/patch/p-1/cveInfo").mock(
        return_value=httpx.Response(200, json={"cves": ["CVE-2024-1234"]})
    )
    result = json.loads(get_patch_cve_info("p-1"))
    assert "CVE-2024-1234" in result["cves"]


@respx.mock
def test_list_endpoint_patch_packages(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointPatchPatchPackages/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_endpoint_patch_packages())
    assert "serverResponseObject" in result


@respx.mock
def test_list_publisher_products(vicarius_env):
    respx.get(f"{_base()}/organizationPublisherProducts/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [PRODUCT_STUB]})
    )
    result = json.loads(list_publisher_products())
    assert result["serverResponseObject"][0]["publisherName"] == "Microsoft"


@respx.mock
def test_list_endpoint_vulnerabilities(vicarius_env):
    respx.get(f"{_base()}/endpointVulnerability/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_endpoint_vulnerabilities())
    assert "serverResponseObject" in result


@respx.mock
def test_list_endpoint_vulnerabilities_with_asset(vicarius_env):
    route = respx.get(f"{_base()}/endpointVulnerability/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    list_endpoint_vulnerabilities(asset_name="host1")
    assert route.called
