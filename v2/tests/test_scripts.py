import json

import httpx
import respx

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.tools_scripts import (
    search_private_scripts,
    create_private_script,
    search_public_scripts,
)


@respx.mock
def test_search_and_create_private_scripts(vicarius_v2_env):
    respx.post(f"{_base('acme')}/privateScripts/search").mock(return_value=httpx.Response(200, json=[{"id": "sc-1"}]))
    respx.post(f"{_base('acme')}/privateScripts").mock(return_value=httpx.Response(200, json={"id": "sc-2"}))
    assert json.loads(search_private_scripts(filters={"name": "cleanup"}))[0]["id"] == "sc-1"
    assert json.loads(create_private_script({"name": "cleanup", "type": "POWERSHELL"}))["id"] == "sc-2"


@respx.mock
def test_search_public_scripts(vicarius_v2_env):
    respx.post(f"{_base('acme')}/publicScripts/search").mock(return_value=httpx.Response(200, json=[{"id": "pub-1"}]))
    assert json.loads(search_public_scripts(filters={"cveIds": ["CVE-2024-1"]}))[0]["id"] == "pub-1"
