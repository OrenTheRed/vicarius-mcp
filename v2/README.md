# vicarius-v2-mcp (v2): vRx v2 Customer API

MCP server for the **Vicarius vRx v2 Customer API** (`https://vicarius.cloud/api`). It gives an AI
agent **115 tools** (68 read-only, 21 write, 26 destructive) covering sites, assets, software,
vulnerability findings, scan/patch/script policies, CIS compliance, reports, credentials, users
and API keys. One running server can manage **any number of tenants**.

> Installation and client setup (Claude Code, Codex; macOS, Linux, Windows) are covered in the
> [main README](../README.md). This page is the configuration and tool reference.

## Configuration

### The tenants file

A *tenant* is a local name you choose, mapped to one Vicarius API key. Tenants live in a JSON file
that the server re-reads on every tool call, so edits take effect without a restart.

| OS | Default location |
|---|---|
| macOS / Linux | `~/.config/vicarius-v2-mcp/tenants.json` |
| Windows | `%USERPROFILE%\.config\vicarius-v2-mcp\tenants.json` |

```json
{
  "acme":   { "api_key": "<api-key-for-acme>" },
  "globex": { "api_key": "<api-key-for-globex>", "host": "vicarius.cloud" }
}
```

- `api_key` (required): create one in vRx under **Account Settings → API Tokens**. Each key is
  scoped to a single organization.
- `host` (optional): defaults to `vicarius.cloud`. Change it only if Vicarius has given you a
  different API host. It must be a bare hostname (no path or query), and requests always use HTTPS.

A template is provided in [`tenants.example.json`](tenants.example.json).

### Choosing a tenant

Every tool accepts an optional `tenant` argument. If it's omitted:

1. `VICARIUS_V2_DEFAULT_TENANT` is used, if set.
2. Otherwise, if exactly one tenant is configured, that one is used.
3. Otherwise the tool returns an error listing the configured tenant names.

In practice you just say *"show critical findings for globex"* and the agent passes
`tenant="globex"`.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `VICARIUS_V2_TENANTS_FILE` | see table above | Path to the tenants file. |
| `VICARIUS_V2_TENANTS` | | Tenants as an inline JSON string, same shape as the file. Only used when the tenants file does not exist. |
| `VICARIUS_V2_DEFAULT_TENANT` | | Tenant used when a tool call omits `tenant`. |
| `VICARIUS_READ_ONLY` | `false` | Set to `true` to expose only the 68 read-only tools. |
| `VICARIUS_V2_ALLOW_CUSTOM_HOSTS` | `false` | Allow `add_configured_tenant` to save a host outside `vicarius.cloud`. Hosts you put in the tenants file yourself are always allowed. |

### Managing tenants from the agent

`add_configured_tenant` and `remove_configured_tenant` let the agent edit the tenants file for
you. This is convenient, but **an API key you type into the chat is sent to your AI provider and
stays in your conversation history.** Editing the file directly keeps the key on your machine, so
it's the recommended approach. Both tools are disabled in read-only mode.

To limit what a manipulated agent could do, `add_configured_tenant`:

- won't replace an existing tenant unless it's called with `overwrite=True`,
- only accepts `vicarius.cloud` hosts unless `VICARIUS_V2_ALLOW_CUSTOM_HOSTS=true` is set, and
- refuses to run when your tenants come from the `VICARIUS_V2_TENANTS` environment variable,
  because creating a file would hide them.

When the server writes the tenants file, it writes atomically and creates the file with
owner-only permissions (`0600`) on macOS and Linux. On Windows, the file inherits the ACLs of your
user profile folder.

### Experimental tools

`get_findings_trends`, `get_dashboard_summary` and `list_policy_runs(group_by="run")` use
endpoints that the vRx web app relies on but that aren't part of the published Customer API.
They're marked **[Experimental]** in their descriptions. Vicarius may change these endpoints
without notice, so if one starts failing, the rest of the server is unaffected.

### Pagination and filters

List/search tools take a `params` dict (query string) and, for POST-based searches, a `filters`
dict (request body). Both match the Vicarius API's own parameter names, so anything the API
supports, the tool supports. Results paginate with `size` and `searchAfter`.

## Tools

