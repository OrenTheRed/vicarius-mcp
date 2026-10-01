from __future__ import annotations

import json
import os
import re
import sys
from typing import Literal
from urllib.parse import quote

import fastmcp
import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__

# FastMCP otherwise contacts pypi.org on startup to check for a newer version of itself.
fastmcp.settings.check_for_updates = "off"

mcp = FastMCP(
    "vicarius",
    version=__version__,
    instructions=(
        "Tools for the Vicarius vRx External Data API of a single dashboard. List tools paginate "
        "with `from_` and `size`; `q` arguments take RSQL filter expressions."
    ),
)
TIMEOUT = httpx.Timeout(30.0, connect=5.0)

# Tag applied to every tool that changes state. VICARIUS_READ_ONLY=true hides all of them.
WRITE_TAG = "write"
_TRUTHY = {"1", "true", "yes", "on"}

_DASHBOARD_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def read_tool(fn):
    """Register a tool that only reads data."""
    return mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(fn)


def write_tool(fn):
    """Register a tool that creates or changes data without destroying existing data."""
    return mcp.tool(
        tags={WRITE_TAG},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True),
    )(fn)


def destructive_tool(fn):
    """Register a tool that deletes or overwrites existing data."""
    return mcp.tool(
        tags={WRITE_TAG},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True),
    )(fn)


def read_only_enabled() -> bool:
    return os.environ.get("VICARIUS_READ_ONLY", "").strip().lower() in _TRUTHY


def enforce_read_only() -> None:
    if read_only_enabled():
        mcp.disable(tags={WRITE_TAG})


def _dashboard() -> str:
    """The dashboard subdomain. Accepts "acme", "acme.vicarius.cloud" or
    "https://acme.vicarius.cloud/" and always returns just "acme"."""
    v = os.environ.get("VICARIUS_DASHBOARD", "").strip().lower()
    if not v:
        raise RuntimeError("VICARIUS_DASHBOARD env var is required")
    v = re.sub(r"^https?://", "", v).split("/")[0]
    v = v.removesuffix(".vicarius.cloud")
    if not _DASHBOARD_RE.fullmatch(v):
        raise RuntimeError(
            'VICARIUS_DASHBOARD must be your dashboard subdomain, e.g. "acme" for acme.vicarius.cloud'
        )
    return v


def _api_key() -> str:
    v = os.environ.get("VICARIUS_API_KEY", "").strip()
    if not v:
        raise RuntimeError("VICARIUS_API_KEY env var is required")
    return v


def _base() -> str:
    return f"https://{_dashboard()}.vicarius.cloud/vicarius-external-data-api"


def _headers() -> dict[str, str]:
    return {"vicarius-token": _api_key()}


