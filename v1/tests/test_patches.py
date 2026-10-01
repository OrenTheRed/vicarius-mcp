import json
import respx
import httpx
from vicarius_mcp.server import list_missing_patches, list_pending_reboot_tasks, _base

PATCH_STUB = {"patchPackageFileName": "KB12345.msp", "patchSensitivityLevel": {"sensitivityLevelName": "Critical"}}


@respx.mock
def test_list_missing_patches(vicarius_env):
    respx.get(f"{_base()}/organizationEndpointExternalReferenceExternalReferences/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [PATCH_STUB]})
    )
    result = json.loads(list_missing_patches())
    assert result["serverResponseObject"][0]["patchPackageFileName"] == "KB12345.msp"


@respx.mock
def test_list_missing_patches_by_asset(vicarius_env):
    route = respx.get(f"{_base()}/organizationEndpointExternalReferenceExternalReferences/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    list_missing_patches(asset_name="host1")
    assert route.called


@respx.mock
def test_list_missing_patches_by_severity(vicarius_env):
    route = respx.get(f"{_base()}/organizationEndpointExternalReferenceExternalReferences/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    list_missing_patches(severity="Critical")
    assert route.called


@respx.mock
def test_list_pending_reboot_tasks(vicarius_env):
    respx.get(f"{_base()}/taskEndpointsEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [{"endpointName": "host1"}]})
    )
    result = json.loads(list_pending_reboot_tasks())
    assert result["serverResponseObject"][0]["endpointName"] == "host1"
