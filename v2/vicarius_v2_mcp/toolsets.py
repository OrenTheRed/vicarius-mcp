"""Choose which tools the server offers, with VICARIUS_V2_TOOLSETS.

The full tool list costs about 15,000 to 19,000 tokens of every conversation. That is fine for a
large hosted model and too much for a local model with a small context window, which also picks
tools less reliably from a long list. A smaller list fixes both.

  VICARIUS_V2_TOOLSETS=core                 a small set of read tools for the usual questions
  VICARIUS_V2_TOOLSETS=findings,sites       whole groups of tools (one group per tools_*.py file)
  VICARIUS_V2_TOOLSETS=core,compliance      any mix
  (not set, or "all")                       every tool, as before

VICARIUS_READ_ONLY=true still applies on top: a write tool in a chosen group stays hidden.
"""

from __future__ import annotations

import os

from .app import KNOWN_GROUPS, mcp

# The tools for the questions people ask most: findings, assets, sites, trends, tenants.
# Read-only, so a core list never exposes a write tool. assess_finding_urgency is included when
# it is enabled (it does not exist otherwise, so the name matches nothing).
CORE = [
    "list_configured_tenants",
    "list_sites", "get_site",
    "search_findings", "get_finding", "findings_grouped_by_vulnerability", "findings_severity_distribution",
    "get_findings_trends", "get_risk_score_history", "get_distribution",
    "search_assets", "get_asset", "list_asset_groups", "get_asset_risk_distribution",
    "get_patch_summary", "search_available_patches",
    "assess_finding_urgency",
]

def groups() -> list:
    """The group names: one for each tools_*.py file ("tools_vulnerabilities.py" is called "findings").
    Taken from the tools that are registered, so a new tools file is a valid toolset at once."""
    return sorted(KNOWN_GROUPS)


def requested() -> list:
    raw = os.environ.get("VICARIUS_V2_TOOLSETS", "")
    return [name for name in dict.fromkeys(part.strip().lower() for part in raw.replace(" ", ",").split(",")) if name]


def enforce_toolsets() -> None:
    """Keep only the requested tools. Call this BEFORE enforce_read_only(): FastMCP applies the
    latest rule last, and an allowlist applied afterwards would show write tools again."""
    names = requested()
    if not names or "all" in names:
        return
    allowed_names, allowed_tags = set(), set()
    for name in names:
        if name == "core":
            allowed_names.update(CORE)
        elif name in groups():
            allowed_tags.add(f"toolset:{name}")
        else:
            raise ValueError(
                f'Unknown toolset "{name}" in VICARIUS_V2_TOOLSETS. Use all, core, or any of: {", ".join(groups())}'
            )
    # One call with both names and tags would keep only tools matching both. Two steps give the union.
    if allowed_names:
        mcp.enable(names=allowed_names, only=True)
    if allowed_tags:
        mcp.enable(tags=allowed_tags, only=not allowed_names)
