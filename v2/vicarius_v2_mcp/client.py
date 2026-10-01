from __future__ import annotations

import json
import os
import re
import tempfile
from urllib.parse import quote

import httpx

TIMEOUT = httpx.Timeout(30.0, connect=5.0)

DEFAULT_TENANTS_FILE = os.path.expanduser("~/.config/vicarius-v2-mcp/tenants.json")
DEFAULT_HOST = "vicarius.cloud"

# A bare hostname with an optional port - no scheme, path, query, or credentials - so a tenant's
# API key can only ever be sent to the host named here, over HTTPS.
_HOST_RE = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*(?::[0-9]{1,5})?$")


def normalize_host(host: str | None) -> str:
    """Accepts "vicarius.cloud", "https://vicarius.cloud/" or "vicarius.cloud/api" and returns the
    bare hostname. Raises ValueError for anything that isn't a plain hostname."""
    value = (host or DEFAULT_HOST).strip()
    value = re.sub(r"^https://", "", value, flags=re.IGNORECASE).rstrip("/")
    if value.lower().endswith("/api"):
        value = value[: -len("/api")]
    if not _HOST_RE.fullmatch(value):
        raise ValueError(f'Invalid host "{host}": expected a bare hostname such as "{DEFAULT_HOST}"')
    return value.lower()


def seg(value: object) -> str:
    """Percent-encode a value for use as a single URL path segment, so an id like "../apiKeys"
    can't redirect a request to a different endpoint. Empty, "." and ".." are refused because
    they would still collapse onto the parent path."""
    text = str(value).strip()
    if text in ("", ".", ".."):
        raise ValueError(f"Invalid id {str(value)!r}")
    return quote(text, safe="")


def is_vicarius_host(host: str) -> bool:
    name = host.split(":")[0]
    return name == DEFAULT_HOST or name.endswith("." + DEFAULT_HOST)


def _tenants_file_path() -> str:
    return os.environ.get("VICARIUS_V2_TENANTS_FILE", DEFAULT_TENANTS_FILE)


def _load_tenants_file() -> dict | None:
    """Reads the tenants file fresh on every call (no caching) so tenants added at runtime via
    add_configured_tenant/remove_configured_tenant take effect on the very next tool call."""
    path = _tenants_file_path()
    if not os.path.exists(path):
        return None
    # utf-8-sig tolerates the byte-order mark some Windows editors add.
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object mapping tenant name to {{api_key, host}}")
    return data


def _tenants_or_empty() -> dict:
    """Like _tenants() but returns {} instead of raising when nothing is configured yet -
    used for listing, so list_configured_tenants never errors even with zero tenants."""
    file_data = _load_tenants_file()
    if file_data is not None:
        return file_data
    raw = os.environ.get("VICARIUS_V2_TENANTS", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _tenants() -> dict:
    data = _tenants_or_empty()
    if not data:
        raise RuntimeError(
            f"No tenants configured. Add one at {_tenants_file_path()} (JSON object mapping "
            f"tenant name to {{api_key, host}}), use the add_configured_tenant tool, or set "
            f"VICARIUS_V2_TENANTS."
        )
    return data


def _write_tenants_file(data: dict) -> None:
    """Atomically replace the tenants file. The temp file is created owner-only (0600) from the
    start, so the API keys are never readable by other users, even briefly."""
    path = _tenants_file_path()
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tenants-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def save_tenant(name: str, api_key: str, host: str = DEFAULT_HOST, overwrite: bool = False) -> None:
    name = name.strip()
    api_key = api_key.strip()
    if not name:
        raise ValueError("Tenant name must not be empty")
    if not api_key:
        raise ValueError("API key must not be empty")
    data = _load_tenants_file()
    if data is None:
        if os.environ.get("VICARIUS_V2_TENANTS", "").strip():
            # Writing a file would silently hide every tenant defined in the env var.
            raise ValueError(
                "Tenants are configured through the VICARIUS_V2_TENANTS environment variable; "
                f"add the tenant there, or move them into {_tenants_file_path()} first"
            )
        data = {}
    if name in data and not overwrite:
        raise ValueError(f'Tenant "{name}" already exists; pass overwrite=True to replace it')
    data[name] = {"api_key": api_key, "host": normalize_host(host)}
    _write_tenants_file(data)


def remove_tenant(name: str) -> bool:
    data = _load_tenants_file()
    if not data or name not in data:
        return False
    del data[name]
    _write_tenants_file(data)
    return True


def _resolve_tenant(tenant: str | None) -> tuple[str, str, str]:
    """Returns (tenant_name, host, api_key)."""
    tenants = _tenants()
    name = tenant
    if not name:
        name = os.environ.get("VICARIUS_V2_DEFAULT_TENANT", "").strip() or None
    if not name:
        if len(tenants) == 1:
            name = next(iter(tenants))
        else:
            raise RuntimeError(
                f"No tenant specified and no VICARIUS_V2_DEFAULT_TENANT set. "
                f"Configured tenants: {sorted(tenants)}"
            )
    if name not in tenants:
        raise RuntimeError(f'Unknown tenant "{name}". Configured tenants: {sorted(tenants)}')
    cfg = tenants[name]
    api_key = cfg.get("api_key", "").strip() if isinstance(cfg, dict) else ""
    if not api_key:
        raise RuntimeError(f'Tenant "{name}" is missing an "api_key" value')
    try:
        host = normalize_host(cfg.get("host"))
    except ValueError as exc:
        raise RuntimeError(f'Tenant "{name}": {exc}') from None
    return name, host, api_key


def list_configured_tenant_names() -> list[str]:
    return sorted(_tenants_or_empty())


def _base(tenant: str | None) -> str:
    _, host, _ = _resolve_tenant(tenant)
    return f"https://{host}/api"


def _request(method: str, path: str, tenant: str | None, params: dict | None = None, body: object = None, extra_headers: dict | None = None) -> str:
    try:
        _, host, api_key = _resolve_tenant(tenant)
        headers = {"X-Api-Key": api_key, **(extra_headers or {})}
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.request(
                method,
                f"https://{host}/api{path}",
                headers=headers,
                params=params,
                json=body,
            )
        if not r.is_success:
            return f"ERROR {r.status_code}: {r.text}"
        if not r.text:
            return json.dumps({"ok": True}, indent=2)
        content_type = r.headers.get("content-type", "")
        if "application/json" not in content_type:
            return json.dumps(
                {"contentType": content_type, "contentLength": len(r.content),
                 "note": "Non-JSON response body not returned inline."},
                indent=2,
            )
        return json.dumps(r.json(), indent=2)
    except Exception as exc:
        return f"ERROR: {exc}"


def _get(path: str, tenant: str | None = None, params: dict | None = None) -> str:
    return _request("GET", path, tenant, params=params)


def _post(path: str, tenant: str | None = None, params: dict | None = None, body: object = None) -> str:
    return _request("POST", path, tenant, params=params, body=body)


def _put(path: str, tenant: str | None = None, params: dict | None = None, body: object = None, extra_headers: dict | None = None) -> str:
    return _request("PUT", path, tenant, params=params, body=body, extra_headers=extra_headers)


def _patch(path: str, tenant: str | None = None, params: dict | None = None, body: object = None) -> str:
    return _request("PATCH", path, tenant, params=params, body=body)


def _delete(path: str, tenant: str | None = None, params: dict | None = None) -> str:
    return _request("DELETE", path, tenant, params=params)