def _rsql(value: object) -> str:
    """Escape a value for use inside a quoted RSQL literal, so input such as
    'x";endpointId=="*' can't break out of the string and widen the query."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")


def _seg(value: object) -> str:
    """Percent-encode a value for use as a single URL path segment, so an id like
    "../other" can't redirect a request to a different endpoint. Empty, "." and ".." are
    refused because they would still collapse onto the parent path."""
    text = str(value).strip()
    if text in ("", ".", ".."):
        raise ValueError(f"Invalid id {str(value)!r}")
    return quote(text, safe="")


def _result(r: httpx.Response, empty: dict) -> str:
    if not r.is_success:
        return f"ERROR {r.status_code}: {r.text}"
    if not r.text:
        return json.dumps(empty, indent=2)
    try:
        return json.dumps(r.json(), indent=2)
    except ValueError:
        return json.dumps({"contentType": r.headers.get("content-type", ""), "contentLength": len(r.content),
                           "note": "Non-JSON response body not returned inline."}, indent=2)


def _get(path: str, params: dict | None = None) -> str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(f"{_base()}{path}", headers=_headers(), params=params)
        return _result(r, {"ok": True})
    except Exception as exc:
        return f"ERROR: {exc}"


def _post(path: str, params: dict | None = None, body: object = None) -> str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.post(f"{_base()}{path}", headers=_headers(), params=params, json=body)
        return _result(r, {"ok": True})
    except Exception as exc:
        return f"ERROR: {exc}"


def _put(path: str, params: dict | None = None, body: object = None) -> str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.put(f"{_base()}{path}", headers=_headers(), params=params, json=body)
        return _result(r, {"ok": True})
    except Exception as exc:
        return f"ERROR: {exc}"


def _delete(path: str, params: dict | None = None, body: object = None) -> str:
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.request("DELETE", f"{_base()}{path}", headers=_headers(), params=params, json=body)
        return _result(r, {"deleted": True})
    except Exception as exc:
        return f"ERROR: {exc}"


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

@read_tool
def list_assets(from_: int = 0, size: int = 100, q: str = "") -> str:
    """List all assets (endpoints) in the tenant. Paginate with from_ and size."""
    params: dict = {"from": from_, "size": size}
    if q:
        params["q"] = q
    return _get("/endpoint/search", params=params)


@read_tool
def get_asset_attributes(asset_id: str) -> str:
    """Get hardware and OS attributes for a single asset by its endpointId."""
    return _get("/endpointAttributes/search", params={"q": f'endpointId=="{_rsql(asset_id)}"', "from": 0, "size": 100})


@read_tool
def get_asset_ip_addresses(asset_id: str) -> str:
    """Get IP address information for a single asset by its endpointId."""
    return _get("/endpointAttributes/search", params={"q": f'endpointId=="{_rsql(asset_id)}"', "from": 0, "size": 100, "includeFields": "endpointAttributesIpAddresses"})


@read_tool
def get_asset_applications(asset_id: str, from_: int = 0, size: int = 100) -> str:
    """List installed applications for a single asset by its endpointId."""
    return _get(
        "/organizationEndpointPublisherProductVersions/search",
        params={"from": from_, "size": size, "q": f'endpointId=="{_rsql(asset_id)}"'},
    )


@read_tool
def list_assets_with_cve(cve_id: str, from_: int = 0, size: int = 100) -> str:
    """List all assets affected by a specific CVE ID (e.g. CVE-2024-1234)."""
    return _get(
        "/organizationEndpointVulnerabilities/search",
        params={"from": from_, "size": size, "q": f'vulnerabilityId=="{_rsql(cve_id)}"'},
    )


@destructive_tool
def delete_asset(asset_id: str) -> str:
    """Remove an asset from the tenant by its endpointId."""
    return _delete("/endpoint/delete", params={"id": asset_id})


# ---------------------------------------------------------------------------
# Asset Groups
# ---------------------------------------------------------------------------

@read_tool
def list_asset_groups(from_: int = 0, size: int = 100) -> str:
    """List all asset groups in the tenant."""
    return _get(
        "/organizationEndpointGroup/search",
        params={"from": from_, "size": size, "sort": "-organizationEndpointGroupUpdatedAt"},
    )


def _find_asset_group(group_id: str) -> dict | str:
    """Fetch one asset group object by id, or return an ERROR string."""
    raw = _get("/organizationEndpointGroup/search", params={"q": f'organizationEndpointGroupId=="{_rsql(group_id)}"', "from": 0, "size": 1})
    if raw.startswith("ERROR"):
        return raw
    objects = json.loads(raw).get("serverResponseObject", [])
    if not objects:
        return f'ERROR: asset group "{group_id}" not found'
    return objects[0]


@read_tool
def list_asset_group_members(group_id: str, from_: int = 0, size: int = 100) -> str:
    """List all assets that belong to a specific asset group (two-step: fetch group then query members)."""
    group = _find_asset_group(group_id)
    if isinstance(group, str):
        if "not found" in group:
            return json.dumps({"serverResponseObject": [], "serverResponseCount": 0}, indent=2)
        return group
    search_queries_raw = group.get("organizationEndpointGroupSearchQueries", "[]")
    search_queries = json.loads(search_queries_raw) if isinstance(search_queries_raw, str) else search_queries_raw
    return _post("/endpoint/search", params={"from": from_, "size": size}, body=search_queries)


@write_tool
def create_asset_group(name: str, description: str = "", query: str = "") -> str:
    """Create a new asset group. Returns the created group object."""
    payload = {
        "organizationEndpointGroupName": name,
        "organizationEndpointGroupDescription": description,
        "organizationEndpointGroupQuery": query,
    }
    return _put("/organizationEndpointGroup/insert", body=payload)


@destructive_tool
def update_asset_group(group_id: str, changes: dict) -> str:
    """Update an asset group. changes holds only the fields to change, e.g.
    {"organizationEndpointGroupName": "...", "organizationEndpointGroupDescription": "...",
    "organizationEndpointGroupQuery": "..."}. The current group is fetched first and the changes
    merged into it, so fields you don't mention keep their values."""
    group = _find_asset_group(group_id)
    if isinstance(group, str):
        return group
    return _post("/organizationEndpointGroup/update", body={**group, **changes})


