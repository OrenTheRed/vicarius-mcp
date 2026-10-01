from __future__ import annotations

import os

import fastmcp
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import __version__

# FastMCP otherwise contacts pypi.org on startup to check for a newer version of itself.
fastmcp.settings.check_for_updates = "off"

mcp = FastMCP(
    "vicarius-v2",
    version=__version__,
    instructions=(
        "Tools for the Vicarius vRx v2 Customer API. Every tool accepts an optional `tenant` "
        "argument; call list_configured_tenants to see which tenants are available. List/search "
        "tools paginate with `searchAfter` and `size`."
    ),
)

# Tag applied to every tool that changes state (in Vicarius or in the local tenants file).
# VICARIUS_READ_ONLY=true hides all of them - see enforce_read_only().
WRITE_TAG = "write"

_TRUTHY = {"1", "true", "yes", "on"}


def read_tool(fn):
    """Register a tool that only reads data."""
    return mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))(fn)


def write_tool(fn):
    """Register a tool that creates or changes data without destroying existing data."""
    return mcp.tool(
        tags={WRITE_TAG},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True),
    )(fn)


def destructive_tool(fn):
    """Register a tool that deletes, revokes, or overwrites existing data."""
    return mcp.tool(
        tags={WRITE_TAG},
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True),
    )(fn)


def read_only_enabled() -> bool:
    return os.environ.get("VICARIUS_READ_ONLY", "").strip().lower() in _TRUTHY


def enforce_read_only() -> None:
    """When VICARIUS_READ_ONLY is set, disable every write/destructive tool so the agent can
    neither see nor call them."""
    if read_only_enabled():
        mcp.disable(tags={WRITE_TAG})
