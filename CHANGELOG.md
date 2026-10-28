# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

The release page on GitHub shows the section of this file for that version, so write each entry
for the people who use the servers: what was added, what changed, what was fixed.

## [Unreleased]

## [1.8.0] - 2026-10-28

v2 now covers the published API reference at https://documentation.vicarius.cloud/ (the
`openapi.yaml` of 2026-10-20, 203 operations). Nineteen new tools and four new options cover the
operations that had no tool.

### Added
- v2 read tools: `list_software_installations` (which assets have a given software version),
  `list_public_report_specs` (the ready-made reports Vicarius publishes, such as "Operating System
  Report"), `generate_group_expression` (plain words to a DYNAMIC asset or patch group rule; it
  changes nothing), `get_user_group_site_permissions` and `download_script_file`.
- v2 options on existing read tools: `list_site_agents(site_id=...)`,
  `list_named_targets(site_id=...)`, `list_reports(scheduled=True)` and
  `get_cis_benchmark_catalog(summary=True)`.
- v2 write tools: `export_report` (run a report now), `set_report_enabled`, `add_public_report`
  (link or clone a ready-made report), `add_named_target_to_site`, `copy_script` (from a private or
  a public script) and `set_private_script_published`.
- v2 destructive tools: `cancel_policy_tasks` (stop the pending tasks of a patch or script policy),
  `rename_asset`, `set_report_schedule` (replace or remove), `delete_private_script_file`,
  `update_user_group_members` (remove members or replace the list), `rename_user_group`,
  `delete_user_group` and `update_user_group_site_permission`.
- `VICARIUS_READ_ONLY=true` hides every new write and destructive tool, as before. No new tool is in
  the `core` toolset.

### Changed
- v2: the descriptions of eleven tools that call routes missing from the published reference now
  start with **[Experimental: undocumented endpoint]**: the six software group tools,
  `search_patchless_protections`, `count_patchless_protections`, `list_patchless_protection_events`,
  `list_risk_tags` and `invite_members`. They still work; Vicarius may change them without notice.
- v2: the full tool list is now about 20,000 to 26,000 tokens (148 tools). The size test budget
  went from 64,000 to 74,000 characters (measured 70,900).

### Known limits
- The read tools were run against a live tenant. The write and destructive tools were tested
  against mocked routes only, not a live tenant.
- `get_user_group_site_permissions` returned 403 with the test key, which has no user group rights.
- Not added: uploading files to a private script (the route takes a multipart file upload) and
  `POST /api/sites/{id}/agents`, which does the same as `create_site_agent`.

### Unchanged
- The v1 server has no changes. It is published at 1.8.0 because both packages share one version.

## [1.7.0] - 2026-10-20

A one-line installer for macOS and Linux.

### Added
- A one-line installer for macOS and Linux:
  `curl -fsSL https://raw.githubusercontent.com/OrenTheRed/vicarius-mcp/main/install.sh | bash`.
  It asks its questions first (type `b` to go back one question), shows a review, and changes
  nothing until you submit. It detects the system, installs git, curl, tar and gzip if they are
  missing, then installs uv and the servers. It writes the v2 tenants file, readable by you only,
  and connects Claude Code, Codex or Claude Desktop. `--dry-run` shows what it would do.
- The installer checks each v2 API key with one read-only call before it keeps the key. API keys
  never go on a command line, except the v1 key for Claude Code and Codex, which their own
  `mcp add` commands need.
- CI lints the installer with shellcheck and tests it on Linux and macOS, including bash 3.2.

### Unchanged
- The v1 and v2 servers have no changes in this release. Both packages are published at 1.7.0
  because they share one version number.

## [1.6.0] - 2026-10-20

Ten new read-only tools for v2. They come from a second endpoint check, which compared the routes
the vRx web app calls with the routes the tools use. All ten were run against a live tenant.

### Added
- v2: patchless protection (vShield), which had no tools before. `get_finding_patchless_protection`
  shows, for one finding, whether it can be protected and in which modes (`MONITOR`,
  `MONITOR_AND_PREVENT`), the protections that cover it, or the other findings one protection would
  also cover. `search_patchless_protections`, `count_patchless_protections` and
  `list_patchless_protection_events` list, count and follow protections. They are in the `findings`
  toolset.
- v2: `search_available_patches_grouped` lists pending patches with one row per patch instead of one
  row per asset, with the asset count, the CVEs the patch fixes, and the affected software.
- v2: `get_software_version` gets one installed version of a product, with asset and finding counts.
- v2: `search_patches_for_static_group` and `search_software_for_static_group` find the patches and
  the software to put in a STATIC group.