@destructive_tool
def delete_asset_group(group_id: str) -> str:
    """Delete an asset group by its organizationEndpointGroupId. The assets themselves are not
    affected."""
    group = _find_asset_group(group_id)
    if isinstance(group, str):
        return group
    return _delete("/organizationEndpointGroup/delete", body=group)


# ---------------------------------------------------------------------------
# CVEs / Vulnerabilities
# ---------------------------------------------------------------------------

_VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


@read_tool
def list_active_cves(from_: int = 1, size: int = 500) -> str:
    """List all active CVEs across the tenant. Returns CVE IDs, severity, and affected asset count."""
    return _get(
        "/aggregation/searchGroup",
        params={
            "from": from_, "size": size,
            "objectName": "OrganizationEndpointVulnerabilities",
            "group": "vulnerabilityId",
            "includeOriginalDoc": "true",
            "assetCount": "true",
            "sort": "aggregationId",
            "sumLastSubAggregationBuckets": 1,
        },
    )


@read_tool
def list_cves_by_severity(severity: str, from_: int = 0, size: int = 100) -> str:
    """List CVEs filtered by severity. severity must be one of: Critical, High, Medium, Low."""
    if severity not in _VALID_SEVERITIES:
        return f'ERROR: severity must be one of {sorted(_VALID_SEVERITIES)}, got "{severity}"'
    return _get(
        "/vulnerability/search",
        params={"from": from_, "size": size, "q": f'vulnerabilitySensitivityLevel.sensitivityLevelName=="{_rsql(severity)}"'},
    )


@read_tool
def get_cve_info(cve_id: str) -> str:
    """Get detailed information for a specific CVE ID (CVSS score, description, references)."""
    return _get("/vulnerability/search", params={"q": f'vulnerabilityId=="{_rsql(cve_id)}"', "from": 0, "size": 1})


@read_tool
def get_asset_vulnerabilities(from_: int = 0, size: int = 100, asset_name: str = "") -> str:
    """List vulnerabilities across all assets, optionally filtered to a specific asset by name."""
    params: dict = {"from": from_, "size": size}
    if asset_name:
        params["q"] = f'organizationEndpointVulnerabilitiesEndpoint.endpointName=="{_rsql(asset_name)}"'
    return _get("/organizationEndpointVulnerabilities/search", params=params)


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

@read_tool
def list_missing_patches(from_: int = 0, size: int = 100, asset_name: str = "", severity: str = "") -> str:
    """List missing patches. Filter by asset_name (endpoint name) and/or severity (Critical/High/Medium/Low/N/A)."""
    q_parts = []
    if asset_name:
        q_parts.append(f'organizationEndpointExternalReferenceExternalReferencesEndpoint.endpointName=="{_rsql(asset_name)}"')
    if severity:
        q_parts.append(f"organizationEndpointExternalReferenceExternalReferencesPatches.patchSensitivityLevel.sensitivityLevelName=='{_rsql(severity)}'")
    params: dict = {"from": from_, "size": size}
    if q_parts:
        params["q"] = ";".join(q_parts)
    return _get("/organizationEndpointExternalReferenceExternalReferences/search", params=params)


