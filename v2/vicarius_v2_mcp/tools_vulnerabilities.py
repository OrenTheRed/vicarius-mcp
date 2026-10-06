from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg

# ---------------------------------------------------------------------------
# Vulnerability Findings
# ---------------------------------------------------------------------------


@read_tool
def search_findings(params: dict | None = None, tenant: str | None = None) -> str:
    """Search vulnerability findings. params supports assetId/assetIdIn, findingType/findingTypeIn,
    currentStateIn, siteId, severity/severityIn, cveIds, exploitationStatus, inCisaKev,
    epssScoreRange.min/max, riskScoreRange.min/max, fullTextSearch, sort, sortDirection,
    searchAfter, size, fields."""
    return _get("/findings", tenant=tenant, params=params)


@read_tool
def get_finding(finding_id: str, lean_exploit_intelligence: bool | None = None, tenant: str | None = None) -> str:
    """Get full details for a single finding by its id."""
    params = {"leanExploitIntelligence": lean_exploit_intelligence} if lean_exploit_intelligence is not None else None
    return _get(f"/findings/{seg(finding_id)}", tenant=tenant, params=params)


@read_tool
def findings_grouped_by_vulnerability(params: dict | None = None, tenant: str | None = None) -> str:
    """Search findings grouped by the underlying vulnerability/CVE, deduping across assets.
    Accepts the same filter params as search_findings, plus "from" and "startsWith"."""
    return _get("/findings/grouped-by-vulnerability", tenant=tenant, params=params)


@read_tool
def findings_severity_distribution(site_id: str, asset_id: str | None = None, product_id: str | None = None, tenant: str | None = None) -> str:
    """Get active finding counts bucketed by severity for a site. site_id (UUID) is required."""
    params = {"siteId": site_id}
    if asset_id:
        params["assetId"] = asset_id
    if product_id:
        params["productId"] = product_id
    return _get("/findings/severity-distribution", tenant=tenant, params=params)


@read_tool
def list_risk_tags(tenant: str | None = None) -> str:
    """List the vTags (risk tags) that feed a finding's risk score: each has a tagCode (such as
    exploit.ransomware), a displayName, an explanation, a category (EXPLOIT or INTELLIGENCE), the
    platformDefaultWeight and the effectiveWeight, and whether an admin changed it (overridden).
    A finding's own tags are in the riskTags of get_finding. The whole catalogue (about 20 tags) comes back
    in one reply; it is not paged and takes no filters. This tool only reads: it cannot change a weight."""
    return _get("/v2/risk-tags", tenant=tenant)


# ---------------------------------------------------------------------------
# Vulnerability Exclusion Rules
# ---------------------------------------------------------------------------


@write_tool
def create_vulnerability_exclusion_rule(payload: dict, tenant: str | None = None) -> str:
    """Create a vulnerability exclusion (risk-acceptance) rule. payload defines the matching
    criteria (findingId, assetGroupIds, cveIds, etc.), name, and expirationDate."""
    return _post("/exclusionRules/vulnerability", tenant=tenant, body=payload)


@read_tool
def get_vulnerability_exclusion_rule(rule_id: str, tenant: str | None = None) -> str:
    """Get a vulnerability exclusion rule by its id."""
    return _get(f"/exclusionRules/vulnerability/{seg(rule_id)}", tenant=tenant)


@destructive_tool
def delete_vulnerability_exclusion_rule(rule_id: str, tenant: str | None = None) -> str:
    """Delete a vulnerability exclusion rule by its id."""
    return _delete(f"/exclusionRules/vulnerability/{seg(rule_id)}", tenant=tenant)


@write_tool
def set_vulnerability_exclusion_rule_state(rule_id: str, status: str, tenant: str | None = None) -> str:
    """Enable or disable a vulnerability exclusion rule. status is the rule's status value
    (e.g. "ACTIVE"/"DISABLED" - see the rule's current "status" field for the exact enum)."""
    return _put(f"/exclusionRules/vulnerability/{seg(rule_id)}/updateState", tenant=tenant, body={"status": status})


# ---------------------------------------------------------------------------
# Exclusion Rules (all types)
# ---------------------------------------------------------------------------


@read_tool
def list_exclusion_rules(params: dict | None = None, tenant: str | None = None) -> str:
    """List all exclusion rules (any type). params supports type, status, userId, name,
    fullTextSearch, expirationDateRange.from/to, findingId, sort, sortDirection, searchAfter, size."""
    return _get("/exclusionRules", tenant=tenant, params=params)


@destructive_tool
def delete_exclusion_rule(rule_id: str, tenant: str | None = None) -> str:
    """Delete any exclusion rule by its id, regardless of type."""
    return _delete(f"/exclusionRules/{seg(rule_id)}", tenant=tenant)
