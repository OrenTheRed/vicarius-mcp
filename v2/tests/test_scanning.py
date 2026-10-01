import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_scanning import (
    search_scan_profiles,
    get_scan_profile,
    create_scan_policy,
    get_scan_policy,
    update_scan_policy,
    delete_scan_policy,
    set_scan_policy_state,
    create_patch_policy,
    update_patch_policy,
    set_patch_policy_state,
    create_script_policy,
    update_script_policy,
    set_script_policy_state,
    list_policies,
    list_upcoming_policy_runs,
    list_policy_runs,
    list_policy_run_tasks,
)


@respx.mock
def test_scan_profiles(vicarius_v2_env):
    respx.post(f"{_base('acme')}/scanProfile").mock(return_value=httpx.Response(200, json=[{"id": "sp-1"}]))
    respx.get(f"{_base('acme')}/scanProfile/sp-1").mock(return_value=httpx.Response(200, json={"id": "sp-1"}))
    assert json.loads(search_scan_profiles(filters={"category": "vulnerability"}))[0]["id"] == "sp-1"
    assert json.loads(get_scan_profile("sp-1"))["id"] == "sp-1"


@respx.mock
def test_scan_policy_lifecycle(vicarius_v2_env):
    respx.post(f"{_base('acme')}/policies/scan").mock(return_value=httpx.Response(200, json={"id": "pol-1"}))
    respx.get(f"{_base('acme')}/policies/scan/pol-1").mock(return_value=httpx.Response(200, json={"id": "pol-1"}))
    respx.put(f"{_base('acme')}/policies/scan/pol-1").mock(return_value=httpx.Response(200, json={"id": "pol-1", "name": "Weekly Scan"}))
    route = respx.put(f"{_base('acme')}/policies/scan/pol-1/updateState").mock(return_value=httpx.Response(200, json={"id": "pol-1", "active": False}))
    respx.delete(f"{_base('acme')}/policies/scan/pol-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(create_scan_policy({"name": "Weekly Scan"}))["id"] == "pol-1"
    assert json.loads(get_scan_policy("pol-1"))["id"] == "pol-1"
    assert json.loads(update_scan_policy("pol-1", {"name": "Weekly Scan"}))["name"] == "Weekly Scan"
    result = json.loads(set_scan_policy_state("pol-1", active=False))
    assert result["active"] is False
    assert json.loads(route.calls.last.request.content) == {"active": False}
    assert json.loads(delete_scan_policy("pol-1")) is True


@respx.mock
def test_patch_policy_lifecycle(vicarius_v2_env):
    respx.post(f"{_base('acme')}/policies/patch").mock(return_value=httpx.Response(200, json={"id": "pp-1"}))
    respx.put(f"{_base('acme')}/policies/patch/pp-1").mock(return_value=httpx.Response(200, json={"id": "pp-1"}))
    respx.put(f"{_base('acme')}/policies/patch/pp-1/updateState").mock(return_value=httpx.Response(200, json={"id": "pp-1", "active": True}))

    assert json.loads(create_patch_policy({"name": "Monthly Patch"}))["id"] == "pp-1"
    assert json.loads(update_patch_policy("pp-1", {"name": "Monthly Patch"}))["id"] == "pp-1"
    assert json.loads(set_patch_policy_state("pp-1", active=True))["active"] is True


@respx.mock
def test_script_policy_lifecycle(vicarius_v2_env):
    respx.post(f"{_base('acme')}/policies/script").mock(return_value=httpx.Response(200, json={"id": "scp-1"}))
    respx.put(f"{_base('acme')}/policies/script/scp-1").mock(return_value=httpx.Response(200, json={"id": "scp-1"}))
    respx.put(f"{_base('acme')}/policies/script/scp-1/updateState").mock(return_value=httpx.Response(200, json={"id": "scp-1", "active": False}))

    assert json.loads(create_script_policy({"name": "Cleanup"}))["id"] == "scp-1"
    assert json.loads(update_script_policy("scp-1", {"name": "Cleanup"}))["id"] == "scp-1"
    assert json.loads(set_script_policy_state("scp-1", active=False))["active"] is False


@respx.mock
def test_policies_and_logs(vicarius_v2_env):
    respx.get(f"{_base('acme')}/policies").mock(return_value=httpx.Response(200, json=[{"id": "pol-1"}]))
    respx.get(f"{_base('acme')}/policies/upcoming").mock(return_value=httpx.Response(200, json=[{"id": "pol-2"}]))
    respx.get(f"{_base('acme')}/policy-logs/grouped-by-policy").mock(return_value=httpx.Response(200, json=[{"policyId": "pol-1"}]))
    respx.get(f"{_base('acme')}/policy-logs/flat").mock(return_value=httpx.Response(200, json=[{"taskEntityId": "t-1"}]))

    assert json.loads(list_policies())[0]["id"] == "pol-1"
    assert json.loads(list_upcoming_policy_runs())[0]["id"] == "pol-2"
    assert json.loads(list_policy_runs())[0]["policyId"] == "pol-1"
    assert json.loads(list_policy_run_tasks())[0]["taskEntityId"] == "t-1"


@respx.mock
def test_list_policy_runs_group_by_run(vicarius_v2_env):
    from vicarius_v2_mcp.tools_scanning import list_policy_runs
    by_run = respx.get(f"{_base('acme')}/policy-logs/grouped-by-policy-run").mock(return_value=httpx.Response(200, json=[]))
    list_policy_runs({"size": 1}, group_by="run")
    assert by_run.called


@respx.mock
def test_get_policy_run_details(vicarius_v2_env):
    from vicarius_v2_mcp.tools_scanning import get_policy_run_details
    counts = respx.get(f"{_base('acme')}/policy-logs/status/counts/p-1").mock(return_value=httpx.Response(200, json={"failed": 1}))
    summary = respx.get(f"{_base('acme')}/policy-logs/p-1/1700000000000/export/summary").mock(return_value=httpx.Response(200, json=[]))
    output = respx.get(f"{_base('acme')}/policy-logs/p-1/1700000000000/output/t-1").mock(
        return_value=httpx.Response(200, text="Installation failed", headers={"content-type": "text/plain"}))
    assert json.loads(get_policy_run_details("p-1"))["failed"] == 1
    get_policy_run_details("p-1", "summary", 1700000000000)
    assert summary.calls.last.request.url.params["format"] == "json"
    assert get_policy_run_details("p-1", "task_output", 1700000000000, "t-1") == "Installation failed"
    assert counts.called and output.called
    assert get_policy_run_details("p-1", "summary").startswith("ERROR")
    assert get_policy_run_details("p-1", "task_output", 1700000000000).startswith("ERROR")