@read_tool
def list_pending_reboot_tasks(from_: int = 0, size: int = 100) -> str:
    """List endpoints and patch names where patching completed but a reboot is still pending."""
    return _get(
        "/taskEndpointsEvent/filter",
        params={
            "from": from_, "size": size,
            "q": 'taskEndpointsEventOrganizationEndpointPatchPatchPackages.organizationEndpointPatchPatchPackagesStatusMessage=="Pending Reboot"',
            "includeFields": "taskEndpointsEventEndpoint.endpointName;taskEndpointsEventOrganizationEndpointPatchPatchPackages.organizationEndpointPatchPatchPackagesPatchPackage.patchPackageFileName",
        },
    )


# ---------------------------------------------------------------------------
# Events / Activity
# ---------------------------------------------------------------------------

_VALID_TASK_STATUSES = {"Succeeded", "Failed", "Notice"}


@read_tool
def list_event_log(from_: int = 0, size: int = 500, since_epoch_ns: int = 0) -> str:
    """List the full event log, sorted oldest-first. Use since_epoch_ns (nanoseconds) to pull incremental events."""
    q = f"analyticsEventCreatedAtNano>{since_epoch_ns}" if since_epoch_ns else ""
    params: dict = {"from": from_, "size": size, "sort": "+analyticsEventCreatedAtNano", "returnCount": "true"}
    if q:
        params["q"] = q
    return _get("/incidentEvent/filter", params=params)


@read_tool
def list_cve_events(from_: int = 0, size: int = 500, since_epoch_ns: int = 0) -> str:
    """List CVE detection events (new vulnerabilities appearing/disappearing), sorted oldest-first."""
    params: dict = {
        "from": from_, "size": size,
        "sort": "+analyticsEventCreatedAtNano",
        "q": "incidentEventIncidentEventType==DetectedVulnerability",
    }
    if since_epoch_ns:
        params["q"] += f";analyticsEventCreatedAtNano>{since_epoch_ns}"
    return _get("/incidentEvent/filter", params=params)


@read_tool
def list_task_events(from_: int = 0, size: int = 100) -> str:
    """List the task activity log (patch/script executions across all assets)."""
    return _get("/taskEndpointsEvent/filter", params={"from": from_, "size": size})


