from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg

# ---------------------------------------------------------------------------
# Patch Catalog
# ---------------------------------------------------------------------------


@read_tool
def search_patches(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search the patch catalog (patches applicable to your assets). filters (body) supports
    assetId, productId, publisherId, operatingSystemFamilyIn, patchType, patchIdentifier,
    managedBy, fullTextSearch. params supports size, sort, sortDirection."""
    return _post("/patches", tenant=tenant, params=params, body=filters or {})


@read_tool
def get_patch_summary(site_id: str, asset_id: str | None = None, product_id: str | None = None, tenant: str | None = None) -> str:
    """Get patch status summary/distribution for a site. site_id (UUID) is required."""
    params = {"siteId": site_id}
    if asset_id:
        params["assetId"] = asset_id
    if product_id:
        params["productId"] = product_id
    return _get("/patches/summary", tenant=tenant, params=params)


# ---------------------------------------------------------------------------
# Patch Groups
# ---------------------------------------------------------------------------


@read_tool
def list_patch_groups(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search patch groups. params supports fullTextSearch, type/typeIn, siteIds,
    sort, sortDirection, searchAfter, size."""
    return _get("/patchGroups", tenant=tenant, params=params)


@write_tool
def create_patch_group(payload: dict, tenant: str | None = None) -> str:
    """Create a patch group. payload: name, description, type (STATIC/DYNAMIC), and either
    "expression" (DYNAMIC) or "patchSelections" (STATIC)."""
    return _post("/patchGroups", tenant=tenant, body=payload)


@destructive_tool
def update_patch_group(patch_group_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a patch group by id. payload is the full/partial group object."""
    return _put(f"/patchGroups/{seg(patch_group_id)}", tenant=tenant, body=payload)


@destructive_tool
def delete_patch_group(patch_group_id: str, tenant: str | None = None) -> str:
    """Delete a patch group by its id."""
    return _delete(f"/patchGroups/{seg(patch_group_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Available Patches
# ---------------------------------------------------------------------------


@read_tool
def search_available_patches(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search patches available/pending to be installed (as opposed to the full catalog).
    Accepts the same filters as search_patches."""
    return _post("/availablePatches/search", tenant=tenant, params=params, body=filters or {})


# ---------------------------------------------------------------------------
# Reboot Profiles
# ---------------------------------------------------------------------------


@read_tool
def get_reboot_profile(tenant: str | None = None) -> str:
    """Get the organization's automatic-reboot settings."""
    return _get("/settings/reboot-profile", tenant=tenant)


@destructive_tool
def update_reboot_profile(auto_reboot_settings: dict, tenant: str | None = None) -> str:
    """Update the organization's automatic-reboot settings. auto_reboot_settings is the settings dict."""
    return _put("/settings/reboot-profile", tenant=tenant, body={"autoRebootSettings": auto_reboot_settings})


# ---------------------------------------------------------------------------
# Asset Inactivity Settings
# ---------------------------------------------------------------------------


@read_tool
def get_asset_inactivity_settings(tenant: str | None = None) -> str:
    """Get the organization's asset auto-removal (inactivity) settings."""
    return _get("/v2/asset-inactivity-settings", tenant=tenant)


@destructive_tool
def update_asset_inactivity_settings(asset_auto_removal_days: int, tenant: str | None = None) -> str:
    """Set the number of days of inactivity after which an asset is automatically removed."""
    return _put("/v2/asset-inactivity-settings", tenant=tenant, body={"assetAutoRemovalDays": asset_auto_removal_days})
