"""Realistic requests and what counts as a correct first tool call and a correct answer.

Each task lists the tools that are acceptable, with a check on the arguments. `answer_any` is a list
of strings, any one of which must appear in the model's final answer (mock data, see mock_vrx.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .match import whole

ArgCheck = Callable[[dict], bool]


def _has(*words: str) -> ArgCheck:
    """Every word appears (case-insensitive) somewhere in the arguments."""
    return lambda args: all(w.lower() in str(args).lower() for w in words)


def _id(*ids: str) -> ArgCheck:
    """Every id appears as a whole token ("s-1" does not match "s-10")."""
    return lambda args: all(whole(i, str(args)) for i in ids)


def _eq(key: str, value) -> ArgCheck:
    return lambda args: args.get(key) == value


def _tenant_ok(args: dict) -> bool:
    return args.get("tenant") in (None, "acme")


def _always(_args: dict) -> bool:
    return True


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    accept: dict  # tool name -> ArgCheck
    answer_any: tuple = ()
    tags: tuple = field(default_factory=tuple)


TASKS = [
    Task("critical_findings", "Show me the critical findings.",
         {"search_findings": _has("critical")}, ("CVE-2025-1000", "CVE-2025-1001", "CVE-2025-1002")),
    Task("critical_findings_tenant", "Show me the critical findings for the acme tenant.",
         {"search_findings": lambda a: _has("critical")(a) and _tenant_ok(a)}, ("CVE-2025-1000", "CVE-2025-1001", "CVE-2025-1002"),
         tags=("tenant-word",)),
    Task("list_sites", "List my sites.", {"list_sites": _always}, ("Global",)),
    Task("tenants", "Which tenants are configured?", {"list_configured_tenants": _always}, ("acme",)),
    Task("finding_detail", "Give me the details of finding f-123.",
         {"get_finding": _eq("finding_id", "f-123")}, ("CVE-2025-1000",)),
    Task("kev", "Which findings are in the CISA KEV list?",
         {"search_findings": _has("kev"), "findings_grouped_by_vulnerability": _has("kev")}),
    Task("asset_detail", "Get asset a-77.", {"get_asset": _eq("asset_id", "a-77")}, ("WIN-DC01",)),
    Task("severity_spread", "How are my active findings spread by severity for site s-1?",
         {"findings_severity_distribution": _id("s-1"),
          "get_distribution": lambda a: a.get("kind") == "finding_severity" and _id("s-1")(a)}, ("18",)),
    Task("assets_by_os", "How many assets do we have by operating system in site s-1?",
         {"get_distribution": lambda a: a.get("kind") == "asset_os" and _id("s-1")(a)}),
    Task("asset_groups", "What asset groups exist?", {"list_asset_groups": _always}, ("Servers",)),
    Task("find_asset", "Find the asset called WIN-DC01.", {"search_assets": _has("WIN-DC01")}, ("a-77",)),
    Task("exploited_critical", "Which critical findings are actively exploited?",
         {"search_findings": lambda a: _has("critical")(a) and ("exploit" in str(a).lower() or "active" in str(a).lower())}),
    Task("risk_history", "Show how the risk score of asset a-77 changed over time.",
         {"get_risk_score_history": lambda a: a.get("entity") == "asset" and a.get("entity_id") == "a-77"}),
    Task("available_patches", "Which patches are available to install?", {"search_available_patches": _always}),
    Task("trends", "Show finding trends by week for the last month.",
         {"get_findings_trends": lambda a: a.get("granularity") == "week"}),
    Task("top_vulns", "Which vulnerabilities affect the most assets?", {"findings_grouped_by_vulnerability": _always}),
]

# The harness's `core` set is the product preset (VICARIUS_V2_TOOLSETS=core).
from vicarius_v2_mcp.toolsets import CORE  # noqa: E402,F401
