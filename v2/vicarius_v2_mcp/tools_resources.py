from __future__ import annotations

from typing import Literal

from .app import read_tool
from .client import _get, seg

# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------

# resource_type -> path template ("{}" is replaced by the encoded id)
RESOURCE_PATHS = {
    "asset_group": "/assetGroups/{}",
    "software_group": "/softwareGroups/{}",
    "patch_group": "/patchGroups/{}",
    "credential": "/credentials/{}",
    "named_target": "/named-targets/{}",
    "patch_policy": "/policies/patch/{}",
    "script_policy": "/policies/script/{}",
    "site_agent": "/site-agents/{}",
    "scanner_configuration": "/scannerConfiguration/{}",
    "private_script": "/privateScripts/{}",
    "public_script": "/publicScripts/{}",
    "report": "/reports/{}",
    "exclusion_rule": "/exclusionRules/{}",
    "scan_report": "/evidence-files/{}",
    "audit_log": "/settings/auditLogs/{}",
    "asset_discovery_finding": "/findings/assetDiscovery/{}",
    "software_discovery_finding": "/findings/softwareDiscovery/{}",
    "software_installation": "/software/assets/{}/detailed",
}

ResourceType = Literal[
    "asset_group", "software_group", "patch_group", "credential", "named_target",
    "patch_policy", "script_policy", "site_agent", "scanner_configuration", "private_script",
    "public_script", "report", "exclusion_rule", "scan_report", "audit_log",
    "asset_discovery_finding", "software_discovery_finding", "software_installation",
]


@read_tool
def get_resource(resource_type: ResourceType, resource_id: str, tenant: str | None = None) -> str:
    """Get one object by its id. resource_type picks the kind of object: asset_group,
    software_group, patch_group, credential (metadata only, secrets are never returned),
    named_target, patch_policy, script_policy, site_agent, scanner_configuration,
    private_script, public_script, report, exclusion_rule, scan_report (evidence-file
    metadata), audit_log (one entry), asset_discovery_finding, software_discovery_finding, or
    software_installation (one software install on one asset, by its assetAppId). For assets,
    sites, findings, scan policies and API keys use get_asset, get_site, get_finding,
    get_scan_policy and get_api_key."""
    template = RESOURCE_PATHS.get(resource_type)
    if template is None:
        return f'ERROR: resource_type must be one of {sorted(RESOURCE_PATHS)}, got "{resource_type}"'
    return _get(template.format(seg(resource_id)), tenant=tenant)


# ---------------------------------------------------------------------------
# Previews
# ---------------------------------------------------------------------------

_PREVIEW_PATHS = {
    "asset": "/assetGroups/preview",
    "software": "/softwareGroups/dynamic/software/preview",
    "patch": "/patchGroups/dynamic/patches/preview",
}


@read_tool
def preview_group_expression(group_type: Literal["asset", "software", "patch"], expression: str, max_items: int | None = None, tenant: str | None = None) -> str:
    """Show which assets, software or patches a dynamic-group expression would match, without
    creating anything. Use it to check an expression before create_asset_group,
    create_software_group or create_patch_group (or their update_ tools). Expressions use the
    same syntax as existing dynamic groups, e.g. asset.name.contains('qa')."""
    path = _PREVIEW_PATHS.get(group_type)
    if path is None:
        return f'ERROR: group_type must be one of {sorted(_PREVIEW_PATHS)}, got "{group_type}"'
    params = {"expression": expression}
    if max_items is not None:
        params["maxItems"] = max_items
    return _get(path, tenant=tenant, params=params)


@read_tool
def get_exclusion_rule_impact(rule_id: str, view: Literal["findings_count", "findings", "affected_assets"] = "findings_count", params: dict | None = None, tenant: str | None = None) -> str:
    """Show what an exclusion (risk-acceptance) rule hides. view="findings_count" returns how
    many findings it matches, "findings" lists them, and "affected_assets" lists the assets a
    vulnerability exclusion rule covers. params supports sort, sortDirection, searchAfter, size
    and fields for the list views."""
    if view == "findings_count":
        return _get("/findings/count-by-exclusion-rule", tenant=tenant, params={"ruleId": rule_id})
    if view == "findings":
        return _get("/findings/find-by-exclusion-rule", tenant=tenant, params={"ruleId": rule_id, **(params or {})})
    if view == "affected_assets":
        return _get(f"/exclusionRules/vulnerability/{seg(rule_id)}/affectedAssets", tenant=tenant, params=params)
    return f'ERROR: view must be one of ["affected_assets", "findings", "findings_count"], got "{view}"'
