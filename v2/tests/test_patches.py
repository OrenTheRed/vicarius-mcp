import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_patches import (
    search_patches,
    get_patch_summary,
    list_patch_groups,
    create_patch_group,
    update_patch_group,
    delete_patch_group,
    search_available_patches,
    get_reboot_profile,
    update_reboot_profile,
    get_asset_inactivity_settings,
    update_asset_inactivity_settings,
)


@respx.mock
def test_search_patches(vicarius_v2_env):
    respx.post(f"{_base('acme')}/patches").mock(return_value=httpx.Response(200, json=[{"patchIdentifier": "KB1"}]))
    assert json.loads(search_patches(filters={"assetId": "a-1"}))[0]["patchIdentifier"] == "KB1"


@respx.mock
def test_get_patch_summary(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/patches/summary").mock(return_value=httpx.Response(200, json={"missing": 5}))
    result = json.loads(get_patch_summary("s-1"))
    assert result["missing"] == 5
    assert route.calls.last.request.url.params["siteId"] == "s-1"


@respx.mock
def test_patch_groups_crud(vicarius_v2_env):
    respx.get(f"{_base('acme')}/patchGroups").mock(return_value=httpx.Response(200, json=[{"name": "Critical"}]))
    respx.post(f"{_base('acme')}/patchGroups").mock(return_value=httpx.Response(200, json={"name": "Critical"}))
    respx.put(f"{_base('acme')}/patchGroups/pg-1").mock(return_value=httpx.Response(200, json={"name": "Critical2"}))
    respx.delete(f"{_base('acme')}/patchGroups/pg-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(list_patch_groups())[0]["name"] == "Critical"
    assert json.loads(create_patch_group({"name": "Critical", "type": "STATIC"}))["name"] == "Critical"
    assert json.loads(update_patch_group("pg-1", {"name": "Critical2"}))["name"] == "Critical2"
    assert json.loads(delete_patch_group("pg-1")) is True


@respx.mock
def test_search_available_patches(vicarius_v2_env):
    respx.post(f"{_base('acme')}/availablePatches/search").mock(return_value=httpx.Response(200, json=[{"patchIdentifier": "KB2"}]))
    assert json.loads(search_available_patches())[0]["patchIdentifier"] == "KB2"


@respx.mock
def test_reboot_profile(vicarius_v2_env):
    respx.get(f"{_base('acme')}/settings/reboot-profile").mock(return_value=httpx.Response(200, json={"autoRebootSettings": {}}))
    route = respx.put(f"{_base('acme')}/settings/reboot-profile").mock(return_value=httpx.Response(200, json={"autoRebootSettings": {"enabled": True}}))
    assert "autoRebootSettings" in json.loads(get_reboot_profile())
    result = json.loads(update_reboot_profile({"enabled": True}))
    assert result["autoRebootSettings"]["enabled"] is True
    assert json.loads(route.calls.last.request.content) == {"autoRebootSettings": {"enabled": True}}


@respx.mock
def test_asset_inactivity_settings(vicarius_v2_env):
    respx.get(f"{_base('acme')}/v2/asset-inactivity-settings").mock(return_value=httpx.Response(200, json={"assetAutoRemovalDays": 30}))
    route = respx.put(f"{_base('acme')}/v2/asset-inactivity-settings").mock(return_value=httpx.Response(200, json={"assetAutoRemovalDays": 60}))
    assert json.loads(get_asset_inactivity_settings())["assetAutoRemovalDays"] == 30
    result = json.loads(update_asset_inactivity_settings(60))
    assert result["assetAutoRemovalDays"] == 60
    assert json.loads(route.calls.last.request.content) == {"assetAutoRemovalDays": 60}
