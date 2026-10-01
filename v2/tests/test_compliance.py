import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_compliance import (
    get_cis_benchmark_catalog,
    get_compliance_checks,
    get_compliance_scan_summary,
)


@respx.mock
def test_get_cis_benchmark_catalog(vicarius_v2_env):
    route = respx.post(f"{_base('acme')}/complianceBenchmark/info").mock(
        return_value=httpx.Response(200, json=[{"benchmarkString": "CIS_Windows_10"}])
    )
    result = json.loads(get_cis_benchmark_catalog(params={"isActive": True}))
    assert result[0]["benchmarkString"] == "CIS_Windows_10"
    assert route.calls.last.request.url.params["isActive"] == "true"


@respx.mock
def test_get_compliance_checks(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/v2/compliance/checks").mock(
        return_value=httpx.Response(200, json=[{"ruleId": "r-1"}])
    )
    result = json.loads(get_compliance_checks("bm-1"))
    assert result[0]["ruleId"] == "r-1"
    assert route.calls.last.request.url.params["benchmarkId"] == "bm-1"


@respx.mock
def test_get_compliance_scan_summary(vicarius_v2_env):
    respx.get(f"{_base('acme')}/v2/compliance/scan-info/run-1").mock(
        return_value=httpx.Response(200, json={"passed": 10, "failed": 2})
    )
    result = json.loads(get_compliance_scan_summary("run-1"))
    assert result["passed"] == 10


@respx.mock
def test_search_compliance_views(vicarius_v2_env):
    from vicarius_v2_mcp.tools_compliance import search_compliance
    for view, path in [("results", "/v2/compliance"), ("assets", "/v2/compliance/assets"),
                       ("benchmarks", "/v2/compliance/benchmarks"), ("single_scan", "/v2/compliance/single")]:
        route = respx.get(f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json=[]))
        search_compliance(view, {"siteId": "s-1"})
        assert route.called, view
    assert search_compliance("nope").startswith("ERROR")


@respx.mock
def test_compliance_drill_down(vicarius_v2_env):
    from vicarius_v2_mcp.tools_compliance import get_compliance_benchmark_results, get_compliance_rule, list_compliance_rules
    bench = respx.get(f"{_base('acme')}/v2/compliance/b-1").mock(return_value=httpx.Response(200, json=[]))
    groups = respx.get(f"{_base('acme')}/v2/compliance/checks/groups").mock(return_value=httpx.Response(200, json=[]))
    rules = respx.get(f"{_base('acme')}/v2/compliance/checks/groups/g-1/rules").mock(return_value=httpx.Response(200, json=[]))
    details = respx.get(f"{_base('acme')}/v2/compliance/checks/details").mock(return_value=httpx.Response(200, json=[]))
    docs = respx.get(f"{_base('acme')}/v2/compliance/checks/full-details").mock(return_value=httpx.Response(200, json={}))
    get_compliance_benchmark_results("b-1")
    list_compliance_rules("b-1")
    assert groups.calls.last.request.url.params["benchmarkId"] == "b-1"
    list_compliance_rules("b-1", group_id="g-1")
    get_compliance_rule("r-1")
    assert details.calls.last.request.url.params["ruleId"] == "r-1"
    get_compliance_rule("r-1", "documentation")
    assert all(r.called for r in (bench, rules, docs))
