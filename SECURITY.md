# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use GitHub's private reporting
instead: go to the repository's **Security** tab and choose **Report a vulnerability**. Include
the affected server (v1 or v2), the version (`vicarius-v2-mcp --version`), and steps to reproduce.

You can expect an acknowledgement within a few business days. Fixes are released as a new tagged
version and noted in [CHANGELOG.md](CHANGELOG.md).

## Supported versions

Only the latest release receives security fixes.

## Security model

These servers run locally, as your user, launched by your MCP client over stdio. They open no
network ports. The only outbound connections go over HTTPS to the Vicarius API host you configure.
There is no telemetry, analytics or third-party relay.

### Credentials

| | Where the key lives | Protection |
|---|---|---|
| v1 | Your MCP client's config (`~/.claude.json`, `~/.codex/config.toml`), passed to the server as an environment variable | Your home directory's permissions |
| v2 | `~/.config/vicarius-v2-mcp/tenants.json`, or the `VICARIUS_V2_TENANTS` environment variable | Written atomically with mode `0600` on macOS/Linux. On Windows, the ACLs of your user profile apply. |

Configured API keys are never written to logs, never returned by a tool or included in an error
message, and only sent in the request header to the configured host. Hosts must be bare
hostnames, and every request uses `https://`. As a second line of defense, both servers also replace the
value of any secret-named field (`password`, `privateKey`, `passphrase`, `accessKey`,
`organizationSecretKey`, ...) with `<redacted>` before a response reaches the agent. Vicarius
already blanks these fields server-side; this safeguard keeps them hidden if that ever changes.
The servers also turn off FastMCP's startup
update check, so they make no connection to PyPI. (Two tools handle keys by design:
`create_api_key` returns the newly created secret, and `add_configured_tenant` receives a key
from the agent.)

### Optional: Jev (TypeSafe)

v2 has an optional tool, `assess_finding_urgency`, that sends facts about one finding to
`api.typesafe.ai`. It is off unless you set both `VICARIUS_V2_JEV=true` and `TYPESAFE_API_KEY`,
and until then the server makes no connection to TypeSafe.

- **You choose what leaves.** The tool is off until you opt in. Once it is on, the default is
  `VICARIUS_V2_JEV_PRIVACY=full`: TypeSafe receives machine names, IP addresses, CVE ids, asset
  groups and software names. `minimal` sends only labels computed in code and hides all of those.
  `preview=true` shows the exact payload without sending it.
- **The answer is advice, with a ceiling and a floor.** With no CISA KEV listing, no exploit tags
  and a low or medium EPSS band, the disposition is capped at `STANDARD` in code. A finding listed
  in CISA KEV is never lower than `STANDARD`. So an asset's role cannot turn weak evidence into an
  urgent finding, or strong evidence into one that is ignored. This holds for Jev and for a local
  model.
- **The key goes to one host.** The TypeSafe key is only sent to `api.typesafe.ai`, redirects are
  not followed, and the key is removed from any error text.
- **Free text can steer the model.** In `full` mode, names are cut to 200 characters, stripped of
  control characters and placed under `untrusted_text`. The answer is advice only and changes
  nothing in vRx.
- **Read the provider's terms.** See https://docs.typesafe.ai/legal.md before you send tenant data.

### Optional: a local model for the urgency tool

The same tool can ask a model on your own machine instead of Jev
(`VICARIUS_V2_URGENCY_PROVIDER=local`). No data goes to TypeSafe then.

- **"Local" is enforced.** `VICARIUS_V2_LLM_URL` must point at this machine: the name `localhost`,
  or an address in `127.0.0.0/8` or `::1`. Other names, including `*.localhost`, are refused, because
  some systems resolve them elsewhere. A server on another computer or a hosted API is refused,
  because the facts would leave this machine. `VICARIUS_V2_LLM_ALLOW_REMOTE=true` allows it, and the
  output then carries a warning. The same privacy switch (`VICARIUS_V2_JEV_PRIVACY`) applies.
- **Nothing sits in the middle.** Proxy settings in the environment (`HTTP_PROXY` and the like) are
  ignored for the model server, so the facts and the key cannot be captured by a proxy.
- **The key, if any, goes to one host.** `VICARIUS_V2_LLM_API_KEY` is sent only to the configured
  URL, and never over plain `http` to another machine. Redirects are not followed, a password inside
  the URL is refused, and the key is removed from error text.
- **A general model can be steered by text.** Asset and software names are the risk. The answer is
  limited to five labels and checked in code, the cap and the floor still apply, `minimal` mode
  keeps names out of the prompt, and the answer is advice only.

### What the agent can do

An agent connected to these servers can do anything the API key allows, including deleting
sites, revoking API keys, removing users and changing patch policies. The servers reduce that
risk in four ways:

1. **Read-only mode**: `VICARIUS_READ_ONLY=true` removes every state-changing tool from the server,
   so it can't be listed or called.
2. **Tool annotations**: each tool declares `readOnlyHint` / `destructiveHint`, so MCP clients can
   tell reads from changes and warn you before destructive calls.
3. **Input hardening**: IDs are percent-encoded before they go into URL paths, and empty, `.`
   or `..` IDs are rejected, so a crafted ID such as `../apiKeys/123` can't redirect a call to a
   different endpoint. In v1, quotes in RSQL values are escaped, so a crafted name can't break
   out of its filter. Wildcards such as `*` are passed through.
4. **Tenant guard rails (v2)**: `add_configured_tenant` won't overwrite an existing tenant unless
   asked to, and it only accepts `vicarius.cloud` hosts unless `VICARIUS_V2_ALLOW_CUSTOM_HOSTS` is
   set. A manipulated agent therefore can't quietly re-point a tenant at another server.

### Your responsibilities

- Create a **dedicated API key** for agent use, with the least privilege your workflow needs, and
  rotate it like any other credential.
- Keep your MCP client's **tool approval prompts on** for write and destructive tools.
- Be aware of **prompt injection**: tenant data such as asset names or script output is passed to
  the model and could contain instructions. Don't approve changes you didn't ask for.
- **Don't paste API keys into the chat.** That includes using `add_configured_tenant`: the key goes
  to your AI provider and stays in your conversation history. Edit the tenants file instead.
- Never commit a `tenants.json`, `.env` or `.mcp.json` that contains a key. This repository's
  `.gitignore` excludes them.
