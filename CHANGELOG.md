# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.2.0] - 2026-10-04

### Added: v2 (`vicarius-v2-mcp`)
- Optional `assess_finding_urgency` tool. It asks TypeSafe's Jev model how urgent one finding is
  on its own asset (domain controller or non-production name, and vRx's exploit tags). vRx's own
  numbers are returned unchanged. vRx does not report whether software is running, so that fact
  is not judged. It is off by default and absent from the tool list until you set
  `VICARIUS_V2_JEV=true` and `TYPESAFE_API_KEY`.
- `VICARIUS_V2_JEV_PRIVACY` lets the operator choose what is sent: `full` (default) sends machine
  names, IP addresses, CVE ids, asset groups and software names. `minimal` hides all of them.
  `preview=true` shows the payload without sending it.
- A guard in code caps Jev's disposition at `STANDARD` when vRx's exploit evidence is weak (no
  CISA KEV listing, no exploit tags, low or medium EPSS). The output shows when it applied and
  Jev's original answer.

### Changed
- Added a `.gitleaks.toml` with a rule for Vicarius API keys. The CI secret scan uses it. `.omc/` is now ignored.

## [1.1.1] - 2026-10-01

Security hardening from a repository audit. No tools were added or removed.

### Security
- v1 now replaces secret-named fields (`password`, `privateKey`, `passphrase`, ...) with
  `<redacted>` in responses, as v2 already did.
- v1 and v2 error replies are now capped at 2,000 characters. They have secret-named fields and
  the configured API key removed.
- GitHub Actions are now pinned to commit SHAs. The release workflow runs the tests first, and
  only its release job has write access.

## [1.1.0] - 2026-10-01

This release adds 19 tools (15 in v2, 4 in v1) and fixes eight v1 tools that returned errors
or incomplete results. All new v2 tools are read-only, so they stay available in read-only
mode. The new read tools and the fixes were verified against a live tenant wherever it had
data to return.

### Added: v2 (`vicarius-v2-mcp`, 100 → 115 tools)
- `get_resource`: get any of 18 object types by ID (asset, software and patch groups,
  credentials, named targets, patch and script policies, site agents, scanner configurations,
  private and public scripts, reports, exclusion rules, scan reports, audit-log entries,
  discovery findings, software installations).
- `get_distribution`: 15 site-level breakdowns and rankings, including assets by OS, source,
  status, type and risk; findings by severity, status and type; recently closed findings;
  top software by findings and by installs; top patches; patch summary; patch success rate.
- `count_policies`: count policies with the same filters as `list_policies`.
- `get_risk_score_history`: how an asset's or a finding's risk score changed, and why.
- `preview_group_expression`: show what a dynamic asset, software or patch group expression
  matches before you create or change the group.
- `get_exclusion_rule_impact`: how many findings an exclusion rule hides, which ones, and
  which assets it affects.
- `search_compliance`, `get_compliance_benchmark_results`, `list_compliance_rules`,
  `get_compliance_rule`: CIS compliance results by benchmark, asset and scan, drill-down into
  rule groups and rules, affected assets, and rule documentation.
- `get_policy_run_details`: task status counts, the per-asset summary of one run, and a
  task's console output.
- `get_report_execution` (status or download link) and `preview_report` (CSV preview).
- **Experimental**, built on endpoints the vRx web app uses but the published API doesn't
  document:
  - `get_findings_trends`: findings created, remediated, open backlog and MTTR over time.
  - `get_dashboard_summary`: headline asset, software and finding totals.

### Added: v1 (`vicarius-mcp`, 38 → 42 tools)
- `update_asset_group` and `delete_asset_group`. Previously v1 could create a group but not
  change or remove it. Updates fetch the current group and merge your changes, so unchanged
  fields keep their values.
- `count_objects`: fast totals for vulnerabilities, events, task events and per-endpoint task
  events, with an optional RSQL filter.
- `group_by`: group and count any object type by any field (a general `list_top_10`).

### Changed
- v2: `list_policy_runs` takes `group_by="run"` to return one row per run (experimental).
- v2: `list_report_executions` takes `report_id` to list the runs of a single report.
- v2: text responses (CSV previews, task output) are returned inline instead of being
  discarded, capped at 20,000 characters.
- v1: `list_patch_catalog` takes `software_type` (`APP` or `OS`), and `get_patch_cve_info`
  takes `source` (`VICARIUS` or `XPATCH`). Both are required by the API.

### Fixed: v1
- `get_asset_attributes`, `get_asset_ip_addresses`, `get_cve_info`, `list_top_10` and
  `list_asset_group_members` always failed with `query parameter 'from' is either empty or
  not a natural number`.
- `get_asset_attributes` and `get_asset_ip_addresses` returned only the first of an asset's
  attribute records.
- The `asset_name` filter of `get_asset_vulnerabilities` matched nothing; it now filters on the
  nested endpoint name.
- `list_patch_catalog` and `get_patch_cve_info` failed because required parameters were
  missing.

### Security
- v2: any secret-named field in a response (`password`, `privateKey`, `passphrase`,
  `accessKey`, `organizationSecretKey`, ...) is replaced with `<redacted>` before it reaches the
  agent. This is defense in depth; Vicarius already blanks these fields.
- The undocumented `/me/organization` endpoint was deliberately left out, because its response
  includes the organization's secret key.

## [1.0.0] - 2026-10-01

First public release of both servers.

### Added
- `vicarius-v2-mcp`: 100 tools for the vRx v2 Customer API, with multi-tenant support.
- `vicarius-mcp`: 38 tools for the vRx External Data API.
- Read-only mode (`VICARIUS_READ_ONLY=true`), which removes all state-changing tools.
- MCP tool annotations (`readOnlyHint`, `destructiveHint`) on every tool.
- `--version` and `--help` flags.
- Installation with `uv tool install` on macOS, Linux and Windows.

### Security
- IDs are percent-encoded in URL paths, which prevents path traversal to other endpoints.
- v1: values interpolated into RSQL filters are escaped.
- v1: `VICARIUS_DASHBOARD` is validated as a subdomain. v2: tenant `host` is validated as a bare
  hostname, and requests always use HTTPS.
- v2: the tenants file is written atomically with owner-only permissions.
- v2: `add_configured_tenant` refuses to overwrite an existing tenant without `overwrite=True`,
  and refuses non-`vicarius.cloud` hosts unless `VICARIUS_V2_ALLOW_CUSTOM_HOSTS=true` is set.
- Empty, `.` and `..` IDs are rejected before they reach a URL path.
- FastMCP's startup update check (a request to pypi.org) is turned off.
- Read-only mode is applied when the module loads, whatever launches the server.

### Fixed
- v1: `list_event_log` / `list_cve_events` sent a double-encoded sort parameter (`%252B`).
- v2: tenants files saved with a UTF-8 byte-order mark (common with Windows editors) now load.
- v2: optional tool arguments accept `null`, which some MCP clients send.
- v2: `add_configured_tenant` no longer hides tenants defined in `VICARIUS_V2_TENANTS`.
- v1: empty (e.g. `204 No Content`) responses to POST/PUT are no longer reported as errors.

[Unreleased]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/OrenTheRed/vicarius-mcp/releases/tag/v1.1.0
[1.0.0]: https://github.com/OrenTheRed/vicarius-mcp/releases/tag/v1.0.0