- v2: `get_my_access` shows who the API key acts as, its current site, and its permissions there.
  Use it to explain an `ERROR 403`.
- v2: `list_scan_profile_options` lists the scan profile categories and perspectives that
  `search_scan_profiles` filters on.

### Changed
- v2 now has 129 tools, 82 of them read-only. `core` is unchanged. The full tool list now costs
  about 17,000 to 22,000 tokens. The size limit in the tests went from 58,000 to 64,000 characters;
  the list now measures about 60,700.

### Known limits
- Starting, enabling, disabling and deleting a patchless protection are not tools yet. They change
  what runs on an asset, and they were not tested.
- The test tenant has no patchless protections, so `list_patchless_protection_events` was not run
  on a real protection. With a made-up id it returns `ERROR 403`. The `statusIn` filter of the protection search exists, but its values are not
  known: a guessed value returns `ERROR 400`.
- `search_available_patches_grouped` takes a `size` of 500 at most and pages with `from`.
- Left out on purpose: `/exploitIntelligence/threat`, `/findings/cve` and `/scanProfile/tags` return
  errors from the server. `/me/organization` returns the organization secret key.

### Unchanged
- v1 (`vicarius-mcp`) has no changes in this release. It is published at 1.6.0 because both
  packages share one version number.

### Upgrade notes
- No action is needed. The new tools are read-only, so `VICARIUS_READ_ONLY=true` keeps them.

## [1.5.0] - 2026-10-06

Four new read-only tools for v2, found by checking the vRx API for endpoints that the tools did
not cover. All four were run against a live tenant.

### Added
- v2: `list_risk_tags` lists the vTags (risk tags) that feed a finding's risk score. Each has a code
  such as `exploit.ransomware`, a name, an explanation, a category (`EXPLOIT` or `INTELLIGENCE`),
  the platform default weight, the effective weight, and whether an admin changed it. A finding's
  own vTags were already in `get_finding`. There is no tool to change a weight: that needs an API
  key that is allowed to write vTags, and it re-scores findings.
- v2: `list_patch_group_patches` lists the patches inside a patch group, with the number of assets
  and CVEs each affects.
- v2: `list_software_group_software` lists the software products inside a software group, with
  asset and finding counts.
- v2: `list_software_versions` lists the installed versions of one software product, with asset and
  finding counts per version.
- v2 now has 119 tools, 72 of them read-only. `core` is unchanged. The full tool list now costs
  about 16,000 to 20,000 tokens, depending on the model's tokenizer.
- The two group views page with `size` and `from` (not `searchAfter`). Patch groups accept a
  `size` of up to 200 and refuse 500. The vTag list is not paged.

### Unchanged
- v1 (`vicarius-mcp`) has no changes in this release. It is published at 1.5.0 because both
  packages share one version number.

### Upgrade notes
- No action is needed. The new tools are read-only, so `VICARIUS_READ_ONLY=true` keeps them.
  They are in the `findings`, `patches` and `assets` toolsets.

## [1.4.0] - 2026-10-05

The urgency tool can now ask a model on your own machine, so no data has to go to TypeSafe. It
stays off unless you switch it on.

### Added
- v2: `assess_finding_urgency` can use a local model instead of Jev. Set
  `VICARIUS_V2_URGENCY_PROVIDER=local`, `VICARIUS_V2_LLM_URL` and `VICARIUS_V2_LLM_MODEL`. It works
  with any server that speaks the OpenAI chat API (Ollama, LM Studio, llama.cpp, oMLX, vLLM). It
  sends the same facts, `VICARIUS_V2_JEV_PRIVACY` works the same way, and the weak-evidence cap at
  `STANDARD` still applies. The answer appears under `local` and `preview=true` shows the payload
  under `sent_to_local_model`.
- v2: the confidence of a local answer comes from votes. The model is asked several times
  (`VICARIUS_V2_LLM_SAMPLES`, default 5) and the share that agree is the confidence, because many
  local servers return no token probabilities. The output says `confidence_source: "votes"`. Votes
  measure how consistent a model is, not a calibrated probability. Shares are out of the votes
  asked, so an unusable or missing answer lowers the confidence.
- v2: `VICARIUS_V2_LLM_TIMEOUT` is the time budget for all votes together (default 120 seconds). When
  it runs out, or the server fails after some votes, the votes so far are used and the output says
  `cut_short`.
- v2: `VICARIUS_V2_URGENCY=true` is a neutral switch for the tool. `VICARIUS_V2_JEV=true` still works.
- v2: a floor next to the existing cap. A finding listed in CISA KEV (exploited in the wild) is never
  lower than `STANDARD`: a `DEFER` from the model becomes `STANDARD`. It only lifts `DEFER`, it
  never raises anything higher, and `REVIEW` is left alone. It applies to Jev and to a local model.
  Found when a local model deferred a strong finding on a non-production workstation.

