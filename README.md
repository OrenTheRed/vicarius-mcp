<div align="center">

# Vicarius vRx MCP Servers

**Manage Vicarius vRx from Claude Code, Codex, or any other MCP client, in plain language.**

[![CI](https://github.com/OrenTheRed/vicarius-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/OrenTheRed/vicarius-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-compatible-6E56CF.svg)](https://modelcontextprotocol.io)
![Platforms](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)

</div>

> *"Which assets have critical findings for vulnerabilities in the CISA KEV catalog?"*
> *"Create a patch policy for the Finance asset group that runs Saturdays at 02:00."*
> *"Summarize last week's failed patch tasks by asset."*
> *"How has our open backlog and MTTR changed over the last quarter?"*

This repository contains two [Model Context Protocol](https://modelcontextprotocol.io) servers that
connect AI agents to the [Vicarius vRx](https://www.vicarius.io) vulnerability remediation
platform. They run locally on your machine, talk directly to the Vicarius API over HTTPS, and
send no telemetry anywhere else.

| Server | Vicarius API | Tools | Best for |
|---|---|---|---|
| [**`vicarius-v2-mcp`**](v2/README.md) | vRx v2 Customer API (`vicarius.cloud/api`) | 119 | Sites, findings, trends and KPIs, scan/patch/script policies, CIS compliance, reports, users. Manages **multiple tenants** from one server. |
| [**`vicarius-mcp`**](v1/README.md) | vRx External Data API (`<dashboard>.vicarius.cloud`) | 42 | Assets, CVEs, patches, events, automations and users on a classic vRx dashboard. |

You can install either server or both; they run side by side.

---

## Contents

- [Features](#features)
- [Which server do I need?](#which-server-do-i-need)
- [Quick start](#quick-start)
  - [1. Install the prerequisites](#1-install-the-prerequisites)
  - [2. Install the server](#2-install-the-server)
  - [3. Add your API key](#3-add-your-api-key)
  - [4. Connect your AI client](#4-connect-your-ai-client)
- [Read-only mode](#read-only-mode)
- [Local models and small context windows](#local-models-and-small-context-windows)
- [Security](#security)
- [Updating and uninstalling](#updating-and-uninstalling)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## Features

- **161 tools** across both servers, each a thin wrapper around the Vicarius API.
- **Insights, not just records.** Dashboard KPIs, breakdowns by OS, severity and status, risk-score
  history, and finding trends with mean time to remediate (MTTR).
- **Read-only mode.** Set `VICARIUS_READ_ONLY=true` and every tool that can change anything is
  removed from the server, so the agent can't see or call it.
- **Safety annotations.** Every tool declares MCP `readOnlyHint`/`destructiveHint` metadata, so your
  client knows which calls only read data and which ones delete or overwrite it.
- **Multi-tenant (v2).** One server, many Vicarius organizations. You pick the tenant per request
  (*"...for globex"*), and tenant edits apply without a restart.
- **Credentials stay local.** API keys are read from your MCP client's config or a local file
  that's readable only by you. Configured keys are never logged, never returned by a tool or
  included in an error message, and only ever sent to the Vicarius host you configured.
- **Cross-platform.** macOS, Linux and Windows, tested in CI on all three.

## Which server do I need?

| If you... | Use |
|---|---|
| create API keys under **Account Settings → API Tokens** | **v2** (`vicarius-v2-mcp`) |
| create API keys under **Settings → API → Create Integration** on a dashboard at `https://<name>.vicarius.cloud` | **v1** (`vicarius-mcp`) |

If you're not sure, ask your Vicarius contact which API your account uses. You can also install
both.

## Quick start

### 1. Install the prerequisites

You need [**uv**](https://docs.astral.sh/uv/), a fast Python package manager that also installs
Python for you, plus **git**.

<details open>
<summary><b>macOS</b></summary>

```bash
# uv
curl -LsSf https://astral.sh/uv/install.sh | sh      # or: brew install uv

# git (skip if `git --version` already works)
xcode-select --install                               # or: brew install git
```

</details>

<details>
<summary><b>Linux</b></summary>

```bash
# uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# git (skip if `git --version` already works)
sudo apt install -y git        # Debian / Ubuntu
sudo dnf install -y git        # Fedora / RHEL
```

</details>

<details>
<summary><b>Windows</b> (PowerShell)</summary>

```powershell
# uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # or: winget install --id=astral-sh.uv -e

# git (skip if `git --version` already works)
winget install --id Git.Git -e
```

</details>

**Open a new terminal** afterwards so that `uv` is on your `PATH`.

### 2. Install the server

These commands are the same on macOS, Linux and Windows:

```bash
# v2 - vRx v2 Customer API
uv tool install "git+https://github.com/OrenTheRed/vicarius-mcp#subdirectory=v2"

# v1 - vRx External Data API
uv tool install "git+https://github.com/OrenTheRed/vicarius-mcp#subdirectory=v1"
```

Check that the install worked:

```bash
vicarius-v2-mcp --version
vicarius-mcp --version
```

> [!TIP]
> If you get *command not found*, run `uv tool update-shell` and open a new terminal.
> To pin an exact release, add the tag before `#`, e.g.
> `git+https://github.com/OrenTheRed/vicarius-mcp@v1.5.0#subdirectory=v2`.

### 3. Add your API key

#### v2: create a tenants file

Each entry maps a name of your choosing to one Vicarius API key (from **Account Settings → API
Tokens**). Add as many tenants as you like.

```json
{
  "acme":   { "api_key": "<api-key-for-acme>" },
  "globex": { "api_key": "<api-key-for-globex>" }
}
```

<details open>
<summary><b>macOS / Linux</b></summary>

```bash
mkdir -p ~/.config/vicarius-v2-mcp
${EDITOR:-nano} ~/.config/vicarius-v2-mcp/tenants.json     # paste the JSON above, then save
chmod 600 ~/.config/vicarius-v2-mcp/tenants.json           # readable by you only
```

</details>

<details>
<summary><b>Windows</b> (PowerShell)</summary>

```powershell
New-Item -ItemType Directory -Force "$HOME\.config\vicarius-v2-mcp" | Out-Null
notepad "$HOME\.config\vicarius-v2-mcp\tenants.json"       # paste the JSON above, then save
```

</details>

The file is re-read on every tool call, so you can add or remove tenants at any time without
restarting anything. All options are covered in the [v2 reference](v2/README.md#configuration).

#### v1: nothing to do yet

The v1 server takes your dashboard name and API key as environment variables. You'll pass them
in the next step.

### 4. Connect your AI client

<details open>
<summary><b>Claude Code</b></summary>

Commands are identical in Terminal (macOS/Linux) and PowerShell (Windows). `--scope user` makes
the server available in every project. Use `--scope local` to limit it to the current project.

**v2**

```bash
claude mcp add --scope user vicarius-v2 vicarius-v2-mcp
```

**v1**: replace `acme` with your dashboard subdomain and `<api-key>` with your key:

```bash
claude mcp add --scope user vicarius vicarius-mcp -e VICARIUS_DASHBOARD=acme -e VICARIUS_API_KEY=<api-key>
```

> [!NOTE]
> Claude Code stores the key in `~/.claude.json` (`%USERPROFILE%\.claude.json` on Windows),
> which lives in your home folder and is private to you. **Never** use `--scope project` with a
> key: that writes it into `.mcp.json`, a file meant to be committed to git.
>
> Commands you type are saved in your shell history. If your shell skips lines that start with a
> space (`HISTCONTROL=ignorespace` in bash, `setopt HIST_IGNORE_SPACE` in zsh), start the command
> with a space so the key isn't recorded.

**Verify:** run `claude mcp list` (the server should show *✓ Connected*), or type `/mcp` inside
Claude Code.

</details>

<details open>
<summary><b>Codex</b></summary>

Add the servers to Codex's config file:

| OS | Config file |
|---|---|
| macOS / Linux | `~/.codex/config.toml` |
| Windows | `%USERPROFILE%\.codex\config.toml` |

```toml
# v2
[mcp_servers.vicarius-v2]
command = "vicarius-v2-mcp"

# v1: replace acme and <api-key> with your values
[mcp_servers.vicarius]
command = "vicarius-mcp"
env = { VICARIUS_DASHBOARD = "acme", VICARIUS_API_KEY = "<api-key>" }
```

Or use the Codex CLI instead of editing the file:

```bash
codex mcp add vicarius-v2 -- vicarius-v2-mcp
codex mcp add vicarius --env VICARIUS_DASHBOARD=acme --env VICARIUS_API_KEY=<api-key> -- vicarius-mcp
```

> [!TIP]
> If you keep secrets in a manager such as 1Password or Vault, you can export
> `VICARIUS_API_KEY` from it and replace the `env` line with
> `env_vars = ["VICARIUS_API_KEY", "VICARIUS_DASHBOARD"]`. Codex then forwards those variables
> from your shell, and the key never touches `config.toml`.

**Verify:** run `codex mcp list`, or type `/mcp` inside Codex.

</details>

<details>
<summary><b>Other MCP clients</b></summary>

Both servers speak standard MCP over **stdio**, so any MCP client can use them, with a hosted model
or a local one. Point your client at the command `vicarius-v2-mcp` or `vicarius-mcp` (no arguments)
and pass the environment variables described in the [v1](v1/README.md#configuration) /
[v2](v2/README.md#configuration) references. Most clients take a config like this:

```json
{
  "mcpServers": {
    "vicarius-v2": { "command": "vicarius-v2-mcp", "env": { "VICARIUS_V2_TOOLSETS": "core" } }
  }
}
```

Running a local model? Read [Local models and small context windows](#local-models-and-small-context-windows).

</details>

**Try it:** ask your agent *"List my Vicarius tenants and show the five assets with the most
critical findings."*

## Read-only mode

To give an agent visibility without the ability to change anything, set `VICARIUS_READ_ONLY=true`.
The server then registers only its read tools: 72 of 119 for v2, 32 of 42 for v1. The write tools
aren't just blocked; they no longer exist from the agent's point of view.

```bash
# Claude Code
claude mcp add --scope user vicarius-v2-readonly vicarius-v2-mcp -e VICARIUS_READ_ONLY=true
```

```toml
# Codex
[mcp_servers.vicarius-v2-readonly]
command = "vicarius-v2-mcp"
env = { VICARIUS_READ_ONLY = "true" }
```

You can register the same server twice, once read-only and once full, and enable whichever fits
the task.

## Local models and small context windows

The servers do not care which model drives them. A local model (served by Ollama, LM Studio,
llama.cpp, oMLX, vLLM or similar, inside an MCP-capable client such as LM Studio, Open WebUI, Goose,
Jan, Cline, Continue or AnythingLLM) can use every tool. Two things matter more for a small model
than for a large hosted one:

- **The tool list is sent with every conversation.** The full v2 list is about 16,000 to 20,000
  tokens, more than a small context window holds, and a long list makes tool choice less reliable.
  Set `VICARIUS_V2_TOOLSETS=core` for 16 read tools (about 3,000 tokens) that cover findings,
  assets, sites, trends and tenants. Add whole groups when you need more, for example
  `VICARIUS_V2_TOOLSETS=core,compliance`. See the [v2 reference](v2/README.md#smaller-tool-list).
- **Arguments.** The v2 server accepts a JSON object written as text where a tool wants an object,
  and the text "null" or "none" for `tenant` (which means the default tenant), because some models
  send them that way. When an argument is wrong, the error says which one and how to fix it, so the
  model can correct the call.

Tips: give the model a context of at least 16,000 tokens (Ollama's default is small, so raise it),
pick a model that supports tool calling, set `VICARIUS_READ_ONLY=true` unless you need changes, and
keep your client's approval prompts on. Small models are easier to steer with text in tenant data,
such as an asset name, than large ones.

How well a model drives the tools can be measured. The harness in [`v2/evals`](v2/evals/README.md)
scores tool choice, arguments and answers against a mocked vRx, for any server that speaks the
OpenAI chat API.

## Security

These servers give an AI agent the same power over your Vicarius tenant as the API key you
provide. The short version:

- **Prefer read-only mode** unless you need the agent to make changes. Use a dedicated API key
  for the agent so its actions are easy to spot in the vRx audit log (`list_audit_logs`).
- **Review write actions.** Claude Code asks for your approval before each MCP tool call unless
  you've allowed that tool. Don't auto-approve write or destructive Vicarius tools, and check
  your Codex approval settings before you rely on them. You can also block specific tools
  entirely: in Claude Code, add a rule such as `"mcp__vicarius-v2__delete_site"` to
  `permissions.deny` in `settings.json`. In Codex, add `disabled_tools = ["delete_site"]` under
  the server's table.
- **Mind prompt injection.** Asset names, script output and other tenant data are shown to the
  model. Treat requests to make changes that came from data, rather than from you, with
  suspicion.
- **Keep keys out of chats and repos.** Don't paste API keys into the conversation (they reach
  your AI provider), and never commit `tenants.json` or a `.mcp.json` that contains a key.

See [SECURITY.md](SECURITY.md) for the full security model and how to report a vulnerability.

## Updating and uninstalling

```bash
uv tool upgrade vicarius-v2-mcp          # or: uv tool upgrade --all
uv tool uninstall vicarius-v2-mcp        # removes the program

claude mcp remove vicarius-v2 --scope user   # Claude Code
codex mcp remove vicarius-v2                 # Codex
```

Uninstalling doesn't delete your tenants file. Remove `~/.config/vicarius-v2-mcp/` yourself if
you no longer need it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `vicarius-v2-mcp: command not found` | Run `uv tool update-shell` and open a new terminal. Or use the full path in your client config: find it with `which vicarius-v2-mcp` (macOS/Linux) or `where.exe vicarius-v2-mcp` (Windows). |
| Server shows *Failed* / *disconnected* | Run the command (`vicarius-v2-mcp --version`) in a terminal to see the error. Restart your client after changing its config. |
| `No tenants configured` | The tenants file is missing or empty. Check its location (step 3) or set `VICARIUS_V2_TENANTS_FILE` to its full path. |
| `ERROR 401` / `ERROR 403` | The API key is wrong, expired, or lacks permission for that action. For v1, also check `VICARIUS_DASHBOARD`. |
| `Unknown tenant "x"` | Tenant names are case-sensitive. Ask the agent to run `list_configured_tenants`. |
| Codex reports a startup timeout | Add `startup_timeout_sec = 30` under the server's table in `config.toml`. |
| `uv tool install` fails with a git error | Install git (step 1) and make sure `git --version` works in the same terminal. |

## Development

```bash
git clone https://github.com/OrenTheRed/vicarius-mcp.git
cd vicarius-mcp/v2          # or v1
uv sync --extra dev
uv run pytest
```

The test suites mock every HTTP call, so they need no Vicarius account or network access. To try
local changes in a client, install from your checkout with `uv tool install --force ./v2`.

```
.
├── v1/          vicarius-mcp: vRx External Data API (42 tools)
├── v2/          vicarius-v2-mcp: vRx v2 Customer API, multi-tenant (119 tools)
├── SECURITY.md
├── CHANGELOG.md
└── LICENSE
```

## License

[MIT](LICENSE). You're free to use, copy, modify and redistribute this software, commercially or
otherwise. The only requirement is that you keep the copyright notice.

<sub>Vicarius and vRx are trademarks of their respective owner. This project is provided as-is,
without warranty, and is not an officially supported Vicarius product.</sub>
