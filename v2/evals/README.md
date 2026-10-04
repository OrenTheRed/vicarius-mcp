# Agent evaluation harness

How well does a model drive the `vicarius-v2-mcp` tools? This harness answers that with numbers, so
changes to the tool list, the descriptions or the result size can be measured and not guessed.

It is a development tool. It is not part of the published package.

## What it does

For each task (for example "Show me the critical findings for the acme tenant.") it gives the model
the tools, asks for one tool call, and scores:

| Column | Meaning |
|---|---|
| right tool | The model called a tool that is acceptable for the task. |
| tool+args | The tool is right, the arguments are valid JSON, they pass the tool's own JSON schema, and they pass the task's check. |
| answer | When the call was right, the tool ran, the model got the result, and its final answer contains an expected fact. |
| no call | The model answered in text and called no tool. |
| prompt tok | Tokens the server reported for the first request. This is the cost of the tool list. |
| sec/req | Time per task, including the answer step. |

Everything runs in one process. The server runs through FastMCP's in-memory client. vRx is a mock
(`mock_vrx.py`) with replies sized like real ones. **It never touches a real tenant**: the harness
removes every `VICARIUS_*` and `TYPESAFE_*` setting from its environment (so `VICARIUS_V2_TOOLSETS`
or `VICARIUS_READ_ONLY` in your shell cannot shrink the tool list it tests), defines one fake `acme`
tenant, and an unmocked request raises an error.

## Run it

Any server that speaks the OpenAI chat API with tools works (Ollama, LM Studio, llama.cpp, oMLX, vLLM):

```
cd v2
uv run python -m evals --base-url http://127.0.0.1:8000/v1 --model <model-name>
```

Useful options: `--model` (repeat for several models), `--tools all,core` (compare the full tool list
with the server's `core` preset), `--runs 3`, `--temperature 0.2`, `--tasks list_sites,kev`,
`--out DIR`. The run writes `results.jsonl` and `failures.jsonl` (the raw model reply for every
failure) to the output directory.

## Reading the results

- Small runs are noisy. With 16 tasks and 3 runs per setting, a difference of a few points is noise.
- A model that is unsure can flip between runs. Look at `failures.jsonl` before you trust a number.
- `core` here is the server's own preset (`VICARIUS_V2_TOOLSETS=core`). Every task is a common
  question that `core` is meant to serve, so a high score shows that a model drives `core` reliably.
  It does not show that `core` covers every question someone might ask. A task that needs a tool
  outside `core` would have to be added to test that.
- Answers and ids are matched as whole tokens, so "18" does not match "118" and `s-1` does not
  match `s-10`.
- A run in which the model server fails (a timeout, an error body) counts as a failed run. It is
  never dropped from the rates.
- The system prompt is minimal and the same for every model. Real agent apps add their own.

## Tests

`tests/test_evals.py` tests the scoring with a scripted model. CI runs it. The live runs against a
real model are manual.
