# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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

[1.0.0]: https://github.com/OrenTheRed/vicarius-mcp/releases/tag/v1.0.0
