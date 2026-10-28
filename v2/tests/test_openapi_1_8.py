"""1.8.0: tools for the operations in the published API reference (documentation.vicarius.cloud)
that the server did not cover. Each case checks the method, the route and the body sent."""

import json

import httpx
import pytest
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.toolsets import CORE
from vicarius_v2_mcp import tools_assets, tools_compliance, tools_reports, tools_scanning, tools_scripts, tools_sites, tools_tenants

CASES = [
    # (function, kwargs, method, path, expected body or None for no body check)
    (tools_assets.rename_asset, {"asset_id": "a-1", "name": "web-01"}, "PUT", "/assets/a-1/name", {"name": "web-01", "nameOverridden": True}),
    (tools_assets.rename_asset, {"asset_id": "a-1"}, "PUT", "/assets/a-1/name", {"nameOverridden": False}),
    (tools_assets.generate_group_expression, {"kind": "asset", "text": "windows servers"}, "POST", "/assetGroups/generateExpression", {"input": "windows servers"}),
    (tools_assets.generate_group_expression, {"kind": "patch", "text": "chrome"}, "POST", "/patchGroups/generateExpression", {"input": "chrome"}),
    (tools_assets.generate_group_expression, {"kind": "patch", "software_references": [{"productId": "p"}]}, "POST", "/patchGroups/generateExpressionFromSoftware", {"softwareReferences": [{"productId": "p"}]}),
    (tools_assets.list_software_installations, {"platform_information_ids": ["pi-1", "pi-2"]}, "GET", "/software/assets", None),
    (tools_compliance.get_cis_benchmark_catalog, {"summary": True}, "POST", "/complianceBenchmark", None),
    (tools_compliance.get_cis_benchmark_catalog, {}, "POST", "/complianceBenchmark/info", None),
    (tools_scanning.cancel_policy_tasks, {"policy_type": "patch", "policy_id": "pol-1"}, "POST", "/policies/patch/pol-1/cancelTasks", {}),
    (tools_scanning.cancel_policy_tasks, {"policy_type": "script", "policy_id": "pol-2", "task_entity_ids": ["t-1"]}, "POST", "/policies/script/pol-2/cancelTasks", {"taskEntityIds": ["t-1"]}),
    (tools_sites.list_site_agents, {"site_id": "s-1"}, "GET", "/sites/s-1/agents", None),
    (tools_sites.list_site_agents, {}, "GET", "/site-agents", None),
    (tools_sites.list_named_targets, {"site_id": "s-1"}, "GET", "/sites/s-1/named-targets", None),
    (tools_sites.add_named_target_to_site, {"site_id": "s-1", "named_target_id": "nt-1"}, "POST", "/sites/s-1/named-targets", {"id": "nt-1"}),
    (tools_reports.list_reports, {"scheduled": True}, "GET", "/reports/scheduled", None),
    (tools_reports.export_report, {"report_id": "r-1"}, "POST", "/reports/r-1/export", None),
    (tools_reports.set_report_enabled, {"report_id": "r-1", "enabled": False}, "PATCH", "/reports/r-1/enabled", {"enabled": False}),
    (tools_reports.set_report_schedule, {"report_id": "r-1", "schedule": {"frequency": "DAILY"}}, "PATCH", "/reports/r-1/schedule", {"frequency": "DAILY"}),
    (tools_reports.set_report_schedule, {"report_id": "r-1"}, "DELETE", "/reports/r-1/schedule", None),
    (tools_reports.list_public_report_specs, {}, "GET", "/publicReportSpecs", None),
    (tools_reports.list_public_report_specs, {"spec_id": "ps-1"}, "GET", "/publicReportSpecs/ps-1", None),
    (tools_reports.add_public_report, {"spec_id": "ps-1"}, "POST", "/publicReportSpecs/ps-1/link", None),
    (tools_reports.add_public_report, {"spec_id": "ps-1", "mode": "clone", "name": "OS report"}, "POST", "/publicReportSpecs/ps-1/clone", {"name": "OS report"}),
    (tools_scripts.copy_script, {"source_script_id": "sc-1", "name": "Copy"}, "POST", "/privateScripts/sc-1/copy", {"name": "Copy"}),
    (tools_scripts.copy_script, {"source_script_id": "pub-1", "name": "Mine", "description": "d", "from_public": True}, "POST", "/privateScripts/copy-from-public/pub-1", {"name": "Mine", "description": "d"}),
    (tools_scripts.set_private_script_published, {"script_id": "sc-1", "published": True}, "POST", "/privateScripts/sc-1/publish", None),
    (tools_scripts.set_private_script_published, {"script_id": "sc-1", "published": False}, "POST", "/privateScripts/sc-1/unpublish", None),
    (tools_scripts.delete_private_script_file, {"script_id": "sc-1", "os_family": "LINUX", "file_id": "f-1"}, "DELETE", "/privateScripts/sc-1/commands/LINUX/files/f-1", None),
    (tools_scripts.download_script_file, {"script_id": "sc-1", "file_id": "f-1"}, "GET", "/privateScripts/sc-1/files/f-1/download", None),
    (tools_scripts.download_script_file, {"script_id": "pub-1", "file_id": "f-1", "public": True}, "GET", "/publicScripts/pub-1/files/f-1/download", None),
    (tools_tenants.update_user_group_members, {"group_id": "g-1", "user_ids": ["u-1"]}, "POST", "/settings/user-groups/g-1/members/batchRemove", {"userIds": ["u-1"]}),
    (tools_tenants.update_user_group_members, {"group_id": "g-1", "user_ids": ["u-1"], "mode": "replace"}, "PUT", "/settings/user-groups/g-1/members/batchUpdate", {"userIds": ["u-1"]}),
    (tools_tenants.rename_user_group, {"group_id": "g-1", "display_name": "Ops"}, "PUT", "/settings/user-groups/g-1", {"displayName": "Ops"}),
    (tools_tenants.delete_user_group, {"group_id": "g-1"}, "DELETE", "/settings/user-groups/g-1", None),
    (tools_tenants.get_user_group_site_permissions, {"group_id": "g-1"}, "GET", "/settings/user-groups/g-1/sites", None),
    (tools_tenants.get_user_group_site_permissions, {"group_id": "g-1", "site_id": "s-1"}, "GET", "/settings/user-groups/g-1/sites/s-1/grants", None),
    (tools_tenants.update_user_group_site_permission, {"group_id": "g-1", "site_id": "s-1", "permission": "VIEWER"}, "PUT", "/settings/user-groups/g-1/sites/s-1/grants", {"permission": "VIEWER"}),
    (tools_tenants.update_user_group_site_permission, {"group_id": "g-1", "site_id": "s-1"}, "PUT", "/settings/user-groups/g-1/sites/s-1/grants", {"permission": None}),
]


