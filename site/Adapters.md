
# Adapters

SAGE adapters exchange the same `sage/0.2` wire and durable-bus state while using each host's native lifecycle hooks. The recommended order when integrating a framework: (1) native hook/plugin adapter, (2) A2A as the generic peer envelope, (3) MCP for tool/context access, (4) REST/Python runtime for custom orchestrators. The SAGE server stays the same in all cases.

A key rule applies to every adapter: **adapters must not construct SAGE semantic envelopes**. They pass raw structured application data; semantic and wire encoding remain owned by SAGE. The OpenClaw adapter explicitly rejects content that looks like an encoded SAGE envelope, and the Hermes adapter documents the same rule.

## Hermes plugin

The Hermes adapter ships two ways, kept byte-identical by release checks:

1. The standalone release ZIP (`sage-hermes-plugin-v0.2.6.zip`), which extracts into one versioned directory with installers, README, license, plugin manifest, and adapter.
2. The packaged Python entry point `hermes_agent.plugins:sage = sage_plugin.hermes_plugin` declared in `pyproject.toml`.

### Integration surface

- The plugin registers a `sage_handoff` tool: send raw structured application-level facts or state to another agent (`receiver`, `content` object, optional `correlation_id`, `priority`, `budget_tokens`). `content` must be a JSON object — plain text is rejected, and callers must not serialize content to text or construct SAGE literals/concepts/refs/packets.
- Pre-LLM lifecycle hook claims mailbox messages within an injection budget.
- Post-LLM hook ACKs only successful-turn claims. A crashed turn is recovered by the bus claim lease (`SAGE_BUS_CLAIM_LEASE_SECONDS`, default 60 s).
- The adapter claims already-decoded SAGE context in one request and acknowledges the successful batch after the model call lifecycle completes.

The release plugin is self-contained and uses only the Python standard library inside Hermes; SAGE itself runs as a separate service.

### Manifest

`integrations/hermes/sage/plugin.yaml`:

```yaml
name: sage
version: "0.2.6"
description: Vendor-neutral SAGE semantic bus with automatic context injection and structured handoff.
requires_env:
  - SAGE_URL
```

### Configuration

Set these variables in the environment used to start Hermes:

```text
SAGE_URL=http://127.0.0.1:8080
SAGE_AGENT_ID=hermes-a
SAGE_WORKSPACE=default
SAGE_API_KEY=
SAGE_MAX_INJECT_TOKENS=1200
```

- `SAGE_API_KEY` is needed only when the SAGE service requires authentication.
- Use a unique `SAGE_AGENT_ID` for each agent that has a separate mailbox.
- `SAGE_MAX_INJECT_TOKENS` defaults to 1200 (minimum 64).

### Install and verify

```bash
unzip sage-hermes-plugin-v0.2.6.zip
cd sage-hermes-plugin-v0.2.6
./install.sh
```

The installer copies the plugin to `$HERMES_HOME/plugins/sage` (or `~/.hermes/plugins/sage` when `HERMES_HOME` is not set) and enables it when the `hermes` command is available. Verify with `hermes plugins list --plain` (should show `sage` enabled) and start a new Hermes session after changing plugin files or environment variables.

For Hermes in Docker: `./install.sh "$HERMES_DATA_DIR"`; when SAGE runs on the Docker host set `SAGE_URL=http://host.docker.internal:8080` (Linux Compose deployments may also need `extra_hosts: ["host.docker.internal:host-gateway"]`). Full instructions are in `integrations/hermes/README.md`.

## OpenClaw plugin

`integrations/openclaw` is a native mixed tool/hook plugin (`@sage-agent/openclaw-sage@0.2.6`), built from TypeScript (`src/index.ts`) with an independent conformance runner (`dist/conformance.js`).

### Integration surface

- **Tools** (declared in `openclaw.plugin.json` and registered via the plugin SDK):
  - `sage_handoff` — send raw structured application-level data to another agent through SAGE (`receiver`, `content` JSON object, optional `correlationId`, `priority`, `budgetTokens`). `content` must be a JSON object; plain text and pre-encoded SAGE semantic envelopes are rejected.
  - `sage_poll` — poll pending SAGE handoffs for the active agent (`GET /v1/bus/pull/{agent}` with `claim=false`, optional `limit` 1–100, default 20).
  - `sage_ack` — acknowledge a SAGE handoff after consuming it (`POST /v1/bus/{message_id}/ack`).
- **`agent_turn_prepare` hook**: claims and injects a decoded SAGE context batch (`GET /v1/bus/context/{agentId}`) as same-turn peer context. Injection budget adapts to OpenClaw's exposed context token budget when present (`min(maxInjectTokens, max(64, floor(modelBudget × contextBudgetFraction)))`).
- **`agent_end` hook**: ACKs the claimed batch (`POST /v1/bus/ack-batch`) **only after** OpenClaw reports a successful run (`event.success === true`). Claimed run state is bounded in memory (max 1024 pending runs); failed runs are left for lease-based redelivery.

### Manifest

`integrations/openclaw/openclaw.plugin.json` declares: id `sage`, activation `onStartup`, the three tools under `contracts.tools`, and a `configSchema` with `url`, `agentId`, `workspace`, `apiKey`, `autoInject` (bool), `maxInjectTokens` (integer ≥ 64, default 1200), `contextBudgetFraction` (number 0.01–1, default 0.2).

### Configuration

```json
{
  "url": "http://127.0.0.1:8080",
  "agentId": "openclaw-a",
  "workspace": "default",
  "apiKey": "",
  "autoInject": true,
  "maxInjectTokens": 1200,
  "contextBudgetFraction": 0.2
}
```

The plugin also falls back to environment variables (`SAGE_URL`, `SAGE_AGENT_ID`, `SAGE_WORKSPACE`, `SAGE_API_KEY`). Use a unique `agentId` per agent mailbox; set `apiKey` only when auth is enabled.

### Install and verify

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.6.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

For noninteractive installs, OpenClaw may require `--force` for a reviewed local archive or npm-pack source. From source: `cd integrations/openclaw && npm install && npm run build`, then `openclaw plugins install --link ./integrations/openclaw`. Verify the service independently with `sage-doctor --url http://127.0.0.1:8080 --agent-id openclaw-a`.

## Claude / OpenAI / generic MCP

Use the same authenticated remote `/mcp` endpoint on `sage-api`. MCP tools include `sage_handoff`, `sage_poll`, `sage_ack`, `sage_send`, `sage_receive`, refs, state, codebooks, evals, and latent transport. Because MCP authentication is service-scoped in v0.2, use a per-agent gateway/native adapter when mailbox isolation between untrusted agents is required.

## Generic A2A

Use `sage_plugin.a2a_adapter.pack_data_part` / `unpack_data_part` or the REST bridge. The payload is provider-neutral (`application/vnd.sage.packet+json`); A2A task/message lifecycle and agent cards remain owned by the chosen A2A SDK/runtime.

## Custom orchestrators

Use `SageRuntime.handoff/poll/ack` directly — the smallest dependency surface, below the model, with no model-visible tool calls required.

See `docs/INTEGRATIONS.md` in the repo for the full integration model.

Next: [Development](Development.md)
