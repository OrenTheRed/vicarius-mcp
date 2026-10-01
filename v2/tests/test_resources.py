import json

import httpx
import pytest
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_resources import (
    RESOURCE_PATHS,
    get_exclusion_rule_impact,
    get_resource,
    preview_group_expression,
)


@respx.mock
@pytest.mark.parametrize("resource_type", sorted(RESOURCE_PATHS))
def test_get_resource_routes_every_type(vicarius_v2_env, resource_type):
    path = RESOURCE_PATHS[resource_type].format("x-1")
    route = respx.get(f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json={"id": "x-1"}))
    assert json.loads(get_resource(resource_type, "x-1"))["id"] == "x-1"
    assert route.called


def test_get_resource_rejects_unknown_type(vicarius_v2_env):
    assert get_resource("asset", "x-1").startswith("ERROR")


@respx.mock
def test_get_resource_redacts_credential_secrets(vicarius_v2_env):
    respx.get(f"{_base('acme')}/credentials/c-1").mock(return_value=httpx.Response(200, json={
        "id": "c-1", "attributes": {"username": "svc", "password": "hunter2", "privateKey": "-----BEGIN", "passphrase": ""},
    }))
    attrs = json.loads(get_resource("credential", "c-1"))["attributes"]
    assert attrs == {"username": "svc", "password": "<redacted>", "privateKey": "<redacted>", "passphrase": ""}


@respx.mock
@pytest.mark.parametrize("group_type, path", [
    ("asset", "/assetGroups/preview"),
    ("software", "/softwareGroups/dynamic/software/preview"),
    ("patch", "/patchGroups/dynamic/patches/preview"),
])
def test_preview_group_expression(vicarius_v2_env, group_type, path):
    route = respx.get(f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json=[]))
    preview_group_expression(group_type, "asset.name.contains('qa')", max_items=5)
    params = route.calls.last.request.url.params
    assert params["expression"] == "asset.name.contains('qa')"
    assert params["maxItems"] == "5"


@respx.mock
def test_get_exclusion_rule_impact_views(vicarius_v2_env):
    count = respx.get(f"{_base('acme')}/findings/count-by-exclusion-rule").mock(return_value=httpx.Response(200, json=7))
    found = respx.get(f"{_base('acme')}/findings/find-by-exclusion-rule").mock(return_value=httpx.Response(200, json=[]))
    assets = respx.get(f"{_base('acme')}/exclusionRules/vulnerability/r-1/affectedAssets").mock(return_value=httpx.Response(200, json=[]))
    assert json.loads(get_exclusion_rule_impact("r-1")) == 7
    get_exclusion_rule_impact("r-1", "findings", {"size": 2})
    assert found.calls.last.request.url.params["ruleId"] == "r-1"
    get_exclusion_rule_impact("r-1", "affected_assets")
    assert count.called and assets.called
