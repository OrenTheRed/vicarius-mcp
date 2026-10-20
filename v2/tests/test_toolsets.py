import asyncio
import json
import os
import subprocess
import sys

import pytest

from vicarius_v2_mcp.server import mcp
from vicarius_v2_mcp.toolsets import CORE, groups


def tools_in_process():
    return asyncio.run(mcp.list_tools())


def listed(**env) -> list:
    """Tool names a fresh server offers with these settings (the filters apply at import)."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("VICARIUS", "TYPESAFE"))}
    clean.update(env)
    code = ("import asyncio, json\nfrom vicarius_v2_mcp.server import mcp\n"
            "print(json.dumps(sorted(t.name for t in asyncio.run(mcp.list_tools()))))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=clean)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip().splitlines()[-1])
    return json.loads(out.stdout.strip().splitlines()[-1])


ALL = sorted(t.name for t in tools_in_process())
GROUP_OF = {t.name: next(tag for tag in t.tags if tag.startswith("toolset:")).removeprefix("toolset:") for t in tools_in_process()}


def test_every_tool_belongs_to_exactly_one_known_group():
    known = groups()
    for tool in tools_in_process():
        groups_of_tool = [tag for tag in tool.tags if tag.startswith("toolset:")]
        assert len(groups_of_tool) == 1, tool.name
        assert groups_of_tool[0].removeprefix("toolset:") in known, tool.name
    assert set(GROUP_OF.values()) == set(known)  # the list of groups is the tools' own tags


def test_not_setting_it_or_saying_all_offers_every_tool():
    assert listed() == ALL
    assert listed(VICARIUS_V2_TOOLSETS="all") == ALL
    assert listed(VICARIUS_V2_TOOLSETS="core,all") == ALL
    assert len(ALL) >= 115


def test_core_offers_the_core_tools_and_only_read_tools():
    names = listed(VICARIUS_V2_TOOLSETS="core")
    assert names == sorted(n for n in CORE if n in ALL)  # assess_finding_urgency only exists when Jev is on
    by_name = {t.name: t for t in tools_in_process()}
    assert all(by_name[n].annotations.readOnlyHint for n in names)
    assert 10 <= len(names) <= 25


def test_core_includes_the_urgency_tool_when_jev_is_enabled():
    names = listed(VICARIUS_V2_TOOLSETS="core", VICARIUS_V2_JEV="true", TYPESAFE_API_KEY="dummy-key")
    assert "assess_finding_urgency" in names


def test_groups_can_be_chosen_and_mixed():
    findings_sites = listed(VICARIUS_V2_TOOLSETS="findings,sites")
    assert findings_sites and {GROUP_OF[n] for n in findings_sites} == {"findings", "sites"}
    assert findings_sites == sorted(n for n in ALL if GROUP_OF[n] in ("findings", "sites"))
    mixed = listed(VICARIUS_V2_TOOLSETS="core,compliance")
    assert set(mixed) == {n for n in ALL if n in CORE or GROUP_OF[n] == "compliance"}
    assert listed(VICARIUS_V2_TOOLSETS=" Core  Compliance ") == mixed  # spaces and case do not matter


def test_an_unknown_toolset_stops_the_server_with_a_clear_message():
    with pytest.raises(RuntimeError, match='Unknown toolset "finding"'):
        listed(VICARIUS_V2_TOOLSETS="finding")


def test_read_only_mode_still_hides_write_tools_inside_a_chosen_group():
    # An allowlist applied after read-only mode would show the write tools again. It must not.
    sites = listed(VICARIUS_V2_TOOLSETS="sites")
    sites_read_only = listed(VICARIUS_V2_TOOLSETS="sites", VICARIUS_READ_ONLY="true")
    assert "create_site" in sites and "delete_site" in sites
    assert "list_sites" in sites_read_only
    assert not {"create_site", "delete_site", "update_site"} & set(sites_read_only)
    by_name = {t.name: t for t in tools_in_process()}
    assert all(by_name[n].annotations.readOnlyHint for n in sites_read_only)


def test_the_tool_list_stays_within_its_size_budget():
    """Regression guard for the cost of the tool list in every conversation (about 4 characters a token)."""
    def size(names):
        return sum(len(json.dumps({"n": t.name, "d": t.description, "s": t.parameters}))
                   for t in tools_in_process() if t.name in names)

    assert size(set(ALL)) < 64_000        # about 16,000 tokens; measured 60,700 with the 1.6.0 tools
    assert size(set(CORE)) < 11_000       # about 2,750 tokens; measured 8,600


def test_the_readme_lists_exactly_the_groups_that_exist():
    import re
    from pathlib import Path
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    row = next(line for line in readme.splitlines() if line.startswith("| a group name |"))
    listed_in_readme = set(re.findall(r"`([a-z]+)`", row.split("|")[2]))
    # "jev" exists only while Jev is switched on, which it is not in this process.
    assert listed_in_readme == set(groups()) | {"jev"}


def test_a_bad_toolset_ends_startup_with_one_clear_line_and_no_traceback():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VICARIUS", "TYPESAFE"))}
    env["VICARIUS_V2_TOOLSETS"] = "finding"
    out = subprocess.run([sys.executable, "-c", "import vicarius_v2_mcp.server"], capture_output=True, text=True, env=env)
    assert out.returncode != 0 and "Traceback" not in out.stderr
    assert out.stderr.strip().startswith("vicarius-v2-mcp: Unknown toolset") and "findings" in out.stderr


def test_the_new_read_tools_are_read_only_and_in_the_right_groups():
    by_name = {t.name: t for t in tools_in_process()}
    expected = {"list_risk_tags": "findings", "list_patch_group_patches": "patches",
                "list_software_group_software": "assets", "list_software_versions": "assets"}
    for name, group in expected.items():
        assert by_name[name].annotations.readOnlyHint is True, name
        assert GROUP_OF[name] == group, name
        assert name not in CORE, name  # core stays a small set of the usual questions


# ---------------------------------------------------------------------------
# The new read tools: tenant routing and error replies, and the counts the docs state
# ---------------------------------------------------------------------------

NEW_READ_TOOLS = [
    ("list_risk_tags", {}, "/v2/risk-tags"),
    ("list_patch_group_patches", {"patch_group_id": "pg-1"}, "/patchGroups/pg-1/patches/view"),
    ("list_software_group_software", {"software_group_id": "sg-1"}, "/softwareGroups/sg-1/software/view"),
    ("list_software_versions", {"product_id": "p-1"}, "/software/p-1/versions"),
]


@pytest.mark.parametrize("name, args, path", NEW_READ_TOOLS)
def test_new_read_tools_use_the_chosen_tenant_and_surface_errors(vicarius_v2_env, name, args, path):
    import httpx
    import respx
    from fastmcp import Client
    from vicarius_v2_mcp.client import _base

    async def call(**extra):
        async with Client(mcp) as client:
            return (await client.call_tool(name, {**args, **extra}, raise_on_error=False)).content[0].text

    with respx.mock(assert_all_called=False) as router:
        acme = router.get(f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json=[]))
        beta = router.get(f"{_base('beta')}{path}").mock(return_value=httpx.Response(200, json=[{"ok": 1}]))
        asyncio.run(call())                       # the default tenant
        asyncio.run(call(tenant="beta"))          # an explicit tenant
        assert acme.call_count == 1 and beta.call_count == 1
        beta.mock(return_value=httpx.Response(403, text="Forbidden"))
        assert asyncio.run(call(tenant="beta")).startswith("ERROR 403")   # a key without permission is reported
        beta.mock(return_value=httpx.Response(404, json={"error": "not found"}))
        assert asyncio.run(call(tenant="beta")).startswith("ERROR 404")


def test_the_tool_counts_in_the_docs_match_the_tools():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    tools = tools_in_process()
    total = len(tools)
    read_only = sum(1 for t in tools if t.annotations.readOnlyHint)
    destructive = sum(1 for t in tools if t.annotations.destructiveHint)
    write = total - read_only - destructive

    v2 = (root / "v2/README.md").read_text(encoding="utf-8")
    assert f"**{total} tools** ({read_only} read-only, {write} write, {destructive} destructive)" in v2
    assert f"expose only the {read_only} read-only tools" in v2
    assert f"{total} tools. A model with a small context window" in v2

    top = (root / "README.md").read_text(encoding="utf-8")
    v1_total = int(re.search(r"\]\(v1/README\.md\)\s*\|[^|]*\|\s*(\d+)\s*\|", top).group(1))
    assert re.search(rf"\]\(v2/README\.md\)\s*\|[^|]*\|\s*{total}\s*\|", top)
    assert f"**{total + v1_total} tools** across both servers" in top
    assert f"{read_only} of {total} for v2" in top
    assert f"multi-tenant ({total} tools)" in top


# ---------------------------------------------------------------------------
# 1.6.0: read tools for routes the vRx web app calls, each run against a live tenant
# ---------------------------------------------------------------------------

NEW_READ_TOOLS_1_6 = [
    ("get_finding_patchless_protection", {"finding_id": "f-1"}, "GET", "/findings/f-1/patchless-protection-eligibility", "findings"),
    ("get_finding_patchless_protection", {"finding_id": "f-1", "view": "affected_findings_count"}, "GET", "/findings/f-1/patchless-protection-affected-findings-count", "findings"),
    ("search_patchless_protections", {}, "POST", "/patchless-protections/search", "findings"),
    ("count_patchless_protections", {}, "POST", "/patchless-protections/count", "findings"),
    ("list_patchless_protection_events", {"protection_id": "pp-1"}, "GET", "/patchless-protections/pp-1/events", "findings"),
    ("search_available_patches_grouped", {}, "POST", "/availablePatches/searchGroupedByPatchDefinition", "patches"),
    ("search_patches_for_static_group", {}, "GET", "/patchGroups/static/patches/search", "patches"),
    ("get_software_version", {"product_id": "p-1", "platform_information_id": "pi-1"}, "GET", "/software/p-1/version/pi-1", "assets"),
    ("search_software_for_static_group", {}, "GET", "/softwareGroups/static/software/search", "assets"),
    ("list_scan_profile_options", {"kind": "perspectives"}, "GET", "/scanProfile/perspectives", "scanning"),
]


@pytest.mark.parametrize("name, args, method, path, group", NEW_READ_TOOLS_1_6)
def test_1_6_read_tools_are_read_only_route_to_the_tenant_and_surface_errors(vicarius_v2_env, name, args, method, path, group):
    import httpx
    import respx
    from fastmcp import Client
    from vicarius_v2_mcp.client import _base

    tool = {t.name: t for t in tools_in_process()}[name]
    assert tool.annotations.readOnlyHint is True and GROUP_OF[name] == group and name not in CORE

    async def call(**extra):
        async with Client(mcp) as client:
            return (await client.call_tool(name, {**args, **extra}, raise_on_error=False)).content[0].text

    with respx.mock(assert_all_called=False) as router:
        acme = router.route(method=method, url=f"{_base('acme')}{path}").mock(return_value=httpx.Response(200, json=[]))
        beta = router.route(method=method, url=f"{_base('beta')}{path}").mock(return_value=httpx.Response(200, json=[{"ok": 1}]))
        asyncio.run(call())
        asyncio.run(call(tenant="beta"))
        assert acme.call_count == 1 and beta.call_count == 1
        beta.mock(return_value=httpx.Response(403, text="Forbidden"))
        assert asyncio.run(call(tenant="beta")).startswith("ERROR 403")


def test_get_my_access_combines_three_routes_and_passes_errors_through(vicarius_v2_env):
    import httpx
    import respx
    from vicarius_v2_mcp.client import _base
    from vicarius_v2_mcp.tools_tenants import get_my_access

    assert GROUP_OF["get_my_access"] == "tenants" and "get_my_access" not in CORE
    with respx.mock() as router:
        router.get(f"{_base('acme')}/me").mock(return_value=httpx.Response(200, json={"userId": "u-1"}))
        router.get(f"{_base('acme')}/me/site").mock(return_value=httpx.Response(200, json={"name": "Global Site"}))
        router.get(f"{_base('acme')}/me/site/permissions").mock(return_value=httpx.Response(403, text="Forbidden"))
        result = json.loads(get_my_access())
    assert result["user"]["userId"] == "u-1" and result["site"]["name"] == "Global Site"
    assert result["sitePermissions"].startswith("ERROR 403")


def test_search_available_patches_grouped_sends_filters_and_paging(vicarius_v2_env):
    import httpx
    import respx
    from vicarius_v2_mcp.client import _base
    from vicarius_v2_mcp.tools_patches import search_available_patches_grouped

    with respx.mock() as router:
        route = router.post(f"{_base('acme')}/availablePatches/searchGroupedByPatchDefinition").mock(
            return_value=httpx.Response(200, json=[{"patchIdentifier": "KB1", "cveStrings": ["CVE-1"]}]))
        rows = json.loads(search_available_patches_grouped({"operatingSystemFamilyIn": ["WINDOWS"]}, {"size": 2, "from": 2}))
    request = route.calls.last.request
    assert rows[0]["cveStrings"] == ["CVE-1"]
    assert json.loads(request.content) == {"operatingSystemFamilyIn": ["WINDOWS"]}
    assert request.url.params["size"] == "2" and request.url.params["from"] == "2"


def test_a_finding_id_cannot_escape_its_path_segment(vicarius_v2_env):
    import httpx
    import respx
    from vicarius_v2_mcp.client import _base
    from vicarius_v2_mcp.tools_vulnerabilities import get_finding_patchless_protection

    with respx.mock() as router:
        route = router.get(url__startswith=f"{_base('acme')}/findings/").mock(return_value=httpx.Response(200, json={}))
        get_finding_patchless_protection("../apiKeys")
    assert route.calls.last.request.url.raw_path.startswith(b"/api/findings/..%2FapiKeys/patchless")
