from __future__ import annotations

import json
import uuid

from .app import destructive_tool, read_tool, write_tool
import os

from .client import (
    _delete,
    _get,
    _post,
    _put,
    is_vicarius_host,
    list_configured_tenant_names,
    normalize_host,
    remove_tenant,
    save_tenant,
    seg,
)

# ---------------------------------------------------------------------------
# Tenants & Organizations
# ---------------------------------------------------------------------------


@read_tool
def list_configured_tenants() -> str:
    """List the tenant names configured locally (in the tenants file or VICARIUS_V2_TENANTS).
    Pass one of these as the `tenant` argument to any tool to target that tenant. Distinct from
    list_organizations, which queries the real Vicarius backend for organizations visible to the
    calling account."""
    return json.dumps({"tenants": list_configured_tenant_names()}, indent=2)


@destructive_tool
def add_configured_tenant(name: str, api_key: str, host: str = "vicarius.cloud", overwrite: bool = False) -> str:
    """Add a locally configured tenant: a name mapped to an API key + host. Persisted
    immediately to the tenants file - available to use as the `tenant` argument on the very next
    tool call, no server restart needed. Refuses to replace an existing tenant unless
    overwrite=True. host must be vicarius.cloud or a subdomain of it, unless the user has set
    VICARIUS_V2_ALLOW_CUSTOM_HOSTS=true."""
    try:
        normalized = normalize_host(host)
        if not is_vicarius_host(normalized) and os.environ.get("VICARIUS_V2_ALLOW_CUSTOM_HOSTS", "").strip().lower() not in ("1", "true", "yes", "on"):
            return (
                f'ERROR: host "{normalized}" is not a vicarius.cloud host. To use a custom host, '
                "edit the tenants file directly or set VICARIUS_V2_ALLOW_CUSTOM_HOSTS=true."
            )
        save_tenant(name, api_key, normalized, overwrite=overwrite)
    except (ValueError, OSError) as exc:
        return f"ERROR: {exc}"
    return json.dumps({"saved": name, "tenants": list_configured_tenant_names()}, indent=2)


@destructive_tool
def remove_configured_tenant(name: str) -> str:
    """Remove a locally configured tenant by name."""
    try:
        removed = remove_tenant(name)
    except (ValueError, OSError) as exc:
        return f"ERROR: {exc}"
    return json.dumps({"removed": removed, "tenants": list_configured_tenant_names()}, indent=2)


@read_tool
def list_organizations(tenant: str | None = None) -> str:
    """List every Vicarius organization (tenant) visible to the account behind the given tenant's API key."""
    return _get("/me/availableOrganization", tenant=tenant)


@read_tool
def list_organization_sites(org_id: str, tenant: str | None = None) -> str:
    """List the sites visible to the current user within a specific organization by its org_id (UUID)."""
    return _get(f"/me/organizations/{seg(org_id)}/sites", tenant=tenant)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@read_tool
def list_api_keys(size: int = 10, sort: str = "createdAt", sort_direction: int = -1, search_after: str = "", tenant: str | None = None) -> str:
    """List API keys for the tenant's organization. sort_direction is 1 (asc) or -1 (desc)."""
    params = {"size": size, "sort": sort, "sortDirection": sort_direction}
    if search_after:
        params["searchAfter"] = search_after
    return _get("/apiKeys", tenant=tenant, params=params)


@write_tool
def create_api_key(name: str, expiration_date_ms: int | None = None, tenant: str | None = None) -> str:
    """Create a new API key. expiration_date_ms is an optional epoch-milliseconds expiry.
    The returned secret is shown only once - store it immediately."""
    body = {"name": name}
    if expiration_date_ms is not None:
        body["expirationDate"] = expiration_date_ms
    return _post("/apiKeys", tenant=tenant, body=body)


