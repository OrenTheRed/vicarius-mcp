from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg

# ---------------------------------------------------------------------------
# Scan Reports (evidence files)
# ---------------------------------------------------------------------------


@read_tool
def list_scan_reports(params: dict | None = None, tenant: str | None = None) -> str:
    """List scan-execution evidence files/reports. params supports siteId, scanRunId, entityId,
    type, name, fileName, assetId, sort, sortDirection, searchAfter, size, fields."""
    return _get("/evidence-files", tenant=tenant, params=params)


@read_tool
def download_scan_report(evidence_file_id: str, tenant: str | None = None) -> str:
    """Download a scan report/evidence file by its id. Returns JSON metadata if the response is
    JSON (e.g. a presigned URL); otherwise returns content-type/size only (binary not inlined)."""
    return _get(f"/evidence-files/{seg(evidence_file_id)}/download", tenant=tenant)


# ---------------------------------------------------------------------------
# Reports (scheduled/custom)
# ---------------------------------------------------------------------------


@read_tool
def list_reports(params: dict | None = None, tenant: str | None = None) -> str:
    """List custom/scheduled reports. params supports siteId, ownerUserId, name, fullTextSearch,
    enabled, scheduledOnly, sort, sortDirection, searchAfter, size, fields."""
    return _get("/reports", tenant=tenant, params=params)


@write_tool
def create_report(name: str, spec_json: dict, tenant: str | None = None) -> str:
    """Create a custom report. spec_json defines what the report includes (filters, columns, etc.)."""
    return _post("/reports", tenant=tenant, body={"name": name, "specJson": spec_json})


@destructive_tool
def delete_report(report_id: str, tenant: str | None = None) -> str:
    """Delete a report by its id."""
    return _delete(f"/reports/{seg(report_id)}", tenant=tenant)


@write_tool
def generate_report(prompt: str, name: str | None = None, tenant: str | None = None) -> str:
    """Generate a report from a natural-language prompt describing what it should contain."""
    body = {"prompt": prompt}
    if name:
        body["name"] = name
    return _post("/reports/generate", tenant=tenant, body=body)


@read_tool
def list_report_executions(size: int | None = None, pagination_token: str | None = None, report_id: str | None = None, tenant: str | None = None) -> str:
    """List report executions (runs) across all reports, or only those of report_id."""
    params = {}
    if size is not None:
        params["size"] = size
    if pagination_token:
        params["paginationToken"] = pagination_token
    path = f"/reports/{seg(report_id)}/executions" if report_id else "/reports/executions"
    return _get(path, tenant=tenant, params=params or None)


@read_tool
def get_report_execution(report_id: str, execution_id: str, download_url: bool = False, tenant: str | None = None) -> str:
    """Get one run of a report: its status and timing. With download_url=True, returns a
    temporary link to download the generated file instead."""
    path = f"/reports/{seg(report_id)}/executions/{seg(execution_id)}"
    return _get(f"{path}/download" if download_url else path, tenant=tenant)


@read_tool
def preview_report(report_id: str, tenant: str | None = None) -> str:
    """Preview a report's current content as CSV text, without running or exporting it. Large
    previews are truncated."""
    return _get(f"/reports/{seg(report_id)}/preview", tenant=tenant, params={"format": "CSV"})


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------


@read_tool
def list_audit_logs(params: dict | None = None, tenant: str | None = None) -> str:
    """List the organization's audit log. params supports actorIdIn, actionIn, objectTypeIn,
    fullTextSearch, includeSystemEvents, createdAtFrom, createdAtTo, sort, sortDirection,
    searchAfter, size, fields."""
    return _get("/settings/auditLogs", tenant=tenant, params=params)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


@read_tool
def list_filter_values(collection: str, search_query: str | None = None, size: int | None = None, keys: list | None = None, tenant: str | None = None) -> str:
    """Enumerate the selectable values for a filter dropdown/collection (the same values the
    dashboard's filter UI shows), e.g. collection="severity" or "operatingSystemFamily"."""
    params = {}
    if search_query:
        params["searchQuery"] = search_query
    if size is not None:
        params["size"] = size
    if keys:
        params["keys"] = keys
    return _get(f"/filters/{seg(collection)}/values", tenant=tenant, params=params or None)


# ---------------------------------------------------------------------------
# Deployment Settings
# ---------------------------------------------------------------------------


@read_tool
def get_deployment_settings(tenant: str | None = None) -> str:
    """Get the organization's rollout/deployment settings (maintenance window, batch size, timeouts)."""
    return _get("/settings/deployment", tenant=tenant)


@destructive_tool
def update_deployment_settings(payload: dict, tenant: str | None = None) -> str:
    """Update the organization's deployment settings. payload: maintenanceWindow,
    batchSizePerHour, actionTimeoutMinutes."""
    return _put("/settings/deployment", tenant=tenant, body=payload)
