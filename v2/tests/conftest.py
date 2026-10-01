import json

import pytest


@pytest.fixture(autouse=True)
def vicarius_v2_env(monkeypatch, tmp_path):
    # Point the tenants file at a path that doesn't exist, so _tenants() falls back to the
    # VICARIUS_V2_TENANTS env var below - this isolates tests from any real tenants file on
    # the developer's machine (e.g. ~/.config/vicarius-v2-mcp/tenants.json).
    monkeypatch.setenv("VICARIUS_V2_TENANTS_FILE", str(tmp_path / "unused-tenants.json"))
    tenants = {
        "acme": {"api_key": "dummy-acme", "host": "acme.vicarius.cloud"},
        "beta": {"api_key": "dummy-beta", "host": "vicarius.cloud"},
    }
    monkeypatch.setenv("VICARIUS_V2_TENANTS", json.dumps(tenants))
    monkeypatch.setenv("VICARIUS_V2_DEFAULT_TENANT", "acme")
