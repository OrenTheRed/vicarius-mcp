import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_vulnerabilities import (
    search_findings,
    get_finding,
    findings_grouped_by_vulnerability,
    findings_severity_distribution,
    create_vulnerability_exclusion_rule,
    get_vulnerability_exclusion_rule,
    delete_vulnerability_exclusion_rule,
    set_vulnerability_exclusion_rule_state,
    list_exclusion_rules,
    delete_exclusion_rule,
)


@respx.mock
def test_search_findings(vicarius_v2_env):
    respx.get(f"{_base('acme')}/findings").mock(return_value=httpx.Response(200, json=[{"id": "f-1"}]))
    assert json.loads(search_findings(params={"severityIn": ["Critical"]}))[0]["id"] == "f-1"


@respx.mock
def test_get_finding(vicarius_v2_env):
    respx.get(f"{_base('acme')}/findings/f-1").mock(return_value=httpx.Response(200, json={"id": "f-1"}))
    assert json.loads(get_finding("f-1"))["id"] == "f-1"


@respx.mock
def test_findings_grouped_by_vulnerability(vicarius_v2_env):
    respx.get(f"{_base('acme')}/findings/grouped-by-vulnerability").mock(return_value=httpx.Response(200, json=[{"cve": "CVE-2024-1"}]))
    assert json.loads(findings_grouped_by_vulnerability())[0]["cve"] == "CVE-2024-1"


@respx.mock
def test_findings_severity_distribution(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/findings/severity-distribution").mock(return_value=httpx.Response(200, json={"critical": 3}))
    result = json.loads(findings_severity_distribution("s-1"))
    assert result["critical"] == 3
    assert route.calls.last.request.url.params["siteId"] == "s-1"


@respx.mock
def test_vulnerability_exclusion_rule_lifecycle(vicarius_v2_env):
    respx.post(f"{_base('acme')}/exclusionRules/vulnerability").mock(return_value=httpx.Response(200, json={"id": "r-1"}))
    respx.get(f"{_base('acme')}/exclusionRules/vulnerability/r-1").mock(return_value=httpx.Response(200, json={"id": "r-1"}))
    respx.put(f"{_base('acme')}/exclusionRules/vulnerability/r-1/updateState").mock(return_value=httpx.Response(200, json={"id": "r-1", "status": "DISABLED"}))
    respx.delete(f"{_base('acme')}/exclusionRules/vulnerability/r-1").mock(return_value=httpx.Response(200, json=True))

    assert json.loads(create_vulnerability_exclusion_rule({"findingId": "f-1"}))["id"] == "r-1"
    assert json.loads(get_vulnerability_exclusion_rule("r-1"))["id"] == "r-1"
    assert json.loads(set_vulnerability_exclusion_rule_state("r-1", "DISABLED"))["status"] == "DISABLED"
    assert json.loads(delete_vulnerability_exclusion_rule("r-1")) is True


@respx.mock
def test_general_exclusion_rules(vicarius_v2_env):
    respx.get(f"{_base('acme')}/exclusionRules").mock(return_value=httpx.Response(200, json=[{"id": "r-2"}]))
    respx.delete(f"{_base('acme')}/exclusionRules/r-2").mock(return_value=httpx.Response(200, json=True))
    assert json.loads(list_exclusion_rules())[0]["id"] == "r-2"
    assert json.loads(delete_exclusion_rule("r-2")) is True


@respx.mock
def test_list_risk_tags(vicarius_v2_env):
    tags = [{"tagCode": "exploit.ransomware", "category": "EXPLOIT", "platformDefaultWeight": 1.0, "effectiveWeight": 1.0, "overridden": False}]
    route = respx.get(f"{_base('acme')}/v2/risk-tags").mock(return_value=httpx.Response(200, json=tags))
    from vicarius_v2_mcp.tools_vulnerabilities import list_risk_tags
    assert json.loads(list_risk_tags())[0]["tagCode"] == "exploit.ransomware" and route.call_count == 1