**read**: only reads data. **write**: creates or changes data. **destructive**: deletes,
revokes or overwrites existing data. Every write and destructive tool is hidden when
`VICARIUS_READ_ONLY=true`.

### Tenants & Organizations

| Tool | Access | Description |
|---|---|---|
| `list_configured_tenants` | read | List the tenant names configured locally (in the tenants file or VICARIUS_V2_TENANTS). |
| `add_configured_tenant` | **destructive** | Add a locally configured tenant: a name mapped to an API key + host. |
| `remove_configured_tenant` | **destructive** | Remove a locally configured tenant by name. |
| `list_organizations` | read | List every Vicarius organization (tenant) visible to the account behind the given tenant's API key. |
| `list_organization_sites` | read | List the sites visible to the current user within a specific organization by its org_id (UUID). |

### API Keys

| Tool | Access | Description |
|---|---|---|
| `list_api_keys` | read | List API keys for the tenant's organization. |
| `create_api_key` | write | Create a new API key. |
| `get_api_key` | read | Get metadata for a single API key by its id (never returns the secret). |
| `delete_api_key` | **destructive** | Revoke and delete an API key by its id. |

### Organization Members

| Tool | Access | Description |
|---|---|---|
| `list_org_members` | read | List all members (users) of the tenant's organization. |
| `invite_members` | write | Invite one or more users by email to join the organization. |
| `remove_org_member` | **destructive** | Remove a member from the organization by their userId. |
| `resend_member_invitation` | write | Resend the pending invitation email for a not-yet-active member by their userId. |

### User Groups

| Tool | Access | Description |
|---|---|---|
| `list_user_groups` | read | List all user groups defined in the organization. |
| `create_user_group` | write | Create a new user group with the given display name. |
| `list_user_group_members` | read | List the members of a user group by its groupId. |
| `batch_add_group_members` | write | Add one or more users (by userId) to a user group. |

### Site Permissions

| Tool | Access | Description |
|---|---|---|
| `get_user_site_permissions` | read | List every site-level permission grant (WRITER/ADMIN/VIEWER) for a user by their userId. |
| `update_user_site_permission` | **destructive** | Grant, change, or revoke a user's permission on a site. |

### Sites

| Tool | Access | Description |
|---|---|---|
| `list_sites` | read | List/search sites. |
| `create_site` | write | Create a new site. |
| `get_site` | read | Get a single site by its id (UUID). |
| `update_site` | **destructive** | Update a site by id. |
| `delete_site` | **destructive** | Delete a site by its id (UUID). |

### Site Agents

| Tool | Access | Description |
|---|---|---|
| `list_site_agents` | read | List/search site agents (the assets that perform scanning for a site). |
| `create_site_agent` | write | Register an asset as a site agent. |

### Named Targets

| Tool | Access | Description |
|---|---|---|
| `list_named_targets` | read | List/search named targets (reusable sets of network addresses). |
| `create_named_target` | write | Create a named target. |

### Credentials

| Tool | Access | Description |
|---|---|---|
| `list_credentials` | read | List/search stored scan credentials (metadata only, secrets never returned). |
| `create_credential` | write | Create a scan credential. |

### Scanner Configurations

| Tool | Access | Description |
|---|---|---|
| `list_scanner_configurations` | read | List/search scanner configurations. |
| `create_scanner_configuration` | write | Create a scanner configuration. |

### Assets

| Tool | Access | Description |
|---|---|---|
| `search_assets` | read | Search assets. |
| `get_asset` | read | Get full details for a single asset by its assetId. |
| `get_asset_risk_distribution` | read | Get asset counts bucketed by risk level for a site. |

### Asset Groups

| Tool | Access | Description |
|---|---|---|
| `list_asset_groups` | read | List/search asset groups (static or dynamic expression-based collections of assets). |
| `create_asset_group` | write | Create an asset group. |
| `update_asset_group` | **destructive** | Update an asset group by id. |
| `delete_asset_group` | **destructive** | Delete an asset group by its id. |

### Software

| Tool | Access | Description |
|---|---|---|
| `search_software` | read | Search the software inventory. |
| `get_software` | read | Get details for a single software product by its productId. |

### Software Groups

