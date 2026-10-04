from __future__ import annotations

import json

from . import jev
from .app import read_tool
from .client import _get, seg

# ---------------------------------------------------------------------------
# Optional Jev urgency assessment (see jev.py). Registered only when the operator turned it on.
# ---------------------------------------------------------------------------


def _load(text: str) -> dict:
    if text.startswith("ERROR"):
        raise jev.JevError(text)
    try:
        data = json.loads(text)
    except ValueError:
        raise jev.JevError("vRx returned a reply that is not JSON") from None
    return data if isinstance(data, dict) else {}


def _group_names(asset: dict, tenant: str | None) -> list:
    """Names of the asset groups the asset belongs to. They only feed labels computed in code.
    Failing to read them is not an error: the assessment goes ahead without them."""
    try:
        asset_id = asset.get("id")
        ids = set(asset.get("assetGroupIds") or [])
        groups = json.loads(_get("/assetGroups", tenant=tenant, params={"size": 200}))
        if not isinstance(groups, list):
            return []
        return [
            g["name"] for g in groups
            if isinstance(g, dict) and g.get("name") and (g.get("id") in ids or asset_id in (g.get("assetIds") or []))
        ][: jev.MAX_GROUPS]
    except Exception:
        return []


def assess_finding_urgency(finding_id: str, preview: bool = False, tenant: str | None = None) -> str:
    """Judge how urgent one finding is on its own asset, using TypeSafe's Jev model. This adds a
    judgment vRx's numbers do not capture (the asset's role, and a hint that its name or groups mark
    it as non-production). It does not replace vRx's severity, CVSS, EPSS, CISA KEV, exploit status or risk
    score, which are returned unchanged. The answer is advice: a disposition (DEFER, STANDARD,
    ACCELERATED, EMERGENCY or REVIEW) with probabilities. Treat REVIEW or low confidence as "a
    person must decide". Set preview=true to see exactly what would be sent to TypeSafe without
    sending it. VICARIUS_V2_JEV_PRIVACY decides whether machine names, IP addresses, CVE ids and
    software names are hidden from TypeSafe. With weak exploit evidence (no CISA KEV listing, no
    exploit tags, low or medium EPSS) the disposition is capped at STANDARD, and the output says so."""
    try:
        mode = jev.privacy_mode()
        finding = _load(_get(f"/findings/{seg(finding_id)}", tenant=tenant))
        asset_id = jev.find_value(finding, ["assetId"])
        asset = _load(_get(f"/asset/{seg(asset_id)}", tenant=tenant)) if asset_id else {}
        state = jev.build_state(finding, asset, mode, _group_names(asset, tenant))
        result = {
            "finding_id": finding_id,
            "privacy_mode": mode,
            "vrx": jev.extract_vrx_numbers(finding),
            "sent_to_typesafe": state,
        }
        if preview:
            result["preview_only"] = True
            return json.dumps(result, indent=2)
        result["jev"] = jev.apply_guard(jev.summarize(jev.call_jev(state)), state["vulnerability"])
        result["note"] = "Advice only. It does not change anything in vRx."
        return json.dumps(result, indent=2)
    except Exception as exc:
        return f"ERROR: {exc}"


if jev.enabled():
    read_tool(assess_finding_urgency)
