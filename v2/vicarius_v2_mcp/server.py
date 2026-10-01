from __future__ import annotations

import sys

from . import __version__
from .app import enforce_read_only, mcp

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
)

# Applied at import so read-only mode holds however the server is launched.
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
