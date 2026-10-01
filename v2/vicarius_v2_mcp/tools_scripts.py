from __future__ import annotations

from .app import read_tool, write_tool
from .client import _post

# ---------------------------------------------------------------------------
# Private Scripts
# ---------------------------------------------------------------------------


@read_tool
def search_private_scripts(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search the organization's private (custom) scripts. filters (body) supports fullTextSearch,
    name, status, typeIn, sourceIn, operatingSystemFamilyIn. params supports sort, sortDirection,
    searchAfter, size, fields."""
    return _post("/privateScripts/search", tenant=tenant, params=params, body=filters or {})


@write_tool
def create_private_script(payload: dict, tenant: str | None = None) -> str:
    """Create a private script. payload: name, description, type, source, commands (per-OS command
    definitions), relatedOS, relatedApps, cveStrings."""
    return _post("/privateScripts", tenant=tenant, body=payload)


# ---------------------------------------------------------------------------
# Public Scripts
# ---------------------------------------------------------------------------


@read_tool
def search_public_scripts(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search Vicarius's public script library. filters (body) supports fullTextSearch, name,
    typeIn, sourceIn, cveIds, operatingSystemFamilyIn, relatedOS, relatedApps."""
    return _post("/publicScripts/search", tenant=tenant, params=params, body=filters or {})