@read_tool
def get_api_key(key_id: str, tenant: str | None = None) -> str:
    """Get metadata for a single API key by its id (never returns the secret)."""
    return _get(f"/apiKeys/{seg(key_id)}", tenant=tenant)


@destructive_tool
def delete_api_key(key_id: str, tenant: str | None = None) -> str:
    """Revoke and delete an API key by its id."""
    return _delete(f"/apiKeys/{seg(key_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Organization Members
# ---------------------------------------------------------------------------


@read_tool
def list_org_members(tenant: str | None = None) -> str:
    """List all members (users) of the tenant's organization."""
    return _get("/organizations/members", tenant=tenant)


@write_tool
def invite_members(emails: list, first_names: list | None = None, last_names: list | None = None, site_id: str | None = None, tenant: str | None = None) -> str:
    """Invite one or more users by email to join the organization. emails is a list of addresses;
    first_names/last_names are optional parallel lists; site_id (UUID) optionally scopes all invitees
    to a specific site."""
    users = []
    for i, email in enumerate(emails):
        user = {"email": email}
        if first_names and i < len(first_names):
            user["firstName"] = first_names[i]
        if last_names and i < len(last_names):
            user["lastName"] = last_names[i]
        if site_id:
            user["siteId"] = site_id
        users.append(user)
    return _post("/organizations/invitations/batch", tenant=tenant, body={"users": users})


@destructive_tool
def remove_org_member(user_id: str, tenant: str | None = None) -> str:
    """Remove a member from the organization by their userId."""
    return _delete(f"/organizations/members/{seg(user_id)}", tenant=tenant)


@write_tool
def resend_member_invitation(user_id: str, tenant: str | None = None) -> str:
    """Resend the pending invitation email for a not-yet-active member by their userId."""
    return _post(f"/organizations/members/{seg(user_id)}/resend-invitation", tenant=tenant)


# ---------------------------------------------------------------------------
# User Groups
# ---------------------------------------------------------------------------


@read_tool
def list_user_groups(tenant: str | None = None) -> str:
    """List all user groups defined in the organization."""
    return _get("/settings/user-groups", tenant=tenant)


@write_tool
def create_user_group(display_name: str, tenant: str | None = None) -> str:
    """Create a new user group with the given display name."""
    return _post("/settings/user-groups", tenant=tenant, body={"displayName": display_name})


@read_tool
def list_user_group_members(group_id: str, tenant: str | None = None) -> str:
    """List the members of a user group by its groupId."""
    return _get(f"/settings/user-groups/{seg(group_id)}/members", tenant=tenant)


@write_tool
def batch_add_group_members(group_id: str, user_ids: list, tenant: str | None = None) -> str:
    """Add one or more users (by userId) to a user group."""
    return _post(f"/settings/user-groups/{seg(group_id)}/members/batchAdd", tenant=tenant, body={"userIds": user_ids})


# ---------------------------------------------------------------------------
# Site Permissions
# ---------------------------------------------------------------------------


@read_tool
def get_user_site_permissions(user_id: str, tenant: str | None = None) -> str:
    """List every site-level permission grant (WRITER/ADMIN/VIEWER) for a user by their userId."""
    return _get(f"/settings/user/{seg(user_id)}/site-permissions", tenant=tenant)


@destructive_tool
def update_user_site_permission(user_id: str, site_id: str, permission: str | None = None, tenant: str | None = None) -> str:
    """Grant, change, or revoke a user's permission on a site. permission must be one of
    WRITER, ADMIN, VIEWER, or omitted/None to revoke access to that site."""
    valid = {"WRITER", "ADMIN", "VIEWER"}
    if permission is not None and permission not in valid:
        return f'ERROR: permission must be one of {sorted(valid)} or None, got "{permission}"'
    return _put(
        f"/settings/user/{seg(user_id)}/site-permissions/{seg(site_id)}",
        tenant=tenant,
        body={"permission": permission},
        extra_headers={"X-Idempotency-Key": str(uuid.uuid4())},
    )
