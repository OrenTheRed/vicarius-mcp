from __future__ import annotations

import json
from typing import Literal

from .app import read_tool
from .client import _get, seg

# ---------------------------------------------------------------------------
# Distributions & Rankings
# ---------------------------------------------------------------------------

# kind -> (path, optional filters the endpoint accepts besides siteId)
DISTRIBUTIONS = {
    "asset_os": ("/assets/os-distribution", ()),
    "asset_source": ("/assets/source-distribution", ()),
    "asset_status": ("/assets/status-distribution", ()),
    "asset_type": ("/assets/type-distribution", ()),
    "asset_risk": ("/assets/risk-distribution", ("productId",)),
    "finding_severity": ("/findings/severity-distribution", ("assetId", "productId")),
    "finding_status": ("/findings/status-distribution", ()),
    "finding_type": ("/findings/type-distribution", ()),
    "findings_closed": ("/findings/closed-count", ("assetId", "productId")),
    "top_software_by_findings": ("/findings/top-software", ()),
    "software_type": ("/software/type-distribution", ("assetId",)),
    "top_software_by_assets": ("/software/top-by-assets", ()),
    "top_patches_by_assets": ("/availablePatches/top-by-assets", ("assetId", "productId")),
    "patch_summary": ("/patches/summary", ("assetId", "productId")),
    "patch_success_rate": ("/policies/patch/success-rate", ("assetId", "productId")),
}

DistributionKind = Literal[
    "asset_os", "asset_source", "asset_status", "asset_type", "asset_risk", "finding_severity",
    "finding_status", "finding_type", "findings_closed", "top_software_by_findings",
    "software_type", "top_software_by_assets", "top_patches_by_assets", "patch_summary",
    "patch_success_rate",
]


@read_tool
def get_distribution(kind: DistributionKind, site_id: str, asset_id: str | None = None, product_id: str | None = None, tenant: str | None = None) -> str:
    """Get a summary breakdown for a site, the numbers behind the dashboard charts. kind:
    asset_os, asset_source, asset_status, asset_type, asset_risk (assets by OS, source, status,
    type or risk level); finding_severity, finding_status, finding_type (active findings by
    severity, state or type); findings_closed (recently remediated findings);
    top_software_by_findings, top_software_by_assets, top_patches_by_assets (rankings);
    software_type; patch_summary; patch_success_rate. site_id (UUID) is required - get it from
    list_sites. asset_id/product_id narrow the result where the kind supports it."""
    entry = DISTRIBUTIONS.get(kind)
    if entry is None:
        return f'ERROR: kind must be one of {sorted(DISTRIBUTIONS)}, got "{kind}"'
    path, supported = entry
    params = {"siteId": site_id}
    for name, value in (("assetId", asset_id), ("productId", product_id)):
        if value:
            if name not in supported:
                return f'ERROR: kind "{kind}" does not accept {name}'
            params[name] = value
    return _get(path, tenant=tenant, params=params)


@read_tool
def count_policies(params: dict | None = None, tenant: str | None = None) -> str:
    """Count policies without listing them. params accepts the same filters as list_policies,
    e.g. policyTypeIn (SCAN_TIME_BASED, PATCH_TIME_BASED, ...), statusIn, active, scanCategory,
    upcomingOnly, nextRunTimeDateRange.from/to."""
    return _get("/policies/total", tenant=tenant, params=params)


@read_tool
def get_risk_score_history(entity: Literal["asset", "finding"], entity_id: str, params: dict | None = None, tenant: str | None = None) -> str:
    """Get how the risk score of an asset or a finding changed over time, with the event behind
    each change. params supports fromComputedAt (epoch ms), eventId, searchAfter and size."""
    if entity == "asset":
        return _get(f"/assets/{seg(entity_id)}/risk-score-history", tenant=tenant, params=params)
    if entity == "finding":
        return _get(f"/findings/{seg(entity_id)}/risk-score-history", tenant=tenant, params=params)
    return f'ERROR: entity must be "asset" or "finding", got "{entity}"'


# ---------------------------------------------------------------------------
# Trends & KPIs (experimental)
# ---------------------------------------------------------------------------
# These endpoints are used by the vRx web app but are not part of the published Customer API,
# so Vicarius may change them without notice.


@read_tool
def get_findings_trends(date_from: str, date_to: str, granularity: Literal["day", "week", "month"] = "day", tenant: str | None = None) -> str:
    """[Experimental: undocumented endpoint] Get finding trends over time: findings created,
    findings remediated, open backlog, and mean time to remediate (mttrDays), as time series.
    date_from and date_to are YYYY-MM-DD dates; granularity is day, week or month."""
    return _get(
        "/v1/analytics/findings/trends",
        tenant=tenant,
        params={"from": date_from, "to": date_to, "granularity": granularity},
    )


@read_tool
def get_dashboard_summary(tenant: str | None = None) -> str:
    """[Experimental: undocumented endpoints] Get the headline numbers in one call: total,
    active and inactive assets; total software; total findings and active findings per
    severity. Good starting point for an executive summary."""
    summary = {}
    for key, path in (("assets", "/dashboard/assets"), ("software", "/dashboard/software"), ("findings", "/widget/findings")):
        raw = _get(path, tenant=tenant)
        try:
            summary[key] = json.loads(raw)
        except ValueError:
            summary[key] = raw  # an ERROR string, passed through as-is
    return json.dumps(summary, indent=2)
