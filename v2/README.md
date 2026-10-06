# vicarius-v2-mcp (v2): vRx v2 Customer API

MCP server for the **Vicarius vRx v2 Customer API** (`https://vicarius.cloud/api`). It gives an AI
agent **119 tools** (72 read-only, 21 write, 26 destructive) covering sites, assets, software,
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
| `VICARIUS_READ_ONLY` | `false` | Set to `true` to expose only the 72 read-only tools. |
| `VICARIUS_V2_TOOLSETS` | all tools | Offer fewer tools: `core`, group names, or a mix. See [Smaller tool list](#smaller-tool-list). |
| `VICARIUS_V2_ALLOW_CUSTOM_HOSTS` | `false` | Allow `add_configured_tenant` to save a host outside `vicarius.cloud`. Hosts you put in the tenants file yourself are always allowed. |
| `VICARIUS_V2_JEV` | `false` | Set to `true` to add the optional `assess_finding_urgency` tool. Needs `TYPESAFE_API_KEY` too. See [Optional: Jev urgency assessment](#optional-jev-urgency-assessment). |
| `TYPESAFE_API_KEY` | | Your TypeSafe API key. Only used by the Jev tool. |
| `VICARIUS_V2_JEV_PRIVACY` | `full` | `full` sends machine names, IP addresses, CVE IDs, asset groups and software names to TypeSafe. `minimal` hides all of them. |
| `VICARIUS_V2_JEV_MODEL` | `jev-latest` | The Jev model name. Set a fixed version to keep answers stable. |
| `VICARIUS_V2_URGENCY` | `false` | The neutral switch for the urgency tool. `true` turns it on, like `VICARIUS_V2_JEV`. |
| `VICARIUS_V2_URGENCY_PROVIDER` | `jev` | Who scores the finding: `jev` (TypeSafe) or `local` (a model on your machine). See [Use a local model instead](#use-a-local-model-instead). |
| `VICARIUS_V2_LLM_URL`, `VICARIUS_V2_LLM_MODEL` | | The base URL (including `/v1`) and the model name of your local server. Needed for `local`. |
| `VICARIUS_V2_LLM_SAMPLES` | `5` | How many times the local model is asked. The share that agree is the confidence. `1` asks once and reports no confidence. |
| `VICARIUS_V2_LLM_API_KEY`, `VICARIUS_V2_LLM_TIMEOUT`, `VICARIUS_V2_LLM_ALLOW_REMOTE` | | An optional bearer key, the time budget in seconds for all votes together (default 120), and permission to use a server that is not on this machine. |
| `VICARIUS_V2_JEV_NONPROD_PATTERN`, `VICARIUS_V2_JEV_DC_PATTERN` | built in | Regular expressions that replace the built-in rules for "non-production name" and "domain controller name". |

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

### Smaller tool list

The full tool list is sent to the model with every conversation: about 15,000 to 19,000 tokens for
119 tools. A model with a small context window cannot hold that, and picks tools less reliably from
a long list. `VICARIUS_V2_TOOLSETS` offers fewer tools:

| Value | Tools |
|---|---|
| not set, or `all` | Every tool. |
| `core` | 16 read tools for the usual questions: tenants, sites, findings (search, detail, grouped, severity, trends), asset search and detail, asset groups, distributions, risk history and patches. About 3,000 tokens. It includes `assess_finding_urgency` when Jev is on. |
| a group name | One group of tools: `tenants`, `sites`, `assets`, `findings`, `scanning`, `patches`, `compliance`, `reports`, `scripts`, `resources`, `insights` or `jev`. Each group is one `tools_*.py` file. |
| a mix | A comma or space separated list, for example `core,compliance` or `findings sites`. |

An unknown name stops the server with a message that lists the valid ones. `VICARIUS_READ_ONLY=true`
still applies on top: a write tool inside a chosen group stays hidden.

### Optional: Jev urgency assessment

vRx already gives every finding a severity, CVSS, EPSS, a CISA KEV flag, an exploit status and a
risk score. [Jev](https://docs.typesafe.ai) (TypeSafe's decision model) does not redo those. It
adds one judgment the numbers do not capture: **how urgent this finding is on this asset**. A
critical CVE on a domain controller and the same CVE on a box named `qa-web-01` should not get the
same answer.

The tool `assess_finding_urgency(finding_id)` is **off by default and absent from the tool list**.
To turn it on, set both `VICARIUS_V2_JEV=true` and `TYPESAFE_API_KEY`. It only reads from vRx, so
it stays available in read-only mode. The server contacts `api.typesafe.ai` only when you call it.

It returns vRx's own numbers unchanged, Jev's `disposition` (`DEFER`, `STANDARD`, `ACCELERATED`,
`EMERGENCY` or `REVIEW`) with probabilities and a confidence value, the model version, and the exact
facts it sent. **vRx's exploit evidence sets a ceiling and a floor**, in code, whatever the model
says. With no CISA KEV listing, no exploit tags and a low or medium EPSS band, the disposition is
capped at `STANDARD`. A finding listed in CISA KEV (exploited in the wild) is never lower than
`STANDARD`: a `DEFER` becomes `STANDARD`. The output then shows `guard.applied: true`, `guard.kind`
(`cap` or `floor`) and the model's original answer. An asset's role cannot make weak evidence urgent
or strong evidence ignorable. The floor only lifts `DEFER`; it never raises anything higher, and it
leaves `REVIEW` alone. The answer is advice. It changes nothing in vRx. Treat `REVIEW` or a low
confidence as "a person decides". Call it with `preview=true` to see what would be sent without
sending it.

**You choose what leaves your machine** with `VICARIUS_V2_JEV_PRIVACY`:

| Mode | Sent to TypeSafe |
|---|---|
| `full` (default) | Labels computed in code (severity, CVSS and EPSS bands, CISA KEV flag, exploit status, vRx's exploit tags such as `public`, `weaponized`, `ransomware`, a role, an environment hint and an OS family), plus the CVE ID, the machine name, IP addresses (when vRx reports them), OS, software name and version, and asset group names. **TypeSafe sees all of them.** Free text goes under `untrusted_text`. |
| `minimal` | Only the labels computed in code. **No machine names, IP addresses, CVE IDs, asset groups or software names.** |

How the labels are made, on your machine: the asset name and the names of the asset groups it
belongs to are checked. A name that contains `qa`, `test`, `dev`, `stg`, `staging`, `uat`,
`sandbox`, `lab` or `demo` as a separate word gives `non_production`. A name with `dc` as a
separate word, or a group called "Domain Controllers", gives `domain_controller`. A Windows Server
OS, or a Linux server distribution (Rocky, Red Hat, CentOS, Alma, Debian, SUSE, Oracle or Amazon
Linux), gives `server`. Ubuntu stays `unknown`, because it is often a desktop. No match gives `none` or `unknown`, never "production". Change
the rules with `VICARIUS_V2_JEV_NONPROD_PATTERN` and `VICARIUS_V2_JEV_DC_PATTERN`. The group names
are used for these labels in both modes, and are only sent in `full` mode.

The vRx v2 API does not say whether software is running or only installed. So "installed but not
running" cannot be judged, and the tool does not guess. If vRx adds such a field, the code reads
`isRunning` when it is present.

Limits you should know:

- Jev is new (September 2026). Its answers can change between model versions. Set
  `VICARIUS_V2_JEV_MODEL` to a fixed version if you want stable results.
- Jev is off until you opt in, but once it is on, `full` is the default: TypeSafe sees your machine
  names, IP addresses and CVE IDs. Set `VICARIUS_V2_JEV_PRIVACY=minimal` to hide them. In `minimal`
  mode Jev cannot use what it knows about a specific CVE, which can make its answers less sure.
- Text can steer Jev. That is why `full` keeps free text under
  `untrusted_text`, cuts it to 200 characters and removes control characters.
- A third-party test found Jev ranked urgency well, but about as well as a simple points formula.
  Use it as a second opinion, not as the decision.
- Read [TypeSafe's terms](https://docs.typesafe.ai/legal.md) before you send them any tenant data.

#### Use a local model instead

`assess_finding_urgency` can ask a model on your own machine and never contact TypeSafe. It works
with any server that speaks the OpenAI chat API: Ollama, LM Studio, llama.cpp, oMLX, vLLM.

```
VICARIUS_V2_URGENCY=true
VICARIUS_V2_URGENCY_PROVIDER=local
VICARIUS_V2_LLM_URL=http://127.0.0.1:11434/v1      # Ollama. LM Studio: :1234/v1, llama.cpp: :8080/v1, vLLM: :8000/v1
VICARIUS_V2_LLM_MODEL=<the model name your server knows>
```

It sends the same facts as the Jev provider, and `VICARIUS_V2_JEV_PRIVACY` works the same way. The
answer comes under `local` (not `jev`) and `preview=true` shows the payload under
`sent_to_local_model`. The cap and the floor apply too, and the output reports the model's own
answer under `guard.original`.

- **Confidence comes from votes.** Many local servers return no token probabilities (Ollama's
  OpenAI endpoint and oMLX do not). So the model is asked several times (`VICARIUS_V2_LLM_SAMPLES`,
  default 5) and the share of answers that agree is the confidence. The output says
  `confidence_source: "votes"`. With a tie, the more cautious answer wins, and `REVIEW` wins over
  every other answer. Votes measure how consistent the model is, **not** a calibrated probability: a
  model can be consistently wrong, and a small local model often agrees with itself every time. The
  shares are out of the votes asked, so an answer that is missing or unusable lowers the confidence.
  It costs about 2 seconds for 5 votes on a 4B model on an Apple M4 Pro. A model can be slower.
  `VICARIUS_V2_LLM_TIMEOUT` is the budget for all votes together. When it runs out, or the server
  fails after some votes, the votes so far are used and the output says `cut_short`.
- **"Local" is enforced.** The URL must point at this machine: the name `localhost`, or an address
  in `127.0.0.0/8` or `::1`. Other names, including `*.localhost`, are refused, because some systems
  resolve them elsewhere. A server on another computer, or a hosted API, is outside this machine,
  and the facts would leave it. That is refused unless you set `VICARIUS_V2_LLM_ALLOW_REMOTE=true`,
  and the output then carries a warning. Proxy settings (`HTTP_PROXY` and the like) are ignored.
  Redirects are not followed, the URL may not contain a password, and an API key is never sent
  over plain `http` to another machine.
- **Pick the model.** It must follow instructions and answer in JSON. A reasoning model that spends
  its answer thinking gives no usable answers, and the tool says so. If your server does not support
  JSON-schema output, the tool asks again in plain words and checks the answer itself.
- **Measured.** On made-up facts, two models served by oMLX (Qwen3-4B and gemma4) both passed five
  rules: a domain controller ranks at least as high as a server and a server as a workstation, a
  "qa" name lowers a server, weak findings end at `STANDARD` or below, unknown facts give `REVIEW`,
  and repeated runs agree. Their individual answers differ: gemma4 downgraded a strong finding on a
  non-production workstation to `DEFER`, where Qwen3-4B said `STANDARD`. It is advice, so check it.
  Small local models are easier to steer with text in tenant data than Jev is. `minimal` mode keeps
  names out of the prompt.

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
| `list_software_versions` | read | List the installed versions of one software product, with asset and finding counts per version. |

### Software Groups

| Tool | Access | Description |
|---|---|---|
| `list_software_groups` | read | List/search software groups. |
| `list_software_group_software` | read | List the software products inside one software group, with asset and finding counts. |
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
| `list_risk_tags` | read | List the vTags (risk tags) that feed a finding's risk score, with their weights and whether an admin changed them. |

**vTags.** A vTag is a risk tag, a reason attached to a finding that feeds its risk score, such as
`exploit.ransomware` ("Exploited by Ransomware") or `intel.actor-country.ir`. A finding's own vTags are in the
`riskTags` of `get_finding`. In the vRx web app an admin can change a vTag's weight (a multiplier on the
platform default of 1.0); this server only reads them. Changing a weight needs an API key that is allowed to
write vTags, and it re-scores findings, so there is no tool for it yet.

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
| `list_patch_group_patches` | read | List the patches inside one patch group, with asset and CVE counts. |
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

### Urgency assessment (optional, off by default)

| Tool | Access | Description |
|---|---|---|
| `assess_finding_urgency` | read | Judge how urgent one finding is on its own asset with TypeSafe's Jev model. Only present when `VICARIUS_V2_JEV=true` and `TYPESAFE_API_KEY` are set. Not counted in the 119 tools. |

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