| Tool | Access | Description |
|---|---|---|
| `list_software_groups` | read | List/search software groups. |
| `create_software_group` | write | Create a software group. |
| `update_software_group` | **destructive** | Update a software group by id. |
| `delete_software_group` | **destructive** | Delete a software group by its id. |

### Vulnerability Findings

| Tool | Access | Description |
|---|---|---|
| `search_findings` | read | Search vulnerability findings. |
| `get_finding` | read | Get full details for a single finding by its id. |
| `findings_grouped_by_vulnerability` | read | Search findings grouped by the underlying vulnerability/CVE, deduping across assets. |
| `findings_severity_distribution` | read | Get active finding counts bucketed by severity for a site. |

### Vulnerability Exclusion Rules

| Tool | Access | Description |
|---|---|---|
| `create_vulnerability_exclusion_rule` | write | Create a vulnerability exclusion (risk-acceptance) rule. |
| `get_vulnerability_exclusion_rule` | read | Get a vulnerability exclusion rule by its id. |
| `delete_vulnerability_exclusion_rule` | **destructive** | Delete a vulnerability exclusion rule by its id. |
| `set_vulnerability_exclusion_rule_state` | write | Enable or disable a vulnerability exclusion rule. |

### Exclusion Rules (all types)

| Tool | Access | Description |
|---|---|---|
| `list_exclusion_rules` | read | List all exclusion rules (any type). |
| `delete_exclusion_rule` | **destructive** | Delete any exclusion rule by its id, regardless of type. |

### Scan Profiles

| Tool | Access | Description |
|---|---|---|
| `search_scan_profiles` | read | Browse the catalog of scan profiles (what kind of scan to run - discovery, full vulnerability, PCI, HIPAA, CIS, etc). |
| `get_scan_profile` | read | Get full details for a single scan profile by its id. |

### Scan Policies

| Tool | Access | Description |
|---|---|---|
| `create_scan_policy` | write | Create a scan policy. |
| `get_scan_policy` | read | Get a scan policy by its id. |
| `update_scan_policy` | **destructive** | Update a scan policy by id. |
| `delete_scan_policy` | **destructive** | Delete a scan policy by its id. |
| `set_scan_policy_state` | **destructive** | Enable/disable a scan policy or change its status. |

### Patch Policies

| Tool | Access | Description |
|---|---|---|
| `create_patch_policy` | write | Create a patch policy. |
| `update_patch_policy` | **destructive** | Update a patch policy by id. |
| `set_patch_policy_state` | **destructive** | Enable/disable a patch policy or change its status. |

### Script Policies

| Tool | Access | Description |
|---|---|---|
| `create_script_policy` | write | Create a script policy. |
| `update_script_policy` | **destructive** | Update a script policy by id. |
| `set_script_policy_state` | **destructive** | Enable/disable a script policy or change its status. |

### Policies (cross-type) & Policy Logs

| Tool | Access | Description |
|---|---|---|
| `list_policies` | read | List all policies (scan/patch/script) with unified filtering. |
| `list_upcoming_policy_runs` | read | List policies with an upcoming scheduled run. |
| `list_policy_runs` | read | List policy executions. |
| `list_policy_run_tasks` | read | List individual policy run tasks (flat, one row per asset/task). |
| `get_policy_run_details` | read | Drill into a policy's runs. |

### Patch Catalog

| Tool | Access | Description |
|---|---|---|
| `search_patches` | read | Search the patch catalog (patches applicable to your assets). |
| `get_patch_summary` | read | Get patch status summary/distribution for a site. |

### Patch Groups

| Tool | Access | Description |
|---|---|---|
| `list_patch_groups` | read | List/search patch groups. |
| `create_patch_group` | write | Create a patch group. |
| `update_patch_group` | **destructive** | Update a patch group by id. |
| `delete_patch_group` | **destructive** | Delete a patch group by its id. |

### Available Patches

| Tool | Access | Description |
|---|---|---|
| `search_available_patches` | read | Search patches available/pending to be installed (as opposed to the full catalog). |

### Reboot Profiles

| Tool | Access | Description |
|---|---|---|
| `get_reboot_profile` | read | Get the organization's automatic-reboot settings. |
| `update_reboot_profile` | **destructive** | Update the organization's automatic-reboot settings. |

### Asset Inactivity Settings

