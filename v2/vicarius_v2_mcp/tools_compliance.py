from __future__ import annotations

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
