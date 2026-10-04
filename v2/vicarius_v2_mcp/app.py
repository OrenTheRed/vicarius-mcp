from __future__ import annotations

import os

import fastmcp
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__
from .lenient import LenientArguments

# FastMCP otherwise contacts pypi.org on startup to check for a newer version of itself.
fastmcp.settings.check_for_updates = "off"

mcp = FastMCP(
    "vicarius-v2",
    version=__version__,
    instructions=(
        "Tools for the Vicarius vRx v2 Customer API.\n"
        "- `tenant` is optional on every tool. Leave it out to use the default tenant. Pass it only "
        "when the user names a tenant, for example \"hosts of the globex tenant\" means "
        "search_assets with tenant=\"globex\". Do not ask the user which tenant to use. Call "
        "list_configured_tenants only when the user asks which tenants exist.\n"
        "- Search and list tools take their filters inside a `params` object, for example "
        "search_findings(params={\"severityIn\": [\"CRITICAL\"]}). Do not put filters at the top level.\n"
        "- List and search tools paginate with `searchAfter` and `size`.\n"
        "- If the request has what the tool needs, call the tool. Ask the user only when a required "
        "argument is missing."
    ),
)

# Accept JSON written as text where a tool wants an object, and give short, fixable argument errors.
mcp.add_middleware(LenientArguments())

# Tag applied to every tool that changes state (in Vicarius or in the local tenants file).
# VICARIUS_READ_ONLY=true hides all of them - see enforce_read_only().
WRITE_TAG = "write"

_TRUTHY = {"1", "true", "yes", "on"}


_GROUP_NAMES = {"vulnerabilities": "findings"}
KNOWN_GROUPS: set = set()  # filled as tools register, so the list of toolsets cannot drift from the tools


def group_tag(fn) -> str:
    """The toolset a tool belongs to, taken from its module: tools_assets.py is the "assets" toolset."""
    module = fn.__module__.rsplit(".", 1)[-1].removeprefix("tools_")
    group = _GROUP_NAMES.get(module, module)
    KNOWN_GROUPS.add(group)
    return f"toolset:{group}"


def read_tool(fn):
    """Register a tool that only reads data."""
    return mcp.tool(tags={group_tag(fn)}, annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(fn)


def write_tool(fn):
    """Register a tool that creates or changes data without destroying existing data."""
    return mcp.tool(
        tags={WRITE_TAG, group_tag(fn)},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True),
    )(fn)


def destructive_tool(fn):
    """Register a tool that deletes, revokes, or overwrites existing data."""
    return mcp.tool(
        tags={WRITE_TAG, group_tag(fn)},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True),
    )(fn)


def read_only_enabled() -> bool:
    return os.environ.get("VICARIUS_READ_ONLY", "").strip().lower() in _TRUTHY


def enforce_read_only() -> None:
    """When VICARIUS_READ_ONLY is set, disable every write/destructive tool so the agent can
    neither see nor call them."""
    if read_only_enabled():
        mcp.disable(tags={WRITE_TAG})
