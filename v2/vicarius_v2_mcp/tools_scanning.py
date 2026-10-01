from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg


def _state_body(status: str | None = None, active: bool | None = None, cancel_running_tasks: bool | None = None) -> dict:
    body = {}
    if status is not None:
        body["status"] = status
    if active is not None:
        body["active"] = active
    if cancel_running_tasks is not None:
        body["cancelRunningTasks"] = cancel_running_tasks
    return body


# ---------------------------------------------------------------------------
# Scan Profiles
# ---------------------------------------------------------------------------


@read_tool
def search_scan_profiles(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Browse the catalog of scan profiles (what kind of scan to run - discovery, full
    vulnerability, PCI, HIPAA, CIS, etc). filters (body) supports title, category, scanner,
    scanType, perspectiveIn, supportedOsIn, accessIn, licenseConsumed, fullTextSearch."""
    return _post("/scanProfile", tenant=tenant, params=params, body=filters or {})


@read_tool
def get_scan_profile(profile_id: str, tenant: str | None = None) -> str:
    """Get full details for a single scan profile by its id."""
    return _get(f"/scanProfile/{seg(profile_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Scan Policies
# ---------------------------------------------------------------------------


@write_tool
def create_scan_policy(payload: dict, tenant: str | None = None) -> str:
    """Create a scan policy. payload: name, siteId, target (assets/groups/named targets to scan),
    schedule or eventTrigger, scanner, scanCategory, scanType, benchmarks (for CIS), scanSettings."""
    return _post("/policies/scan", tenant=tenant, body=payload)


@read_tool
def get_scan_policy(policy_id: str, tenant: str | None = None) -> str:
    """Get a scan policy by its id."""
    return _get(f"/policies/scan/{seg(policy_id)}", tenant=tenant)


@destructive_tool
def update_scan_policy(policy_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a scan policy by id. payload is the full/partial policy object."""
    return _put(f"/policies/scan/{seg(policy_id)}", tenant=tenant, body=payload)


@destructive_tool
def delete_scan_policy(policy_id: str, tenant: str | None = None) -> str:
    """Delete a scan policy by its id."""
    return _delete(f"/policies/scan/{seg(policy_id)}", tenant=tenant)


@destructive_tool
def set_scan_policy_state(policy_id: str, active: bool | None = None, status: str | None = None, cancel_running_tasks: bool | None = None, tenant: str | None = None) -> str:
    """Enable/disable a scan policy or change its status. active=True/False toggles it;
    cancel_running_tasks=True also stops any in-flight scans for this policy."""
    return _put(f"/policies/scan/{seg(policy_id)}/updateState", tenant=tenant, body=_state_body(status, active, cancel_running_tasks))


# ---------------------------------------------------------------------------
# Patch Policies
# ---------------------------------------------------------------------------


@write_tool
def create_patch_policy(payload: dict, tenant: str | None = None) -> str:
    """Create a patch policy. payload: name, siteId, target, schedule or eventTrigger,
    patchSelection (patch groups / criteria to install)."""
    return _post("/policies/patch", tenant=tenant, body=payload)


@destructive_tool
def update_patch_policy(policy_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a patch policy by id. payload is the full/partial policy object."""
    return _put(f"/policies/patch/{seg(policy_id)}", tenant=tenant, body=payload)


@destructive_tool
def set_patch_policy_state(policy_id: str, active: bool | None = None, status: str | None = None, cancel_running_tasks: bool | None = None, tenant: str | None = None) -> str:
    """Enable/disable a patch policy or change its status."""
    return _put(f"/policies/patch/{seg(policy_id)}/updateState", tenant=tenant, body=_state_body(status, active, cancel_running_tasks))


# ---------------------------------------------------------------------------
# Script Policies
# ---------------------------------------------------------------------------


@write_tool
def create_script_policy(payload: dict, tenant: str | None = None) -> str:
    """Create a script policy. payload: name, siteId, target, schedule or eventTrigger,
    scripts (list of script ids/config to run)."""
    return _post("/policies/script", tenant=tenant, body=payload)


@destructive_tool
def update_script_policy(policy_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a script policy by id. payload is the full/partial policy object."""
    return _put(f"/policies/script/{seg(policy_id)}", tenant=tenant, body=payload)


@destructive_tool
def set_script_policy_state(policy_id: str, active: bool | None = None, status: str | None = None, cancel_running_tasks: bool | None = None, tenant: str | None = None) -> str:
    """Enable/disable a script policy or change its status."""
    return _put(f"/policies/script/{seg(policy_id)}/updateState", tenant=tenant, body=_state_body(status, active, cancel_running_tasks))


# ---------------------------------------------------------------------------
# Policies (cross-type) & Policy Logs
# ---------------------------------------------------------------------------


@read_tool
def list_policies(params: dict | None = None, tenant: str | None = None) -> str:
    """List all policies (scan/patch/script) with unified filtering. params supports policyType/
    policyTypeIn, active, status/statusIn, name, scanCategory, sort, sortDirection, searchAfter, size."""
    return _get("/policies", tenant=tenant, params=params)


@read_tool
def list_upcoming_policy_runs(params: dict | None = None, tenant: str | None = None) -> str:
    """List policies with an upcoming scheduled run. Accepts the same params as list_policies."""
    return _get("/policies/upcoming", tenant=tenant, params=params)


@read_tool
def list_policy_runs(params: dict | None = None, tenant: str | None = None) -> str:
    """List policy executions grouped by policy. params supports policyId, statusIn, startTime.from/to,
    endTime.from/to, policyName, assetId, sort, sortDirection, searchAfter, size (aka policy-logs)."""
    return _get("/policy-logs/grouped-by-policy", tenant=tenant, params=params)


@read_tool
def list_policy_run_tasks(params: dict | None = None, tenant: str | None = None) -> str:
    """List individual policy run tasks (flat, one row per asset/task). Accepts the same params
    as list_policy_runs."""
    return _get("/policy-logs/flat", tenant=tenant, params=params)