@pytest.mark.parametrize("fn,kwargs,method,path,body", CASES, ids=[f"{c[0].__name__}-{i}" for i, c in enumerate(CASES)])
def test_each_tool_calls_the_documented_route(fn, kwargs, method, path, body):
    with respx.mock(assert_all_called=True) as router:
        route = router.route(method=method, url=f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json={"ok": True}))
        assert json.loads(fn(**kwargs)) == {"ok": True}
        if body is not None:
            assert json.loads(route.calls.last.request.content) == body


def test_software_installations_sends_every_id():
    with respx.mock as router:
        route = router.get(f"{_base('acme')}/software/assets").mock(return_value=httpx.Response(200, json=[]))
        tools_assets.list_software_installations(["pi-1", "pi-2"])
        assert route.calls.last.request.url.params.get_list("platformInformationIds") == ["pi-1", "pi-2"]


def test_bad_input_is_refused_before_any_call():
    with respx.mock(assert_all_mocked=True):
        assert tools_assets.generate_group_expression("asset").startswith("ERROR")
        assert tools_tenants.update_user_group_site_permission("g-1", "s-1", permission="OWNER").startswith("ERROR")


def test_path_ids_are_escaped():
    with respx.mock as router:
        route = router.put(url__startswith=_base("acme")).mock(return_value=httpx.Response(200, json={}))
        tools_assets.rename_asset("../apiKeys", "x")
        assert route.calls.last.request.url.raw_path.decode() == "/api/assets/..%2FapiKeys/name"


def test_no_new_tool_joins_core():
    names = {fn.__name__ for fn, *_ in CASES}
    assert not names & set(CORE)
