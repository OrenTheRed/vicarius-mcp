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
