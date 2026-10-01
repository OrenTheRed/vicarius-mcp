from __future__ import annotations

from typing import Literal

from .app import read_tool
from .client import _get, _post, seg

# ---------------------------------------------------------------------------
# CIS Benchmarks
# ---------------------------------------------------------------------------


@read_tool
def get_cis_benchmark_catalog(params: dict | None = None, tenant: str | None = None) -> str:
    """Browse the catalog of CIS compliance benchmarks. params supports benchmarkString, title,
    workbenchId, version, isActive, familyIn, fullTextSearch, sort, sortDirection, searchAfter, size."""
    return _post("/complianceBenchmark/info", tenant=tenant, params=params)


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------


@read_tool
def get_compliance_checks(benchmark_id: str, params: dict | None = None, tenant: str | None = None) -> str:
    """List CIS compliance checks (rules) for a benchmark. benchmark_id is required.
    params supports ruleId, groupId, assetId, scanRunId, productId, fullTextSearch, sort,
    sortDirection, searchAfter, size, fields."""
    merged = {"benchmarkId": benchmark_id}
    if params:
        merged.update(params)
    return _get("/v2/compliance/checks", tenant=tenant, params=merged)


@read_tool
def get_compliance_scan_summary(scan_run_id: str, tenant: str | None = None) -> str:
    """Get the pass/fail summary for a single CIS compliance scan run by its scanRunId."""
    return _get(f"/v2/compliance/scan-info/{seg(scan_run_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Compliance Results
# ---------------------------------------------------------------------------

_COMPLIANCE_VIEWS = {
    "results": "/v2/compliance",
    "assets": "/v2/compliance/assets",
    "benchmarks": "/v2/compliance/benchmarks",
    "single_scan": "/v2/compliance/single",
}


@read_tool
def search_compliance(view: Literal["results", "assets", "benchmarks", "single_scan"] = "results", params: dict | None = None, tenant: str | None = None) -> str:
    """Search CIS compliance results. view="results" lists compliance scores, "assets" lists
    scanned assets with their pass/fail counts, "benchmarks" lists the benchmarks evaluated in a
    scan run, and "single_scan" lists the results of individual scans. params supports
    benchmarkId/benchmarkIds, assetId, scanRunId, siteId, productId, publisherId, allRuns,
    sort, sortDirection, searchAfter, size and fields."""
    path = _COMPLIANCE_VIEWS.get(view)
    if path is None:
        return f'ERROR: view must be one of {sorted(_COMPLIANCE_VIEWS)}, got "{view}"'
    return _get(path, tenant=tenant, params=params)


@read_tool
def get_compliance_benchmark_results(benchmark_id: str, params: dict | None = None, tenant: str | None = None) -> str:
    """Get compliance results for one CIS benchmark. params supports assetId, scanRunId, siteId,
    productId, publisherId and allRuns."""
    return _get(f"/v2/compliance/{seg(benchmark_id)}", tenant=tenant, params=params)


@read_tool
def list_compliance_rules(benchmark_id: str, group_id: str | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Browse a CIS benchmark's rules. Without group_id, lists the benchmark's rule groups
    (sections) with pass/fail counts; with group_id, lists the rules in that group. params
    supports assetId, scanRunId, ruleId, fullTextSearch, sort, sortDirection, searchAfter, size."""
    merged = {"benchmarkId": benchmark_id, **(params or {})}
    if group_id:
        return _get(f"/v2/compliance/checks/groups/{seg(group_id)}/rules", tenant=tenant, params=merged)
    return _get("/v2/compliance/checks/groups", tenant=tenant, params=merged)


@read_tool
def get_compliance_rule(rule_id: str, view: Literal["affected_assets", "documentation"] = "affected_assets", params: dict | None = None, tenant: str | None = None) -> str:
    """Drill into one CIS rule. view="affected_assets" lists the assets and their result for the
    rule; view="documentation" returns the rule's description, rationale and remediation steps.
    params supports benchmarkId, groupId, assetId, scanRunId, sort, sortDirection, searchAfter,
    size."""
    if view == "affected_assets":
        return _get("/v2/compliance/checks/details", tenant=tenant, params={"ruleId": rule_id, **(params or {})})
    if view == "documentation":
        return _get("/v2/compliance/checks/full-details", tenant=tenant, params={"ruleId": rule_id, **(params or {})})
    return f'ERROR: view must be "affected_assets" or "documentation", got "{view}"'