@read_tool
def list_completed_tasks(status: str = "Succeeded", from_: int = 0, size: int = 100) -> str:
    """List completed patch tasks by status. status must be one of: Succeeded, Failed, Notice."""
    if status not in _VALID_TASK_STATUSES:
        return f'ERROR: status must be one of {sorted(_VALID_TASK_STATUSES)}, got "{status}"'
    return _get(
        "/taskEndpointsEvent/filter",
        params={
            "from": from_, "size": size,
            "q": f'taskEndpointsEventOrganizationEndpointPatchPatchPackages.organizationEndpointPatchPatchPackagesActionStatus.actionStatusName=="{_rsql(status)}"',
        },
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

@read_tool
def list_top_10(type: str = "assets") -> str:
    """List top 10 most vulnerable assets or CVEs. type must be 'assets' or 'cves'."""
    if type == "assets":
        return _get(
            "/aggregation/searchGroup",
            params={"objectName": "OrganizationEndpointVulnerabilities", "group": "endpointId", "from": 0, "size": 10, "sort": "-aggregationCount", "assetCount": "true"},
        )
    elif type == "cves":
        return _get(
            "/aggregation/searchGroup",
            params={"objectName": "OrganizationEndpointVulnerabilities", "group": "vulnerabilityId", "from": 0, "size": 10, "sort": "-aggregationCount", "assetCount": "true"},
        )
    return f'ERROR: type must be "assets" or "cves", got "{type}"'


_COUNT_PATHS = {
    "vulnerabilities": "/vulnerability/count",
    "events": "/incidentEvent/count",
    "task_events": "/taskEvent/count",
    "task_endpoint_events": "/taskEndpointsEvent/count",
}


@read_tool
def count_objects(
    object_type: Literal["vulnerabilities", "events", "task_events", "task_endpoint_events"],
    q: str = "",
) -> str:
    """Count objects without listing them - much faster than paging for totals. object_type:
    vulnerabilities (the vRx CVE catalog, not just CVEs on your assets), events (the event log),
    task_events, or task_endpoint_events (per-endpoint task results).
    q is an optional RSQL filter, e.g. vulnerabilitySensitivityLevel.sensitivityLevelName=="Critical".
    The total is in serverResponseCount."""
    path = _COUNT_PATHS.get(object_type)
    if path is None:
        return f'ERROR: object_type must be one of {sorted(_COUNT_PATHS)}, got "{object_type}"'
    return _get(path, params={"q": q})


@read_tool
def group_by(object_name: str, group: str, q: str = "", from_: int = 0, size: int = 25, sort: str = "-aggregationCount", include_original_doc: bool = False) -> str:
    """Group and count any object type by a field - a general version of list_top_10. object_name
    is the object to aggregate, e.g. OrganizationEndpointVulnerabilities; group is the field to
    group by, e.g. vulnerabilityId or endpointId. q is an optional RSQL filter; sort defaults to
    the largest groups first; include_original_doc adds a sample document per group."""
    params: dict = {"objectName": object_name, "group": group, "from": from_, "size": size, "sort": sort, "assetCount": "true"}
    if q:
        params["q"] = q
    if include_original_doc:
        params["includeOriginalDoc"] = "true"
    return _get("/aggregation/searchGroup", params=params)


@read_tool
def list_endpoint_tags(from_: int = 0, size: int = 100) -> str:
    """List all endpoint tags (xtags) defined in the tenant."""
    return _get("/endpointAttributes/search", params={"from": from_, "size": size, "includeFields": "endpointAttributesXtags"})


# ---------------------------------------------------------------------------
# Automations
# ---------------------------------------------------------------------------

@read_tool
def list_automations(from_: int = 0, size: int = 100) -> str:
    """List all automations configured in the tenant."""
    return _get("/v1/automations", params={"from": from_, "size": size})


@read_tool
def get_automation(automation_id: str) -> str:
    """Get full details for a specific automation by its ID."""
    return _get(f"/v1/automations/{_seg(automation_id)}")


@write_tool
def create_automation(payload: dict) -> str:
    """Create a new automation. Pass the full automation config as a dict (see vRx API docs for schema)."""
    return _post("/v1/automations", body=payload)


@destructive_tool
def update_automation(automation_id: str, payload: dict) -> str:
    """Update an existing automation by ID. Pass the full updated config as a dict."""
    return _put(f"/v1/automations/{_seg(automation_id)}", body=payload)


@write_tool
def set_automation_state(automation_id: str, enabled: bool) -> str:
    """Enable or disable an automation. enabled=True activates it, enabled=False deactivates it."""
    return _put(f"/v1/automations/{_seg(automation_id)}/updateState", body={"enabled": enabled})


@read_tool
def list_script_templates(from_: int = 0, size: int = 100) -> str:
    """List all script templates available in the tenant."""
    return _get("/scriptTemplate/search", params={"from": from_, "size": size})


@read_tool
def list_task_types() -> str:
    """List all available task type identifiers (e.g. patch, script, reboot)."""
    return _get("/taskEndpointsEvent/taskTypes")


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@read_tool
def list_users(from_: int = 0, size: int = 100) -> str:
    """List all users in the tenant."""
    return _get("/user/search", params={"from": from_, "size": size})


@read_tool
def list_user_invitations(from_: int = 0, size: int = 100) -> str:
    """List all pending user invitations."""
    return _get("/userInvitation/search", params={"from": from_, "size": size})


@write_tool
def invite_user(email: str, role: str) -> str:
    """Send an invitation to a new user. role is the vRx role name (e.g. 'admin', 'viewer')."""
    return _put("/userInvitation/insert", body={"userInvitationEmail": email, "userInvitationRole": role})


@write_tool
def resend_invitation(invitation_id: str) -> str:
    """Resend an existing invitation email by its userInvitationId."""
    return _post("/userInvitation/resend", body={"userInvitationId": invitation_id})


@destructive_tool
def delete_invitation(invitation_id: str) -> str:
    """Cancel and delete a pending invitation by its userInvitationId."""
    return _delete("/userInvitation/delete", params={"id": invitation_id})


# ---------------------------------------------------------------------------
# Patch Catalog
# ---------------------------------------------------------------------------

@read_tool
def list_patch_catalog(from_: int = 0, size: int = 100, software_type: Literal["APP", "OS"] = "APP") -> str:
    """List the global patch catalog — all patches known to vRx, with metadata. software_type
    is APP (third-party application patches) or OS (operating-system patches)."""
    return _get("/patchManagement/patch", params={"from": from_, "size": size, "softwareType": software_type})


@read_tool
def get_patch_cve_info(patch_id: str, source: Literal["VICARIUS", "XPATCH"] = "VICARIUS") -> str:
    """Get the CVEs addressed by a specific patch ID. source is VICARIUS for regular catalog
    patches or XPATCH for Vicarius xPatch (patchless protection) entries."""
    return _get(f"/patchManagement/patch/{_seg(patch_id)}/cveInfo", params={"source": source})


@read_tool
def list_endpoint_patch_packages(from_: int = 0, size: int = 100, asset_name: str = "") -> str:
    """List patch packages installed or pending on endpoints. Optionally filter by asset name."""
    params: dict = {"from": from_, "size": size}
    if asset_name:
        params["q"] = f'endpointName=="{_rsql(asset_name)}"'
    return _get("/organizationEndpointPatchPatchPackages/filter", params=params)


# ---------------------------------------------------------------------------
# Software Catalog
# ---------------------------------------------------------------------------

@read_tool
def list_publisher_products(from_: int = 0, size: int = 100, q: str = "") -> str:
    """List all software publishers and products detected across the tenant."""
    params: dict = {"from": from_, "size": size}
    if q:
        params["q"] = q
    return _get("/organizationPublisherProducts/search", params=params)


@read_tool
def list_endpoint_vulnerabilities(from_: int = 0, size: int = 100, asset_name: str = "") -> str:
    """Detailed per-endpoint vulnerability filter. More granular than get_asset_vulnerabilities."""
    params: dict = {"from": from_, "size": size}
    if asset_name:
        params["q"] = f'endpointName=="{_rsql(asset_name)}"'
    return _get("/endpointVulnerability/filter", params=params)


USAGE = """\
vicarius-mcp - MCP server for the Vicarius vRx External Data API (stdio transport).

This command is launched by your MCP client (Claude Code, Codex, ...), not run by hand.

Options:
  --version   Print the version and exit
  --help      Show this message and exit

Environment:
  VICARIUS_DASHBOARD   Dashboard subdomain, e.g. "acme" for acme.vicarius.cloud (required)
  VICARIUS_API_KEY     API key for that dashboard (required)
  VICARIUS_READ_ONLY   Set to "true" to expose read-only tools only
"""


# Applied at import so read-only mode holds however the server is launched.
enforce_read_only()


def main() -> None:
    args = sys.argv[1:]
    if "--version" in args:
        print(f"vicarius-mcp {__version__}")
        return
    if "--help" in args or "-h" in args:
        print(USAGE)
        return
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
