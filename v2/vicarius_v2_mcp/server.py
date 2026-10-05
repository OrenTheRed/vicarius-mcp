from __future__ import annotations

import sys

from . import __version__
from .app import enforce_read_only, mcp
from .toolsets import enforce_toolsets

# Import for registration side effects: each module's tool decorators register
# against the shared `mcp` instance above.
from . import (  # noqa: F401
    tools_tenants,
    tools_sites,
    tools_assets,
    tools_vulnerabilities,
    tools_scanning,
    tools_patches,
    tools_compliance,
    tools_reports,
    tools_scripts,
    tools_resources,
    tools_insights,
    tools_jev,
)

# Applied at import so they hold however the server is launched. The toolset filter must come first:
# an allowlist applied after read-only mode would show the write tools again.
try:
    enforce_toolsets()
except ValueError as exc:
    sys.exit(f"vicarius-v2-mcp: {exc}")
enforce_read_only()

USAGE = """\
vicarius-v2-mcp - MCP server for the Vicarius vRx v2 Customer API (stdio transport).

This command is launched by your MCP client (Claude Code, Codex, ...), not run by hand.

Options:
  --version   Print the version and exit
  --help      Show this message and exit

Environment:
  VICARIUS_V2_TENANTS_FILE    Tenants file (default: ~/.config/vicarius-v2-mcp/tenants.json)
  VICARIUS_V2_TENANTS         Tenants as inline JSON (used only if the tenants file is absent)
  VICARIUS_V2_DEFAULT_TENANT  Tenant used when a tool call omits `tenant`
  VICARIUS_READ_ONLY          Set to "true" to expose read-only tools only
  VICARIUS_V2_TOOLSETS        Offer fewer tools: "core", group names such as "findings,sites", or "all"

Optional urgency assessment (off unless switched on and the chosen provider is set up):
  VICARIUS_V2_JEV             Set to "true" to add the assess_finding_urgency tool
  TYPESAFE_API_KEY            TypeSafe API key
  VICARIUS_V2_JEV_PRIVACY     "full" (default: machine names, IPs, CVE ids, software names are sent)
                              or "minimal" (none of those are sent)
  VICARIUS_V2_JEV_MODEL       Jev model alias (default: jev-latest)
  VICARIUS_V2_URGENCY         Set to "true" to add the tool (same as VICARIUS_V2_JEV)
  VICARIUS_V2_URGENCY_PROVIDER  "jev" (default) or "local" (a model on this machine)
  VICARIUS_V2_LLM_URL, VICARIUS_V2_LLM_MODEL   local model server (base URL with /v1) and model name
  VICARIUS_V2_LLM_SAMPLES     How many times to ask the local model (default 5; the agreeing share is the confidence)
  VICARIUS_V2_LLM_TIMEOUT     Seconds for all votes together (default 120)
"""


def main() -> None:
    args = sys.argv[1:]
    if "--version" in args:
        print(f"vicarius-v2-mcp {__version__}")
        return
    if "--help" in args or "-h" in args:
        print(USAGE)
        return
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
