# vicarius-mcp (v1): vRx External Data API

MCP server for the **Vicarius vRx External Data API**, the API served from your own dashboard
subdomain (`https://<dashboard>.vicarius.cloud/vicarius-external-data-api`). It gives an AI agent
**38 tools** (30 read-only, 5 write, 3 destructive) covering assets, CVEs, patches, events, automations and users.

> Installation and client setup (Claude Code, Codex; macOS, Linux, Windows) are covered in the
> [main README](../README.md). This page is the configuration and tool reference.

## Configuration

The server is configured entirely through environment variables, which your MCP client passes in
when it launches the server.

| Variable | Required | Description |
|---|---|---|
| `VICARIUS_DASHBOARD` | Yes | Your dashboard subdomain, e.g. `acme` for `https://acme.vicarius.cloud`. A full URL such as `https://acme.vicarius.cloud/` is also accepted. |
| `VICARIUS_API_KEY` | Yes | API key for that dashboard (in vRx: **Settings → API → Create Integration**). |
| `VICARIUS_READ_ONLY` | No | Set to `true` to expose only the 30 read-only tools. |

One running server talks to one dashboard. To manage several dashboards, register the server
several times under different names (e.g. `vicarius-acme`, `vicarius-globex`), each with its own
variables.

### Query syntax

List tools paginate with `from_` and `size`. Tools that take a `q` argument (`list_assets`,
`list_publisher_products`) accept an [RSQL](https://github.com/jirutka/rsql-parser) filter
expression, for example `endpointName=="web-01"`. Values passed through dedicated arguments
(`asset_id`, `cve_id`, `asset_name`, ...) are escaped automatically.

## Tools

**read**: only reads data. **write**: creates or changes data. **destructive**: deletes or
overwrites existing data. Every write and destructive tool is hidden when `VICARIUS_READ_ONLY=true`.

### Assets

| Tool | Access | Description |
|---|---|---|
| `list_assets` | read | List all assets (endpoints) in the tenant. |
| `get_asset_attributes` | read | Get hardware and OS attributes for a single asset by its endpointId. |
| `get_asset_ip_addresses` | read | Get IP address information for a single asset by its endpointId. |
| `get_asset_applications` | read | List installed applications for a single asset by its endpointId. |
| `list_assets_with_cve` | read | List all assets affected by a specific CVE ID (e.g. CVE-2024-1234). |
| `delete_asset` | **destructive** | Remove an asset from the tenant by its endpointId. |

### Asset Groups

| Tool | Access | Description |
|---|---|---|
| `list_asset_groups` | read | List all asset groups in the tenant. |
| `list_asset_group_members` | read | List all assets that belong to a specific asset group (two-step: fetch group then query members). |
| `create_asset_group` | write | Create a new asset group. |

### CVEs / Vulnerabilities

| Tool | Access | Description |
|---|---|---|
| `list_active_cves` | read | List all active CVEs across the tenant. |
| `list_cves_by_severity` | read | List CVEs filtered by severity. |
| `get_cve_info` | read | Get detailed information for a specific CVE ID (CVSS score, description, references). |
| `get_asset_vulnerabilities` | read | List vulnerabilities across all assets, optionally filtered to a specific asset by name. |

### Patches

| Tool | Access | Description |
|---|---|---|
| `list_missing_patches` | read | List missing patches. |
| `list_pending_reboot_tasks` | read | List endpoints and patch names where patching completed but a reboot is still pending. |

### Events / Activity

| Tool | Access | Description |
|---|---|---|
| `list_event_log` | read | List the full event log, sorted oldest-first. |
| `list_cve_events` | read | List CVE detection events (new vulnerabilities appearing/disappearing), sorted oldest-first. |
| `list_task_events` | read | List the task activity log (patch/script executions across all assets). |
| `list_completed_tasks` | read | List completed patch tasks by status. |

### Reporting

| Tool | Access | Description |
|---|---|---|
| `list_top_10` | read | List top 10 most vulnerable assets or CVEs. |
| `list_endpoint_tags` | read | List all endpoint tags (xtags) defined in the tenant. |

### Automations

| Tool | Access | Description |
|---|---|---|
| `list_automations` | read | List all automations configured in the tenant. |
| `get_automation` | read | Get full details for a specific automation by its ID. |
| `create_automation` | write | Create a new automation. |
| `update_automation` | **destructive** | Update an existing automation by ID. |
| `set_automation_state` | write | Enable or disable an automation. |
| `list_script_templates` | read | List all script templates available in the tenant. |
| `list_task_types` | read | List all available task type identifiers (e.g. patch, script, reboot). |

### User Management

| Tool | Access | Description |
|---|---|---|
| `list_users` | read | List all users in the tenant. |
| `list_user_invitations` | read | List all pending user invitations. |
| `invite_user` | write | Send an invitation to a new user. |
| `resend_invitation` | write | Resend an existing invitation email by its userInvitationId. |
| `delete_invitation` | **destructive** | Cancel and delete a pending invitation by its userInvitationId. |

### Patch Catalog

| Tool | Access | Description |
|---|---|---|
| `list_patch_catalog` | read | List the global patch catalog — all patches known to vRx, with metadata. |
| `get_patch_cve_info` | read | Get the CVEs addressed by a specific patch ID. |
| `list_endpoint_patch_packages` | read | List patch packages installed or pending on endpoints. |

### Software Catalog

| Tool | Access | Description |
|---|---|---|
| `list_publisher_products` | read | List all software publishers and products detected across the tenant. |
| `list_endpoint_vulnerabilities` | read | Detailed per-endpoint vulnerability filter. |

## Development

```bash
cd v1
uv sync --extra dev
uv run pytest
```

All HTTP calls are mocked with [respx](https://lundberg.github.io/respx/), so the test suite needs
no Vicarius credentials or network access.
