import asyncio
import json

import httpx
import pytest
import respx
from fastmcp import Client

from vicarius_v2_mcp.client import _base
from vicarius_v2_mcp.lenient import coerce_arguments, find_problems
from vicarius_v2_mcp.server import mcp

SCHEMA = {
    "properties": {
        "params": {"anyOf": [{"type": "object"}, {"type": "null"}], "default": None},
        "ids": {"type": "array", "items": {"type": "string"}},
        "tenant": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
        "name": {"type": "string"},
        "label": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": None},
        "size": {"type": "integer", "default": 10},
        "kind": {"$ref": "#/$defs/Kind"},
    },
    "required": ["name"],
}


# ---------------------------------------------------------------------------
# coerce_arguments
# ---------------------------------------------------------------------------


def test_json_text_becomes_an_object_or_an_array():
    out = coerce_arguments({"params": '{"severityIn": ["CRITICAL"]}', "ids": '["a", "b"]'}, SCHEMA)
    assert out == {"params": {"severityIn": ["CRITICAL"]}, "ids": ["a", "b"]}


def test_whitespace_around_the_json_is_fine():
    assert coerce_arguments({"params": '  {"a": 1}\n'}, SCHEMA) == {"params": {"a": 1}}


def test_text_that_is_not_json_is_left_for_the_normal_error():
    assert coerce_arguments({"params": "critical please"}, SCHEMA) == {"params": "critical please"}
    assert coerce_arguments({"params": '{"a": '}, SCHEMA) == {"params": '{"a": '}


def test_the_wrong_kind_of_json_is_left_alone():
    assert coerce_arguments({"params": "[1, 2]"}, SCHEMA) == {"params": "[1, 2]"}
    assert coerce_arguments({"ids": '{"a": 1}'}, SCHEMA) == {"ids": '{"a": 1}'}


def test_a_string_the_schema_allows_is_never_reinterpreted():
    # `name` and `label` accept strings, so JSON-looking or "null" text is a real value there.
    args = {"name": '{"a": 1}', "label": "null"}
    assert coerce_arguments(args, SCHEMA) == args


def test_null_text_becomes_none_where_a_string_is_not_allowed():
    assert coerce_arguments({"params": "null"}, SCHEMA) == {"params": None}
    assert coerce_arguments({"params": "None"}, SCHEMA) == {"params": None}


def test_tenant_null_text_means_the_default_tenant():
    # Models told that tenant is optional often write "null" or "None" for it.
    for text in ("null", "None", " NONE "):
        assert coerce_arguments({"tenant": text}, SCHEMA) == {"tenant": None}
    assert coerce_arguments({"tenant": "acme"}, SCHEMA) == {"tenant": "acme"}


def test_values_that_are_not_text_and_unknown_names_are_untouched():
    args = {"params": {"a": 1}, "size": 5, "extra": '{"a": 1}'}
    assert coerce_arguments(args, SCHEMA) == args
    assert coerce_arguments({"kind": '{"a": 1}'}, SCHEMA) == {"kind": '{"a": 1}'}  # a $ref: do not guess


def test_the_input_is_not_modified():
    args = {"params": '{"a": 1}'}
    coerce_arguments(args, SCHEMA)
    assert args == {"params": '{"a": 1}'}


# ---------------------------------------------------------------------------
# find_problems
# ---------------------------------------------------------------------------


def test_no_problems_for_good_arguments():
    assert find_problems("t", {"name": "x", "params": {"a": 1}, "ids": ["a"]}, SCHEMA) == []


def test_unknown_parameter_names_the_real_ones_and_points_at_params():
    (msg,) = find_problems("search_findings", {"name": "x", "severity": "CRITICAL"}, SCHEMA)
    assert "`severity` is not a parameter of search_findings" in msg
    assert "ids, kind, label, name, params, size, tenant" in msg and "inside the `params` object" in msg


def test_missing_required_argument():
    assert find_problems("t", {}, SCHEMA) == ["`name` is required."]


def test_text_where_an_object_or_array_is_needed():
    problems = find_problems("t", {"name": "x", "params": "critical", "ids": "a,b"}, SCHEMA)
    assert any("`params` must be a JSON object" in p and "Got: critical." in p for p in problems)
    assert any("`ids` must be a JSON array" in p for p in problems)


def test_a_long_bad_value_is_cut():
    (msg,) = find_problems("t", {"name": "x", "params": "z" * 500}, SCHEMA)
    assert len(msg) < 200 and "..." in msg


# ---------------------------------------------------------------------------
# Through the real server
# ---------------------------------------------------------------------------


def call(tool, args, route=None):
    async def go():
        async with Client(mcp) as client:
            return await client.call_tool(tool, args, raise_on_error=False)

    with respx.mock(assert_all_called=False) as router:
        found = router.get(f"{_base('acme')}/findings").mock(return_value=httpx.Response(200, json=[{"id": "f-1"}]))
        result = asyncio.run(go())
        return result, found


def test_a_json_string_params_reaches_vrx_as_a_query(vicarius_v2_env):
    result, found = call("search_findings", {"params": '{"severityIn": "CRITICAL", "size": 5}'})
    assert not result.is_error and found.call_count == 1
    url = str(found.calls.last.request.url)
    assert "severityIn=CRITICAL" in url and "size=5" in url


def test_a_normal_object_still_works(vicarius_v2_env):
    result, found = call("search_findings", {"params": {"severityIn": "HIGH"}})
    assert not result.is_error and "severityIn=HIGH" in str(found.calls.last.request.url)


def test_a_top_level_filter_gets_a_helpful_error_and_no_request(vicarius_v2_env):
    result, found = call("search_findings", {"severity": "CRITICAL"})
    text = result.content[0].text
    assert result.is_error and found.call_count == 0
    assert "not a parameter of search_findings" in text and "params, tenant" in text
    assert "pydantic" not in text and "validation error" not in text


def test_a_missing_required_argument_gets_a_helpful_error(vicarius_v2_env):
    result, _ = call("get_finding", {})
    assert result.is_error and "`finding_id` is required" in result.content[0].text


def test_an_unknown_tool_is_reported_by_the_server_as_before(vicarius_v2_env):
    result, _ = call("no_such_tool", {})
    assert result.is_error and "no_such_tool" in result.content[0].text


def test_every_tool_without_required_arguments_passes_the_precheck():
    tools = asyncio.run(mcp.list_tools())
    for tool in tools:
        schema = tool.parameters
        if not schema.get("required"):
            assert find_problems(tool.name, {}, schema) == [], tool.name


def test_tenant_null_text_uses_the_default_tenant_end_to_end(vicarius_v2_env):
    result, found = call("search_findings", {"params": {"size": 1}, "tenant": "null"})
    assert not result.is_error and found.call_count == 1  # reached the default tenant (acme)
