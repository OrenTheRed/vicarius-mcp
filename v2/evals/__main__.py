"""Command line: score local models on driving vicarius-v2-mcp. Uses a mocked vRx and never touches a real tenant."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evals", description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible base URL, for example http://127.0.0.1:8000/v1")
    parser.add_argument("--model", action="append", required=True, help="model name (repeat for several)")
    parser.add_argument("--api-key", default=os.environ.get("EVAL_API_KEY"), help="optional bearer key (or set EVAL_API_KEY)")
    parser.add_argument("--tools", default="all,core", help="comma list of: all, core, or a set of tool names joined with +")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--instructions", choices=("none", "server"), default="none",
                        help="'server' adds the server's own instructions text to the system prompt, as MCP clients usually do")
    parser.add_argument("--tasks", default="", help="comma list of task ids (default: all)")
    parser.add_argument("--out", default="evals_out", help="directory for results.jsonl and failures.jsonl")
    args = parser.parse_args(argv)

    # Isolate from the shell: no real tenants file or key, no tool filter, only the mocked tenant.
    from .env import isolate_environment

    isolate_environment()

    import httpx
    import respx
    from fastmcp import Client

    from vicarius_v2_mcp.server import mcp

    from . import mock_vrx
    from .harness import (ModelError, OpenAICompatibleModel, failed_result, format_table, result_to_dict, run_task,
                          summarize, to_openai_tools)
    from .tasks import CORE, TASKS

    wanted = {t for t in args.tasks.split(",") if t}
    tasks = [t for t in TASKS if not wanted or t.id in wanted]
    if not tasks:
        parser.error("no matching tasks")

    async def go() -> int:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        results = []
        with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
            router.route(host=mock_vrx.HOST).mock(side_effect=mock_vrx.handler)
            async with Client(mcp) as client:
                instructions = (client.initialize_result.instructions or "") if args.instructions == "server" else ""
                all_tools = await client.list_tools()
                by_name = {t.name: t for t in all_tools}
                sets = {}
                for spec in args.tools.split(","):
                    spec = spec.strip()
                    names = list(by_name) if spec == "all" else [n for n in CORE if n in by_name] if spec == "core" else spec.split("+")
                    missing = [n for n in names if n not in by_name]
                    if missing:
                        parser.error(f"unknown tools in {spec!r}: {missing}")
                    chosen = [by_name[n] for n in names]
                    label = spec if spec in ("all", "core") else f"custom{len(sets)}"
                    sets[label + ("+instr" if instructions else "")] = (
                        to_openai_tools(chosen), {t.name: t.inputSchema for t in chosen})
                for model_name in args.model:
                    model = OpenAICompatibleModel(args.base_url, model_name, args.api_key)
                    warm_tools = next(iter(sets.values()))[0]
                    try:
                        model.chat([{"role": "user", "content": "hi"}], warm_tools, 0.0)  # loads the model
                    except ModelError as exc:
                        print(f"{model_name}: cannot reach the model: {exc}", file=sys.stderr)
                        return 1
                    for toolset, (oa_tools, schemas) in sets.items():
                        for task in tasks:
                            for run in range(args.runs):
                                try:
                                    result = await run_task(client, model, model_name, toolset, oa_tools, schemas, task, run, args.temperature, instructions)
                                except ModelError as exc:
                                    # A model that errors on a task has failed it. Count it, do not drop it.
                                    print(f"{model_name} {toolset} {task.id}: {exc}", file=sys.stderr)
                                    result = failed_result(task, model_name, toolset, run, str(exc))
                                results.append(result)
                        print(f"done: {model_name} / {toolset}", flush=True)
        with open(out_dir / "results.jsonl", "w") as fh:
            for r in results:
                fh.write(json.dumps(result_to_dict(r)) + "\n")
        with open(out_dir / "failures.jsonl", "w") as fh:
            for r in results:
                if not r.args_ok or r.answer_ok is False:
                    fh.write(json.dumps(result_to_dict(r)) + "\n")
        print()
        print(format_table(summarize(results)))
        print(f"\nraw results and failures: {out_dir}/")
        return 0

    return asyncio.run(go())


if __name__ == "__main__":
    sys.exit(main())
