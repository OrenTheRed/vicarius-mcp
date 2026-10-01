import json
import respx
import httpx
from vicarius_mcp.server import (
    list_active_cves, list_cves_by_severity, get_cve_info,
    get_asset_vulnerabilities, _base,
)

CVE_STUB = {"vulnerabilityId": "CVE-2024-1234", "vulnerabilitySensitivityLevel": {"sensitivityLevelName": "Critical"}}


@respx.mock
def test_list_active_cves(vicarius_env):
    respx.get(f"{_base()}/aggregation/searchGroup").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [CVE_STUB], "serverResponseCount": 1})
    )
    result = json.loads(list_active_cves())
    assert result["serverResponseObject"][0]["vulnerabilityId"] == "CVE-2024-1234"


@respx.mock
def test_list_cves_by_severity(vicarius_env):
    route = respx.get(f"{_base()}/vulnerability/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [CVE_STUB]})
    )
    result = json.loads(list_cves_by_severity("Critical"))
    assert route.called
    assert result["serverResponseObject"][0]["vulnerabilityId"] == "CVE-2024-1234"


def test_list_cves_invalid_severity(vicarius_env):
    result = list_cves_by_severity("Unknown")
    assert result.startswith("ERROR")


@respx.mock
def test_get_cve_info(vicarius_env):
    respx.get(f"{_base()}/vulnerability/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [CVE_STUB]})
    )
    result = json.loads(get_cve_info("CVE-2024-1234"))
    assert result["serverResponseObject"][0]["vulnerabilityId"] == "CVE-2024-1234"


@respx.mock
def test_get_asset_vulnerabilities(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointVulnerabilities/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [CVE_STUB]})
    )
    result = json.loads(get_asset_vulnerabilities())
    assert len(result["serverResponseObject"]) == 1


@respx.mock
def test_get_asset_vulnerabilities_with_filter(vicarius_env):
    route = respx.get(f"{_base()}/organizationEndpointVulnerabilities/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    get_asset_vulnerabilities(asset_name="host1")
    assert route.called
