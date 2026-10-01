import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_sites import (
    list_sites,
    create_site,
    get_site,
    update_site,
    delete_site,
    list_site_agents,
    create_site_agent,
    list_named_targets,
    create_named_target,
    list_credentials,
    create_credential,
    list_scanner_configurations,
    create_scanner_configuration,
)


@respx.mock
def test_sites_crud(vicarius_v2_env):
    respx.get(f"{_base('acme')}/sites").mock(return_value=httpx.Response(200, json=[{"id": "s-1", "name": "Global"}]))
    respx.post(f"{_base('acme')}/sites").mock(return_value=httpx.Response(200, json={"id": "s-2", "name": "Branch"}))
    respx.get(f"{_base('acme')}/sites/s-1").mock(return_value=httpx.Response(200, json={"id": "s-1", "name": "Global"}))
    respx.put(f"{_base('acme')}/sites/s-1").mock(return_value=httpx.Response(200, json={"id": "s-1", "name": "Global HQ"}))
    respx.delete(f"{_base('acme')}/sites/s-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(list_sites())[0]["name"] == "Global"
    assert json.loads(create_site({"name": "Branch"}))["name"] == "Branch"
    assert json.loads(get_site("s-1"))["id"] == "s-1"
    assert json.loads(update_site("s-1", {"name": "Global HQ"}))["name"] == "Global HQ"
    assert json.loads(delete_site("s-1")) is True


@respx.mock
def test_site_agents(vicarius_v2_env):
    respx.get(f"{_base('acme')}/site-agents").mock(return_value=httpx.Response(200, json=[{"id": "a-1"}]))
    route = respx.post(f"{_base('acme')}/site-agents").mock(return_value=httpx.Response(200, json={"id": "a-2"}))
    assert json.loads(list_site_agents())[0]["id"] == "a-1"
    payload = {"name": "linux-01", "siteId": "s-1", "modules": {"cis": True}}
    assert json.loads(create_site_agent(payload))["id"] == "a-2"
    assert json.loads(route.calls.last.request.content) == payload


@respx.mock
def test_named_targets(vicarius_v2_env):
    respx.get(f"{_base('acme')}/named-targets").mock(return_value=httpx.Response(200, json=[{"id": "nt-1"}]))
    respx.post(f"{_base('acme')}/named-targets").mock(return_value=httpx.Response(200, json={"id": "nt-2"}))
    assert json.loads(list_named_targets())[0]["id"] == "nt-1"
    assert json.loads(create_named_target({"name": "dmz"}))["id"] == "nt-2"


@respx.mock
def test_credentials(vicarius_v2_env):
    respx.get(f"{_base('acme')}/credentials").mock(return_value=httpx.Response(200, json=[{"id": "c-1", "type": "LINUX_UNIX_MAC"}]))
    respx.post(f"{_base('acme')}/credentials").mock(return_value=httpx.Response(200, json={"id": "c-2"}))
    assert json.loads(list_credentials())[0]["type"] == "LINUX_UNIX_MAC"
    assert json.loads(create_credential({"name": "root", "type": "LINUX_UNIX_MAC"}))["id"] == "c-2"


@respx.mock
def test_scanner_configurations(vicarius_v2_env):
    respx.get(f"{_base('acme')}/scannerConfiguration").mock(return_value=httpx.Response(200, json=[{"id": "sc-1"}]))
    respx.post(f"{_base('acme')}/scannerConfiguration").mock(return_value=httpx.Response(200, json={"id": "sc-2"}))
    assert json.loads(list_scanner_configurations())[0]["id"] == "sc-1"
    assert json.loads(create_scanner_configuration({"settings": {"key": "value"}}))["id"] == "sc-2"
