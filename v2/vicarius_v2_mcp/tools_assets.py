from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


@read_tool
def search_assets(filters: dict | None = None, params: dict | None = None, tenant: str | None = None) -> str:
    """Search assets. filters is the request body, e.g. {"typeIn": ["MANAGED"],
    "activityStatusIn": ["ACTIVE"], "attributes": [{"key": "os_family", "value": "linux"}],
    "fullTextSearch": "...", "siteIdIn": [...], "assetGroupIdsIn": [...]}. params is optional
    query pagination: sort, sortDirection, searchAfter, size, fields."""
    return _post("/assets/search", tenant=tenant, params=params, body=filters or {})


@read_tool
def get_asset(asset_id: str, tenant: str | None = None) -> str:
    """Get full details for a single asset by its assetId."""
    return _get(f"/asset/{seg(asset_id)}", tenant=tenant)


@read_tool
def get_asset_risk_distribution(site_id: str, product_id: str | None = None, tenant: str | None = None) -> str:
    """Get asset counts bucketed by risk level for a site. site_id (UUID) is required."""
    params = {"siteId": site_id}
    if product_id:
        params["productId"] = product_id
    return _get("/assets/risk-distribution", tenant=tenant, params=params)


# ---------------------------------------------------------------------------
# Asset Groups
# ---------------------------------------------------------------------------


@read_tool
def list_asset_groups(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search asset groups (static or dynamic expression-based collections of assets).
    params supports name, siteIds, type/typeIn (STATIC/DYNAMIC), fullTextSearch, sort,
    sortDirection, searchAfter, size, fields."""
    return _get("/assetGroups", tenant=tenant, params=params)


@write_tool
def create_asset_group(payload: dict, tenant: str | None = None) -> str:
    """Create an asset group. payload: name, siteId, type (STATIC/DYNAMIC), and either
    "expression" (for DYNAMIC) or "assetIds" (for STATIC)."""
    return _post("/assetGroups", tenant=tenant, body=payload)


@destructive_tool
def update_asset_group(asset_group_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update an asset group by id. payload is the full/partial group object."""
    return _put(f"/assetGroups/{seg(asset_group_id)}", tenant=tenant, body=payload)


@destructive_tool
def delete_asset_group(asset_group_id: str, tenant: str | None = None) -> str:
    """Delete an asset group by its id."""
    return _delete(f"/assetGroups/{seg(asset_group_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Software
# ---------------------------------------------------------------------------


@read_tool
def search_software(params: dict | None = None, tenant: str | None = None) -> str:
    """Search the software inventory. params supports fullTextSearch, productNameIn, publisherNameIn,
    assetIdIn, siteIdIn, versionIn, productOsTypeIn, sort, sortDirection, searchAfter, size, fields."""
    return _get("/software", tenant=tenant, params=params)


@read_tool
def get_software(product_id: str, publisher_id: str | None = None, tenant: str | None = None) -> str:
    """Get details for a single software product by its productId."""
    params = {"publisherId": publisher_id} if publisher_id else None
    return _get(f"/software/{seg(product_id)}", tenant=tenant, params=params)


@read_tool
def list_software_versions(product_id: str, tenant: str | None = None) -> str:
    """List the versions of one software product that are installed, with how many assets run each
    version and how many findings it has (version, assetsCount, findingsCount, lastSeen). product_id
    is the id of the product in search_software."""
    return _get(f"/software/{seg(product_id)}/versions", tenant=tenant)


# ---------------------------------------------------------------------------
# Software Groups
# ---------------------------------------------------------------------------


@read_tool
def list_software_groups(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search software groups. params supports name, description, siteIds, type/typeIn,
    fullTextSearch, sort, sortDirection, searchAfter, size, fields."""
    return _get("/softwareGroups", tenant=tenant, params=params)


@read_tool
def list_software_group_software(software_group_id: str, params: dict | None = None, tenant: str | None = None) -> str:
    """List the software products inside one software group, with how many assets run each and how
    many findings it has (productName, publisherName, type, assetCount, findingCount).
    software_group_id comes from list_software_groups. params is optional paging: size, searchAfter."""
    return _get(f"/softwareGroups/{seg(software_group_id)}/software/view", tenant=tenant, params=params)


@write_tool
def create_software_group(payload: dict, tenant: str | None = None) -> str:
    """Create a software group. payload: name, description, siteId, type (STATIC/DYNAMIC), and
    either "expression" (DYNAMIC) or "platformInformationIds" (STATIC)."""
    return _post("/softwareGroups", tenant=tenant, body=payload)


@destructive_tool
def update_software_group(software_group_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a software group by id. payload is the full/partial group object."""
    return _put(f"/softwareGroups/{seg(software_group_id)}", tenant=tenant, body=payload)


@destructive_tool
def delete_software_group(software_group_id: str, tenant: str | None = None) -> str:
    """Delete a software group by its id."""
    return _delete(f"/softwareGroups/{seg(software_group_id)}", tenant=tenant)
