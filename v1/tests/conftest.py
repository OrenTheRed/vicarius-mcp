import pytest


@pytest.fixture(autouse=True)
def vicarius_env(monkeypatch):
    monkeypatch.setenv("VICARIUS_DASHBOARD", "testdash")
    monkeypatch.setenv("VICARIUS_API_KEY", "dummy")