| Tool | Access | Description |
|---|---|---|
| `get_asset_inactivity_settings` | read | Get the organization's asset auto-removal (inactivity) settings. |
| `update_asset_inactivity_settings` | **destructive** | Set the number of days of inactivity after which an asset is automatically removed. |

### CIS Benchmarks

| Tool | Access | Description |
|---|---|---|
| `get_cis_benchmark_catalog` | read | Browse the catalog of CIS compliance benchmarks. |

### Compliance

| Tool | Access | Description |
|---|---|---|
| `get_compliance_checks` | read | List CIS compliance checks (rules) for a benchmark. |
| `get_compliance_scan_summary` | read | Get the pass/fail summary for a single CIS compliance scan run by its scanRunId. |

### Compliance Results

| Tool | Access | Description |
|---|---|---|
| `search_compliance` | read | Search CIS compliance results. |
| `get_compliance_benchmark_results` | read | Get compliance results for one CIS benchmark. |
| `list_compliance_rules` | read | Browse a CIS benchmark's rules. |
| `get_compliance_rule` | read | Drill into one CIS rule. |

### Scan Reports (evidence files)

| Tool | Access | Description |
|---|---|---|
| `list_scan_reports` | read | List scan-execution evidence files/reports. |
| `download_scan_report` | read | Download a scan report/evidence file by its id. |

### Reports (scheduled/custom)

| Tool | Access | Description |
|---|---|---|
| `list_reports` | read | List custom/scheduled reports. |
| `create_report` | write | Create a custom report. |
| `delete_report` | **destructive** | Delete a report by its id. |
| `generate_report` | write | Generate a report from a natural-language prompt describing what it should contain. |
| `list_report_executions` | read | List report executions (runs) across all reports, or only those of report_id. |
| `get_report_execution` | read | Get one run of a report: its status and timing. |
| `preview_report` | read | Preview a report's current content as CSV text, without running or exporting it. |

### Audit Logs

| Tool | Access | Description |
|---|---|---|
| `list_audit_logs` | read | List the organization's audit log. |

### Filters

| Tool | Access | Description |
|---|---|---|
| `list_filter_values` | read | Enumerate the selectable values for a filter dropdown/collection (the same values the dashboard's filter UI shows), e.g. collection="severity" or "operatingSystemFamily". |

### Deployment Settings

| Tool | Access | Description |
|---|---|---|
| `get_deployment_settings` | read | Get the organization's rollout/deployment settings (maintenance window, batch size, timeouts). |
| `update_deployment_settings` | **destructive** | Update the organization's deployment settings. |

### Private Scripts

| Tool | Access | Description |
|---|---|---|
| `search_private_scripts` | read | Search the organization's private (custom) scripts. |
| `create_private_script` | write | Create a private script. |

### Public Scripts

| Tool | Access | Description |
|---|---|---|
| `search_public_scripts` | read | Search Vicarius's public script library. |

### Get by ID

| Tool | Access | Description |
|---|---|---|
| `get_resource` | read | Get one object by its id. |

### Previews

| Tool | Access | Description |
|---|---|---|
| `preview_group_expression` | read | Show which assets, software or patches a dynamic-group expression would match, without creating anything. |
| `get_exclusion_rule_impact` | read | Show what an exclusion (risk-acceptance) rule hides. |

### Distributions & Rankings

| Tool | Access | Description |
|---|---|---|
| `get_distribution` | read | Get a summary breakdown for a site, the numbers behind the dashboard charts. |
| `count_policies` | read | Count policies without listing them. |
| `get_risk_score_history` | read | Get how the risk score of an asset or a finding changed over time, with the event behind each change. |

### Trends & KPIs (experimental)

| Tool | Access | Description |
|---|---|---|
| `get_findings_trends` | read | [Experimental: undocumented endpoint] Get finding trends over time: findings created, findings remediated, open backlog, and mean time to remediate (mttrDays), as time series. |
| `get_dashboard_summary` | read | [Experimental: undocumented endpoints] Get the headline numbers in one call: total, active and inactive assets; total software; total findings and active findings per severity. |

## Development

```bash
cd v2
uv sync --extra dev
uv run pytest
```

All HTTP calls are mocked with [respx](https://lundberg.github.io/respx/), so the test suite needs
no Vicarius credentials or network access. Tests never touch your real tenants file.
