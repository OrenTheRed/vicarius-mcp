import json
import respx
import httpx
from vicarius_mcp.server import (
    list_event_log, list_cve_events, list_task_events,
    list_completed_tasks, list_top_10, list_endpoint_tags, _base,
)


@respx.mock
def test_list_event_log(vicarius_env):
    respx.get(f"{_base()}/incidentEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": [{"eventType": "patch"}]})
    )
    result = json.loads(list_event_log())
    assert result["serverResponseObject"][0]["eventType"] == "patch"


@respx.mock
def test_list_event_log_since(vicarius_env):
    route = respx.get(f"{_base()}/incidentEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    list_event_log(since_epoch_ns=1682913600000000000)
    assert route.called


@respx.mock
def test_list_cve_events(vicarius_env):
    respx.get(f"{_base()}/incidentEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_cve_events())
    assert "serverResponseObject" in result


@respx.mock
def test_list_task_events(vicarius_env):
    respx.get(f"{_base()}/taskEndpointsEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_task_events())
    assert "serverResponseObject" in result


@respx.mock
def test_list_completed_tasks(vicarius_env):
    respx.get(f"{_base()}/taskEndpointsEvent/filter").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_completed_tasks("Succeeded"))
    assert "serverResponseObject" in result


def test_list_completed_tasks_invalid_status(vicarius_env):
    result = list_completed_tasks("Pending")
    assert result.startswith("ERROR")


@respx.mock
def test_list_top_10_assets(vicarius_env):
    respx.get(f"{_base()}/aggregation/searchGroup").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_top_10("assets"))
    assert "serverResponseObject" in result


@respx.mock
def test_list_endpoint_tags(vicarius_env):
    respx.get(f"{_base()}/endpointAttributes/search").mock(
        return_value=httpx.Response(200, json={"serverResponseObject": []})
    )
    result = json.loads(list_endpoint_tags())
    assert "serverResponseObject" in result