### Changed
- v2: `VICARIUS_V2_URGENCY`, when it is set, wins over the older `VICARIUS_V2_JEV`, so `false` turns
  the tool off even if an old `VICARIUS_V2_JEV=true` is still around.
- v2: the guard now reports Jev's or the model's answer under `guard.original`, and says which rule
  applied in `guard.kind` (`cap` or `floor`). `guard.jev_original` stays for Jev.
- README: the example for pinning a release names the current release, and a test keeps it current.

### Security
- "Local" is enforced. The model URL must point at this machine: the name `localhost` or an
  address in `127.0.0.0/8` or `::1`. Other names, including `*.localhost`, are refused because some
  systems resolve them elsewhere. A server on another computer, or a hosted API, is refused unless
  you set `VICARIUS_V2_LLM_ALLOW_REMOTE=true`, and the output then carries a warning.
- Proxy settings (`HTTP_PROXY` and the like) are ignored for the model server, so the facts and the
  key go straight to it. Redirects are not followed, and a password inside the URL is refused.
- An API key is never sent over plain `http` to another machine. Use `https`, or no key.

### Upgrade notes
- No action is needed. The default provider is still Jev, and the tool is still off by default.
- To keep your data on your machine, use a local model and set `VICARIUS_V2_JEV_PRIVACY=minimal`
  if you also want names kept out of the prompt.

## [1.3.0] - 2026-10-04

Makes the v2 server work well with local models and other MCP clients, not only large hosted
agents. Nothing changes for you unless you use the new settings.

### Added
- v2: `VICARIUS_V2_TOOLSETS` offers fewer tools. `core` is 16 read tools (about 3,000 tokens
  against about 15,000 to 19,000 for all 115). Whole groups (`findings`, `sites`, ...) can be
  chosen and mixed. This helps any model with a small context window, and any client that picks
  tools less reliably from a long list. `VICARIUS_READ_ONLY` still applies on top. On the
  evaluation harness a small local model (Qwen3-4B) made the right tool call with the right
  arguments in all 48 runs with `core` (16 tasks that `core` is meant to serve), using 5.7 times
  fewer prompt tokens than with all tools.
- v2: a JSON object or array written as text is accepted where a tool wants an object or an
  array, and the text "null" or "none" for `tenant` means the default tenant, because some models
  and clients send arguments that way.
- `v2/evals`: a harness that measures how well a local or hosted model drives the v2 tools. It
  scores tool choice, arguments and answers against a mocked vRx, so changes can be measured. It is
  a development tool and is not part of the published package.
- README: a section on local models and small context windows, and a generic MCP client config.

### Changed
- v2: the server instructions that MCP clients show to the model are rewritten. They now say that
  `tenant` is optional (leave it out for the default tenant, and do not ask the user which one),
  that a word like "tenant" in a request is not a request to list tenants, that filters go inside
  a `params` object, and to call a tool when the request has what it needs. On the evaluation
  harness this lifted a small local model (Qwen3-4B) from 75% to 100% correct tool calls on a
  small tool set.
- v2: when an argument is wrong, the error now says which one and how to fix it, for example that
  a filter belongs inside `params`, instead of a validation dump with a link.
- GitHub release pages now show the matching section of this changelog, instead of an automatic
  list of pull requests. The release workflow stops if the changelog has no entry for the tag or
  if the packages declare another version, and CI checks that the current version has an entry.

### Upgrade notes
- No action is needed. Every tool is still offered by default.
- To use a local model with a small context window, set `VICARIUS_V2_TOOLSETS=core`. Add
  `VICARIUS_READ_ONLY=true` unless you need the agent to make changes.

## [1.2.0] - 2026-10-04

Adds an optional urgency assessment to v2. Nothing changes for you unless you turn it on.

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

### Upgrade notes
- No action is needed. The new tool does not exist until you set `VICARIUS_V2_JEV=true` and
  `TYPESAFE_API_KEY`.
- If you turn it on, the default `VICARIUS_V2_JEV_PRIVACY=full` sends machine names, IP addresses,
  CVE ids, asset groups and software names to TypeSafe. Set `minimal` to hide them.

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

[Unreleased]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.5.0...HEAD
[1.5.0]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/OrenTheRed/vicarius-mcp/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/OrenTheRed/vicarius-mcp/releases/tag/v1.1.0
[1.0.0]: https://github.com/OrenTheRed/vicarius-mcp/releases/tag/v1.0.0
