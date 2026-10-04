"""A fake vRx backend for the evaluation harness: canned JSON, sized like real replies."""

from __future__ import annotations

import json
import re

import httpx

HOST = "acme.vicarius.cloud"
_SEVERITIES = ["CRITICAL"] * 18 + ["HIGH"] * 12 + ["MEDIUM"] * 10


def _finding(i: int) -> dict:
    """About as wide as a real finding in a search reply (about 25 fields)."""
    return {
        "id": f"f-{i}", "findingId": f"CVE-2025-{1000 + i}", "findingType": "CVE", "findingTitle": None,
        "assetId": f"a-{70 + i % 20}", "assetName": f"HOST-{i % 20:02d}",
        "assetAttributes": [{"key": "os_family", "source": "agent", "value": "windows", "normalizedValue": None}],
        "assetOsFromAttributes": "Microsoft Windows Server 2022 Standard", "assetOsVersionFromAttributes": "10.0.20348",
        "productId": f"p-{i}", "productName": "Windows Server 2022", "productType": "OPERATING_SYSTEM",
        "publisherId": "pub-1", "publisherName": "Microsoft", "platformInformationId": "plat-1",
        "status": "ACTIVE", "severity": _SEVERITIES[i % len(_SEVERITIES)],
        "epssScore": round(0.9 - i * 0.01, 4), "cvssBaseScore": 9.8 if i % 2 == 0 else 7.5,
        "exploitationStatus": "ACTIVE" if i % 3 == 0 else "PUBLIC_POC", "inCisaKev": i % 2 == 0,
        "firstSeen": 1790000000000 + i, "lastSeen": 1790900000000 + i, "riskScore": round(85.0 - i * 0.5, 2),
        "riskScoreUpdatedAt": 1790900000000, "patchlessProtectionMode": None, "paginationToken": f"tok-{i}",
    }


FINDINGS = [_finding(i) for i in range(40)]

ASSET = {
    "id": "a-77", "name": "WIN-DC01", "type": "MANAGED", "siteId": "s-1", "siteName": "Global",
    "osName": "Microsoft Windows Server 2019", "activityStatus": "ACTIVE", "riskScore": 82.5,
    "assetGroupIds": ["g-1"], "attributes": [{"key": "os_family", "value": "windows"}],
}


def _route(method: str, path: str):
    """Return (status, body) for an API path below /api."""
    if method == "GET" and path == "/sites":
        return [{"id": "s-1", "name": "Global"}, {"id": "s-2", "name": "Branch office"}]
    if method == "GET" and path == "/findings":
        return FINDINGS
    if method == "GET" and (m := re.fullmatch(r"/findings/(f-\d+)", path)):
        n = int(m.group(1)[2:])
        return {**_finding(n if n < len(FINDINGS) else 0), "findingId": "CVE-2025-1000",
                "vulnerabilityInformation": {"id": "CVE-2025-1000", "name": "A remote code execution flaw."},
                "evidences": [], "states": [{"state": "ACTIVE"}]}
    if method == "GET" and path == "/findings/severity-distribution":
        return {"CRITICAL": 18, "HIGH": 7, "MEDIUM": 120, "LOW": 240}
    if method == "GET" and path == "/findings/grouped-by-vulnerability":
        return [{"findingId": f"CVE-2025-{1000 + i}", "assetCount": 40 - i, "severity": "CRITICAL"} for i in range(10)]
    if method == "GET" and path == "/asset/a-77":
        return ASSET
    if method == "POST" and path == "/assets/search":
        return [ASSET]
    if method == "GET" and path == "/assetGroups":
        return [{"id": "g-1", "name": "Servers", "type": "STATIC", "assetCount": 12},
                {"id": "g-2", "name": "Workstations", "type": "DYNAMIC", "assetCount": 31}]
    if method == "GET" and path == "/organizations/members":
        return [{"id": "u-1", "email": "admin@example.com", "role": "ADMIN"}]
    return []  # anything else: an empty, valid reply


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path.removeprefix("/api")
    body = _route(request.method, path)
    return httpx.Response(200, content=json.dumps(body), headers={"content-type": "application/json"})
