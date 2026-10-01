import json
import respx
import httpx
from vicarius_mcp.server import (
    list_automations, get_automation, create_automation,
    update_automation, set_automation_state,
    list_script_templates, list_task_types, _base,
)

AUTO_STUB = {"id": "auto-1", "name": "Patch Servers", "enabled": True}


@respx.mock
def test_list_automations(vicarius_env):
    respx.get(f"{_base()}/v1/automations").mock(
        return_value=httpx.Response(200, json={"data": [AUTO_STUB]})
    )
    result = json.loads(list_automations())
    assert result["data"][0]["id"] == "auto-1"


@respx.mock
def test_get_automation(vicarius_env):
    respx.get(f"{_base()}/v1/automations/auto-1").mock(
        return_value=httpx.Response(200, json=AUTO_STUB)
    )
    result = json.loads(get_automation("auto-1"))
    assert result["name"] == "Patch Servers"


@respx.mock
def test_create_automation(vicarius_env):
    respx.post(f"{_base()}/v1/automations").mock(
        return_value=httpx.Response(200, json={"id": "auto-2"})
    )
    result = json.loads(create_automation({"name": "New Auto"}))
    assert result["id"] == "auto-2"


@respx.mock
def test_update_automation(vicarius_env):
    respx.put(f"{_base()}/v1/automations/auto-1").mock(
        return_value=httpx.Response(200, json=AUTO_STUB)
    )
    result = json.loads(update_automation("auto-1", {"name": "Updated"}))
    assert result["id"] == "auto-1"


@respx.mock
def test_set_automation_state_enable(vicarius_env):
    respx.put(f"{_base()}/v1/automations/auto-1/updateState").mock(
        return_value=httpx.Response(200, json={"enabled": True})
    )
    result = json.loads(set_automation_state("auto-1", True))
    assert result["enabled"] is True


@respx.mock
def test_list_script_templates(vicarius_env):
    respx.get(f"{_base()}/scriptTemplate/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_script_templates())
    assert "serverResponseObject" in result


@respx.mock
def test_list_task_types(vicarius_env):
    respx.get(f"{_base()}/taskEndpointsEvent/taskTypes").mock(
        return_value=httpx.Response(200, json=["patch", "script", "reboot"])
    )
    result = json.loads(list_task_types())
    assert "patch" in result
