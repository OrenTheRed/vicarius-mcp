"""Run tasks against a model that drives the vicarius-v2-mcp tools, and score what it does."""

from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

import jsonschema

from .match import whole as _whole
from .tasks import Task

SYSTEM_PROMPT = "You help with Vicarius vRx. Use the tools to answer. Call the single best tool first."


class ModelError(Exception):
    pass


@dataclass
class Reply:
    content: str | None
    tool_calls: list  # [{"id": str, "name": str, "arguments": str | dict}]
    finish: str | None = None
    prompt_tokens: int = 0
    seconds: float = 0.0


class OpenAICompatibleModel:
    """Any server that speaks POST /v1/chat/completions with tools (Ollama, LM Studio, llama.cpp, oMLX, vLLM)."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 600.0):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def chat(self, messages: list, tools: list, temperature: float) -> Reply:
        body = {"model": self.model, "messages": messages, "tools": tools, "temperature": temperature, "max_tokens": 400}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers)
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise ModelError(f"HTTP {exc.code}: {exc.read(300).decode('utf-8', 'replace')}") from None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise ModelError(str(exc)[:200]) from None
        try:
            choice = data["choices"][0]
            message = choice.get("message") or {}
            calls = [
                {"id": c.get("id") or f"call_{i}", "name": c["function"]["name"], "arguments": c["function"].get("arguments", "{}")}
                for i, c in enumerate(message.get("tool_calls") or [])
            ]
            return Reply(message.get("content"), calls, choice.get("finish_reason"),
                         (data.get("usage") or {}).get("prompt_tokens", 0), time.time() - started)
        except (KeyError, IndexError, TypeError, AttributeError):
            # Some servers answer HTTP 200 with an error body, or an empty list of choices.
            raise ModelError(f"unexpected reply: {json.dumps(data, default=str)[:200]}") from None


@dataclass
class Result:
    task: str
    model: str
    toolset: str
    run: int
    chose: str | None
    n_calls: int
    tool_ok: bool
    args_json_ok: bool
    args_schema_ok: bool
    args_ok: bool
    server_accepted: bool
    answer_ok: bool | None  # None when the task has no answer check or the call was wrong
    prompt_tokens: int
    seconds: float
    tool_result_chars: int = 0
    raw: dict = field(default_factory=dict)


def failed_result(task: Task, model: str, toolset: str, run: int, error: str) -> Result:
    """A run in which the model server failed counts as a failed run, so it cannot flatter the rates."""
    return Result(task.id, model, toolset, run, None, 0, False, False, False, False, False, None, 0, 0.0,
                  raw={"model_error": error[:300]})


def to_openai_tools(tools) -> list:
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}}
            for t in tools]


def _parse_args(raw) -> tuple[dict, bool]:
    if isinstance(raw, dict):
        return raw, True
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}, False
    return (value, True) if isinstance(value, dict) else ({}, False)


def _text(result) -> str:
    return "".join(getattr(part, "text", "") for part in result.content)


async def run_task(client, model, model_name: str, toolset: str, tools: list, schemas: dict,
                   task: Task, run: int, temperature: float, instructions: str = "") -> Result:
    """One request, scored on the first tool call and (when the task has one) on the final answer.
    `instructions` is the server's own text, which MCP clients usually add to the system prompt."""
    system = SYSTEM_PROMPT + (f"\n\n{instructions}" if instructions else "")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": task.prompt}]
    first = await asyncio.to_thread(model.chat, messages, tools, temperature)
    seconds, tokens = first.seconds, first.prompt_tokens
    raw = {"content": (first.content or "")[:300], "finish": first.finish, "tool_calls": first.tool_calls[:2]}

    if not first.tool_calls:
        return Result(task.id, model_name, toolset, run, None, 0, False, False, False, False, False, None, tokens, seconds, raw=raw)

    call = first.tool_calls[0]
    name = call["name"]
    args, json_ok = _parse_args(call["arguments"])
    schema_ok = False
    if json_ok and name in schemas:
        try:
            jsonschema.validate(args, schemas[name])
            schema_ok = True
        except jsonschema.ValidationError:
            schema_ok = False
    tool_ok = name in task.accept

    # What the server really does with the call. A strict client would stop at the advertised schema.
    accepted, outcome, text = False, None, ""
    if json_ok and name in schemas:
        outcome = await client.call_tool(name, args, raise_on_error=False)
        text = _text(outcome)
        accepted = not (outcome.is_error and (text.startswith("Invalid arguments") or "validation error" in text))
    args_ok = bool(tool_ok and accepted and task.accept[name](args))
    raw["tool_error"] = text[:200] if outcome is not None and outcome.is_error else None

    answer_ok, result_chars = None, 0
    if args_ok and task.answer_any:
        result_chars = len(text)
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": call["id"], "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]})
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": text})
        second = await asyncio.to_thread(model.chat, messages, tools, temperature)
        seconds += second.seconds
        final = second.content or ""
        answer_ok = (not second.tool_calls) and any(_whole(a, final) for a in task.answer_any)
        raw["answer"] = (second.content or "")[:300]
    return Result(task.id, model_name, toolset, run, name, len(first.tool_calls), tool_ok, json_ok, schema_ok, args_ok,
                  accepted, answer_ok, tokens, seconds, result_chars, raw)


@dataclass
class Summary:
    model: str
    toolset: str
    n: int
    tool_ok: float
    args_ok: float
    strict_ok: float
    answer_ok: float | None
    no_call: float
    prompt_tokens: float
    seconds: float


def summarize(results: list) -> list:
    groups: dict = {}
    for r in results:
        groups.setdefault((r.model, r.toolset), []).append(r)
    out = []
    for (model, toolset), rs in groups.items():
        n = len(rs)
        answered = [r for r in rs if r.answer_ok is not None]
        out.append(Summary(
            model, toolset, n,
            sum(r.tool_ok for r in rs) / n, sum(r.args_ok for r in rs) / n,
            sum(r.args_ok and r.args_schema_ok for r in rs) / n,
            (sum(bool(r.answer_ok) for r in answered) / len(answered)) if answered else None,
            sum(r.chose is None for r in rs) / n,
            sum(r.prompt_tokens for r in rs) / n, sum(r.seconds for r in rs) / n,
        ))
    return out


def format_table(summaries: list) -> str:
    lines = [f"{'model':30} {'tools':8} {'n':>4} {'right tool':>10} {'tool+args':>9} {'strict':>7} {'answer':>7} {'no call':>8} {'prompt tok':>10} {'sec/req':>8}"]
    for s in summaries:
        answer = "-" if s.answer_ok is None else f"{s.answer_ok:.0%}"
        lines.append(f"{s.model[:30]:30} {s.toolset:8} {s.n:>4} {s.tool_ok:>10.0%} {s.args_ok:>9.0%} {s.strict_ok:>7.0%} {answer:>7} "
                     f"{s.no_call:>8.0%} {s.prompt_tokens:>10.0f} {s.seconds:>8.1f}")
    return "\n".join(lines)


def result_to_dict(result: Result) -> dict:
    return asdict(result)
