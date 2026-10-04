import asyncio
import json
import os

import httpx
import pytest
import respx
from fastmcp import Client

from evals import mock_vrx
from evals.env import isolate_environment
from evals.harness import (ModelError, OpenAICompatibleModel, Reply, Result, failed_result, format_table, run_task,
                           summarize, to_openai_tools)
from evals.tasks import CORE, TASKS
from vicarius_v2_mcp.server import mcp


class ScriptedModel:
    """Replays prepared replies, so the scoring can be tested without a real model."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages, tools, temperature):
        self.calls.append(messages)
        return self.replies.pop(0)


def call(name, arguments, content=None):
    return Reply(content, [{"id": "c1", "name": name, "arguments": arguments}], "tool_calls", 100, 0.5)


def text(content):
    return Reply(content, [], "stop", 120, 0.4)


def run(task_id, model, tool_names=None, instructions=""):
    task = next(t for t in TASKS if t.id == task_id)

    async def go():
        async with Client(mcp) as client:
            tools = [t for t in await client.list_tools() if tool_names is None or t.name in tool_names]
            schemas = {t.name: t.inputSchema for t in tools}
            with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
                router.route(host=mock_vrx.HOST).mock(side_effect=mock_vrx.handler)
                return await run_task(client, model, "scripted", "all", to_openai_tools(tools), schemas, task, 0, 0.0, instructions)

    return asyncio.run(go())


def test_every_task_names_real_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert len({t.id for t in TASKS}) == len(TASKS)
    for task in TASKS:
        assert task.accept, task.id
        assert set(task.accept) <= names, task.id
    assert set(CORE) - {"assess_finding_urgency"} <= names  # that one exists only when Jev is on


def test_core_set_contains_a_tool_for_every_task():
    for task in TASKS:
        assert set(task.accept) & set(CORE), task.id


def test_right_call_and_right_answer_pass():
    model = ScriptedModel(call("list_sites", "{}"), text("You have the site Global and Branch office."))
    r = run("list_sites", model)
    assert (r.chose, r.tool_ok, r.args_ok, r.answer_ok) == ("list_sites", True, True, True)
    assert r.tool_result_chars > 0 and r.prompt_tokens == 100 and r.seconds == 0.9
    assert model.calls[1][-1]["role"] == "tool" and "Global" in model.calls[1][-1]["content"]


def test_wrong_answer_fails_only_the_answer():
    r = run("list_sites", ScriptedModel(call("list_sites", "{}"), text("I found nothing.")))
    assert r.args_ok is True and r.answer_ok is False


def test_follow_up_tool_call_instead_of_an_answer_fails():
    r = run("list_sites", ScriptedModel(call("list_sites", "{}"), call("list_sites", "{}")))
    assert r.answer_ok is False


def test_wrong_tool_is_scored_and_not_executed():
    model = ScriptedModel(call("list_organizations", "{}"))
    r = run("critical_findings_tenant", model)
    assert (r.chose, r.tool_ok, r.args_ok, r.answer_ok) == ("list_organizations", False, False, None)
    assert r.server_accepted is True  # the server took the call; it was just the wrong tool for the task
    assert len(model.calls) == 1


def test_no_tool_call_is_recorded():
    r = run("list_sites", ScriptedModel(text("Sure, here are some sites...")))
    assert r.chose is None and r.n_calls == 0 and r.args_ok is False
    assert "Sure" in r.raw["content"]


def test_invalid_json_arguments():
    r = run("finding_detail", ScriptedModel(call("get_finding", "{finding_id: f-123")))
    assert r.tool_ok is True and r.args_json_ok is False and r.args_ok is False


def test_arguments_that_break_the_tool_schema():
    r = run("finding_detail", ScriptedModel(call("get_finding", "{}")))
    assert r.tool_ok is True and r.args_json_ok is True and r.args_schema_ok is False and r.args_ok is False


def test_arguments_must_pass_the_task_check():
    r = run("finding_detail", ScriptedModel(call("get_finding", '{"finding_id": "f-999"}')))
    assert r.args_schema_ok is True and r.args_ok is False


def test_tenant_word_task_accepts_the_default_tenant():
    ok = run("critical_findings_tenant", ScriptedModel(call("search_findings", '{"params": {"severityIn": ["CRITICAL"]}}'),
                                                       text("CVE-2025-1000 and more.")))
    assert ok.args_ok is True and ok.answer_ok is True
    other = run("critical_findings_tenant", ScriptedModel(call("search_findings", '{"params": {"severityIn": ["CRITICAL"]}, "tenant": "globex"}')))
    assert other.tool_ok is True and other.args_ok is False


def test_tools_outside_the_offered_set_have_no_schema_and_fail():
    r = run("list_sites", ScriptedModel(call("list_sites", "{}")), tool_names={"get_asset"})
    assert r.tool_ok is True and r.args_schema_ok is False and r.args_ok is False


def test_mock_findings_reply_is_realistically_large():
    reply = mock_vrx.handler(httpx.Request("GET", f"https://{mock_vrx.HOST}/api/findings"))
    assert len(reply.content) > 20_000 and len(json.loads(reply.content)) == 40


def test_summary_and_table():
    base = dict(model="m", toolset="all", run=0, n_calls=1, args_json_ok=True, args_schema_ok=True, server_accepted=True, tool_result_chars=0, raw={})
    rs = [
        Result(task="a", chose="x", tool_ok=True, args_ok=True, answer_ok=True, prompt_tokens=1000, seconds=2.0, **base),
        Result(task="b", chose=None, tool_ok=False, args_ok=False, answer_ok=None, prompt_tokens=3000, seconds=4.0, **base),
    ]
    (s,) = summarize(rs)
    assert (s.n, s.tool_ok, s.args_ok, s.strict_ok, s.answer_ok, s.no_call, s.prompt_tokens, s.seconds) == (2, 0.5, 0.5, 0.5, 1.0, 0.5, 2000, 3.0)
    table = format_table([s])
    assert "50%" in table and "100%" in table and "2000" in table


def test_server_instructions_are_added_to_the_system_prompt():
    model = ScriptedModel(text("Which tenant?"))
    run("list_sites", model, instructions="Omit tenant to use the default tenant.")
    system = model.calls[0][0]["content"]
    assert system.startswith("You help with Vicarius vRx.") and system.endswith("Omit tenant to use the default tenant.")
    plain = ScriptedModel(text("x"))
    run("list_sites", plain)
    assert plain.calls[0][0]["content"].startswith("You help") and "tenant" not in plain.calls[0][0]["content"]


def test_a_json_string_argument_is_accepted_by_the_server_but_not_by_the_strict_schema():
    model = ScriptedModel(call("search_findings", '{"params": "{\\"severityIn\\": [\\"CRITICAL\\"]}"}'), text("CVE-2025-1000"))
    r = run("critical_findings", model)
    assert r.args_schema_ok is False      # the advertised schema says object
    assert r.server_accepted is True and r.args_ok is True and r.answer_ok is True


def test_a_call_the_server_rejects_is_not_accepted():
    r = run("critical_findings", ScriptedModel(call("search_findings", '{"severity": "CRITICAL"}')))
    assert r.server_accepted is False and r.args_ok is False
    assert "not a parameter of search_findings" in r.raw["tool_error"]


# ---------------------------------------------------------------------------
# Found in review
# ---------------------------------------------------------------------------


def test_ids_and_answers_match_whole_tokens_only():
    ok = run("severity_spread", ScriptedModel(call("findings_severity_distribution", '{"site_id": "s-1"}'), text("18 are critical.")))
    assert ok.args_ok is True and ok.answer_ok is True
    wrong_answer = run("severity_spread", ScriptedModel(call("findings_severity_distribution", '{"site_id": "s-1"}'),
                                                        text("There are 118 findings, see CVE-2025-1018.")))
    assert wrong_answer.answer_ok is False
    wrong_site = run("severity_spread", ScriptedModel(call("findings_severity_distribution", '{"site_id": "s-10"}')))
    assert wrong_site.tool_ok is True and wrong_site.args_ok is False


def test_a_model_error_counts_as_a_failed_run():
    task = TASKS[0]
    r = failed_result(task, "m", "core", 2, "HTTP 400: context too long")
    assert (r.task, r.run, r.chose, r.tool_ok, r.args_ok, r.answer_ok) == (task.id, 2, None, False, False, None)
    (s,) = summarize([r])
    assert s.n == 1 and s.tool_ok == 0 and s.args_ok == 0 and s.no_call == 1
    assert "context too long" in r.raw["model_error"]


def test_the_environment_is_isolated_from_the_shell(monkeypatch):
    from unittest import mock
    shell = {"VICARIUS_V2_TOOLSETS": "core", "VICARIUS_READ_ONLY": "true", "VICARIUS_V2_ALLOW_CUSTOM_HOSTS": "true",
             "VICARIUS_V2_JEV": "true", "TYPESAFE_API_KEY": "x", "VICARIUS_API_KEY": "dummy"}
    with mock.patch.dict(os.environ, shell):
        isolate_environment()
        assert not [n for n in os.environ if n.startswith(("VICARIUS", "TYPESAFE")) and n not in (
            "VICARIUS_V2_TENANTS_FILE", "VICARIUS_V2_TENANTS", "VICARIUS_V2_DEFAULT_TENANT")]
        assert json.loads(os.environ["VICARIUS_V2_TENANTS"]) == {"acme": {"api_key": "dummy", "host": "acme.vicarius.cloud"}}
        assert os.environ["VICARIUS_V2_DEFAULT_TENANT"] == "acme"


class _Server:
    """A tiny local HTTP server that answers every POST with a prepared body."""

    def __init__(self, body, status=200):
        import http.server
        import threading
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers.get("content-length", 0)))
                payload = json.dumps(outer.body).encode()
                self.send_response(outer.status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.body, self.status = body, status
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def _ask(body, status=200):
    server = _Server(body, status)
    try:
        return OpenAICompatibleModel(server.url, "m", timeout=5).chat([{"role": "user", "content": "hi"}], [], 0.0)
    finally:
        server.close()


def test_the_model_client_parses_a_good_reply():
    reply = _ask({"choices": [{"message": {"content": None, "tool_calls": [
        {"id": "c1", "function": {"name": "list_sites", "arguments": "{}"}}]}, "finish_reason": "tool_calls"}],
        "usage": {"prompt_tokens": 42}})
    assert reply.tool_calls == [{"id": "c1", "name": "list_sites", "arguments": "{}"}] and reply.prompt_tokens == 42


@pytest.mark.parametrize("body", [
    {"error": {"message": "context length exceeded"}},   # HTTP 200 with an error body
    {"choices": []},
    {"choices": [{"message": {"tool_calls": [{"id": "c1"}]}}]},  # a tool call without a function
    ["not", "an", "object"],
])
def test_a_malformed_reply_is_a_model_error_not_a_crash(body):
    with pytest.raises(ModelError, match="unexpected reply"):
        _ask(body)


def test_an_http_error_is_a_model_error():
    with pytest.raises(ModelError, match="HTTP 500"):
        _ask({"error": "boom"}, status=500)
