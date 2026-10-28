from __future__ import annotations

from typing import Literal

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, seg

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


@write_tool
def copy_script(source_script_id: str, name: str, description: str | None = None, from_public: bool = False, tenant: str | None = None) -> str:
    """Copy a script into a new private script named name. from_public=True copies from Vicarius's
    public library (an id from search_public_scripts); otherwise from a private script."""
    body = {"name": name}
    if description:
        body["description"] = description
    path = f"/privateScripts/copy-from-public/{seg(source_script_id)}" if from_public else f"/privateScripts/{seg(source_script_id)}/copy"
    return _post(path, tenant=tenant, body=body)


@write_tool
def set_private_script_published(script_id: str, published: bool, tenant: str | None = None) -> str:
    """Publish a private script so policies can run it, or unpublish it."""
    return _post(f"/privateScripts/{seg(script_id)}/{'publish' if published else 'unpublish'}", tenant=tenant)


@destructive_tool
def delete_private_script_file(script_id: str, os_family: Literal["WINDOWS", "MACOS", "LINUX"], file_id: str, tenant: str | None = None) -> str:
    """Delete one attached file from a private script's command for one OS family."""
    return _delete(f"/privateScripts/{seg(script_id)}/commands/{os_family}/files/{seg(file_id)}", tenant=tenant)


@read_tool
def download_script_file(script_id: str, file_id: str, public: bool = False, tenant: str | None = None) -> str:
    """Download a file attached to a private script (or a public one, with public=True). Returns
    JSON or text as is; for a binary file, only its content type and size."""
    kind = "publicScripts" if public else "privateScripts"
    return _get(f"/{kind}/{seg(script_id)}/files/{seg(file_id)}/download", tenant=tenant)


# ---------------------------------------------------------------------------
# Public Scripts
# ---------------------------------------------------------------------------


@read_tool
def search_public_scripts(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search Vicarius's public script library. filters (body) supports fullTextSearch, name,
    typeIn, sourceIn, cveIds, operatingSystemFamilyIn, relatedOS, relatedApps."""
    return _post("/publicScripts/search", tenant=tenant, params=params, body=filters or {})
