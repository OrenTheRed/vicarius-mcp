import json

import httpx
import pytest
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_insights import (
    DISTRIBUTIONS,
    count_policies,
    get_dashboard_summary,
    get_distribution,
    get_findings_trends,
    get_risk_score_history,
)


@respx.mock
@pytest.mark.parametrize("kind", sorted(DISTRIBUTIONS))
def test_get_distribution_routes_every_kind(vicarius_v2_env, kind):
    route = respx.get(f"{_base('acme')}{DISTRIBUTIONS[kind][0]}").mock(return_value=httpx.Response(200, json={"buckets": []}))
    get_distribution(kind, "s-1")
    assert route.calls.last.request.url.params["siteId"] == "s-1"


@respx.mock
def test_get_distribution_passes_supported_filters(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/findings/severity-distribution").mock(return_value=httpx.Response(200, json={}))
    get_distribution("finding_severity", "s-1", asset_id="a-1", product_id="p-1")
    params = route.calls.last.request.url.params
    assert (params["assetId"], params["productId"]) == ("a-1", "p-1")


def test_get_distribution_rejects_unsupported_filter(vicarius_v2_env):
    assert get_distribution("asset_os", "s-1", asset_id="a-1").startswith("ERROR")
    assert get_distribution("nope", "s-1").startswith("ERROR")


@respx.mock
def test_count_policies(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/policies/total").mock(return_value=httpx.Response(200, json={"active": 3}))
    assert json.loads(count_policies({"active": True}))["active"] == 3
    assert route.calls.last.request.url.params["active"] == "true"


@respx.mock
def test_get_risk_score_history(vicarius_v2_env):
    a = respx.get(f"{_base('acme')}/assets/a-1/risk-score-history").mock(return_value=httpx.Response(200, json=[]))
    f = respx.get(f"{_base('acme')}/findings/f-1/risk-score-history").mock(return_value=httpx.Response(200, json=[]))
    get_risk_score_history("asset", "a-1")
    get_risk_score_history("finding", "f-1", {"size": 3})
    assert a.called and f.called
    assert get_risk_score_history("site", "s-1").startswith("ERROR")


@respx.mock
def test_get_findings_trends(vicarius_v2_env):
    route = respx.get(f"{_base('acme')}/v1/analytics/findings/trends").mock(return_value=httpx.Response(200, json={"series": {}}))
    get_findings_trends("2026-07-01", "2026-10-01", "week")
    params = route.calls.last.request.url.params
    assert (params["from"], params["to"], params["granularity"]) == ("2026-07-01", "2026-10-01", "week")


@respx.mock
def test_get_dashboard_summary_combines_and_tolerates_errors(vicarius_v2_env):
    respx.get(f"{_base('acme')}/dashboard/assets").mock(return_value=httpx.Response(200, json={"totalAssets": 5}))
    respx.get(f"{_base('acme')}/dashboard/software").mock(return_value=httpx.Response(500, text="boom"))
    respx.get(f"{_base('acme')}/widget/findings").mock(return_value=httpx.Response(200, json={"totalFindings": 9}))
    result = json.loads(get_dashboard_summary())
    assert result["assets"] == {"totalAssets": 5}
    assert result["software"].startswith("ERROR 500")
    assert result["findings"]["totalFindings"] == 9
