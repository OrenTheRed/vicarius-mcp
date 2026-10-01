from __future__ import annotations

from .app import destructive_tool, read_tool, write_tool
from .client import _delete, _get, _post, _put, seg

# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


@read_tool
def list_sites(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search sites. params is an optional dict of query filters, e.g. name, nameIn, global,
    draft, siteAgentIdsIn, namedTargetIdsIn, riskScoreRange.min/max, sort, sortDirection,
    searchAfter, size (default 10), fields."""
    return _get("/sites", tenant=tenant, params=params)


@write_tool
def create_site(payload: dict, tenant: str | None = None) -> str:
    """Create a new site. payload must include "name"; optional: description, global, draft, settings."""
    return _post("/sites", tenant=tenant, body=payload)


@read_tool
def get_site(site_id: str, tenant: str | None = None) -> str:
    """Get a single site by its id (UUID)."""
    return _get(f"/sites/{seg(site_id)}", tenant=tenant)


@destructive_tool
def update_site(site_id: str, payload: dict, tenant: str | None = None) -> str:
    """Update a site by id. payload is the full/partial Site object (name, description, settings, etc.)."""
    return _put(f"/sites/{seg(site_id)}", tenant=tenant, body=payload)


@destructive_tool
def delete_site(site_id: str, tenant: str | None = None) -> str:
    """Delete a site by its id (UUID)."""
    return _delete(f"/sites/{seg(site_id)}", tenant=tenant)


# ---------------------------------------------------------------------------
# Site Agents
# ---------------------------------------------------------------------------


@read_tool
def list_site_agents(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search site agents (the assets that perform scanning for a site). params supports
    siteId, name, modules (radarExternal/radarInternal/cis/proxy), sort, sortDirection, searchAfter, size."""
    return _get("/site-agents", tenant=tenant, params=params)


@write_tool
def create_site_agent(payload: dict, tenant: str | None = None) -> str:
    """Register an asset as a site agent. payload: name, siteId (UUID), modules (dict of
    radarExternal/radarInternal/cis/proxy booleans). The asset must be a managed Linux asset."""
    return _post("/site-agents", tenant=tenant, body=payload)


# ---------------------------------------------------------------------------
# Named Targets
# ---------------------------------------------------------------------------


@read_tool
def list_named_targets(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search named targets (reusable sets of network addresses). params supports name,
    targetSiteIdsIn, sort, sortDirection, searchAfter, size."""
    return _get("/named-targets", tenant=tenant, params=params)


@write_tool
def create_named_target(payload: dict, tenant: str | None = None) -> str:
    """Create a named target. payload: name, description, isNetworkDevice, addressSpecs (list of
    {included, addressType: CIDR|IP_RANGE|SINGLE_IP|FQDN, addressValue}), targetSiteIds, credentialsIds."""
    return _post("/named-targets", tenant=tenant, body=payload)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


@read_tool
def list_credentials(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search stored scan credentials (metadata only, secrets never returned). params supports
    name, type (WINDOWS_ADMIN/LINUX_UNIX_MAC/AWS_IAM/SNMP_VERSION_3/WEB_APPLICATION/HTTP),
    targetSiteIdsIn, sort, sortDirection, searchAfter, size."""
    return _get("/credentials", tenant=tenant, params=params)


@write_tool
def create_credential(payload: dict, tenant: str | None = None) -> str:
    """Create a scan credential. payload requires name, type (WINDOWS_ADMIN/LINUX_UNIX_MAC/AWS_IAM/
    SNMP_VERSION_3/WEB_APPLICATION/HTTP); optional siteId, targetSiteIds, rotationPolicy, and
    attributes (username/domain/password/privateKey/accessKey/passphrase/etc. depending on type)."""
    return _post("/credentials", tenant=tenant, body=payload)


# ---------------------------------------------------------------------------
# Scanner Configurations
# ---------------------------------------------------------------------------


@read_tool
def list_scanner_configurations(params: dict | None = None, tenant: str | None = None) -> str:
    """List/search scanner configurations. params supports sort, sortDirection, searchAfter, size."""
    return _get("/scannerConfiguration", tenant=tenant, params=params)


@write_tool
def create_scanner_configuration(payload: dict, tenant: str | None = None) -> str:
    """Create a scanner configuration. payload: settings (dict of string key/value settings)."""
    return _post("/scannerConfiguration", tenant=tenant, body=payload)
