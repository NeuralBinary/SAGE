
# CLI Tools

The wheel (`sage_agent_protocol-0.2.2`) installs **12 console scripts**, declared in `[project.scripts]` in `pyproject.toml`. The short table below mirrors the README; each command then gets a paragraph and example.

| Command | Purpose |
| --- | --- |
| `sage-api` | Start the HTTP service on `0.0.0.0:8080`. |
| `sage-mcp` | Standalone MCP adapter mode; development only because it lacks the FastAPI authentication wrapper. |
| `sage-doctor` | Verify service health, database readiness, protocol identity, and the full delivery flow. |
| `sage-demo` | Run a demonstration handoff → claim → ACK delivery; `--single-agent` sends to itself. |
| `sage-tck` | Run the language-neutral conformance vectors (13 vectors, `--json` for machine output). |
| `sage-conform` | Conformance checks; `--fuzz N` runs deterministic malformed-wire mutations. |
| `sage-integrate` | Generate adapter settings for Hermes, OpenClaw, and other platforms. |
| `sage-inspect` | Inspect packet/run compression and semantic decisions. |
| `sage-qualify` | Run the v0.2 qualification runner (concurrency, chaos, vocabulary). |
| `sage-bench` | Compare model-token economics across the protocol's required baselines. |
| `sage-sim` | Offline communication simulator/evaluator over JSON/JSONL cases. |
| `sage-learn` | Codebook and learned-language operations. |

## sage-api

Starts the FastAPI/uvicorn HTTP service on `0.0.0.0:8080`. All server behavior is driven by `SAGE_` environment variables (see [Configuration](Configuration.md)).

```bash
sage-api
```

With authentication disabled this is only safe on a trusted local interface. In production mode the service fails closed at startup unless the production requirements are met (see [Configuration](Configuration.md)).

## sage-mcp

Runs the standalone MCP adapter mode. **Development only**: direct `sage-mcp` mode does not provide the FastAPI authentication wrapper. Production MCP access is served through the authenticated `/mcp` mount on `sage-api` (requires the `mcp` optional dependency group).

```bash
sage-mcp
```

## sage-doctor

Checks liveness, database readiness, `sage/0.2` wire identity, handoff, context claim, ACK, and removal from the pending mailbox. Supports `--url`, `--api-key`, `--workspace`, `--agent-id`, `--timeout`, `--no-flow` (health/database/protocol only), and `--json` for machine output.

```bash
sage-doctor
sage-doctor --url http://127.0.0.1:8080 --agent-id hermes-a
sage-doctor --json
```

## sage-demo

Runs a demonstration handoff → claim → ACK delivery. `--single-agent` sends, decodes, and acknowledges one message to itself, exercising the same durable lifecycle as two-agent delivery. Supports `--url`, `--api-key`, `--workspace`, `--sender`, `--receiver`, `--single-agent`, `--content` (raw JSON object), `--timeout`, and `--json`.

```bash
sage-demo --single-agent
sage-demo --url http://127.0.0.1:8080
sage-demo --content '{"task": "check readiness"}'
```

## sage-tck

Runs the language-neutral conformance vectors (13 normative vectors: 6 valid + 7 invalid) against the installed protocol implementation. `--json` emits machine-readable output.

```bash
sage-tck
sage-tck --json
```

## sage-conform

Runs conformance checks; `--fuzz N` executes N deterministic malformed-wire mutations (seed configurable with `--seed`). The verified v0.2 campaign passes 1,000/1,000 mutations.

```bash
sage-conform
sage-conform --fuzz 1000
```

## sage-integrate

Generates adapter settings/profiles for Hermes, OpenClaw, and other platforms. `--list` shows available platforms; `--url`, `--agent-id`, and `--workspace` parameterize the generated settings.

```bash
sage-integrate --list
sage-integrate hermes --url http://127.0.0.1:8080 --agent-id hermes-a
sage-integrate openclaw --url http://127.0.0.1:8080 --agent-id claw-a
```

## sage-inspect

Inspects packet or run compression and semantic decisions — compression waterfall, semantic loss, receiver-known ratio, reference savings, pattern decisions, and replay context. `--json` emits machine-readable output.

```bash
sage-inspect --packet P...
sage-inspect --run run-... --json
```

## sage-qualify

Runs the v0.2 qualification runner: local concurrency, configured-database concurrency, ordering, pattern contention, chaos, vocabulary, and encode query-budget profiling. Flags include `--concurrency`, `--configured-concurrency`, `--workers`, `--messages`, `--vocabulary`, `--pattern-concurrency`, `--ordering-concurrency`, `--configured-ordering`, `--profile-encode`, `--profile-iterations`, and `--max-query-count`.

```bash
sage-qualify --concurrency --workers 8 --messages 20
sage-qualify --profile-encode --profile-iterations 30 --max-query-count 40
```

## sage-bench

Compares model-token economics across the protocol's required baselines. Takes a JSON file containing observations and price; it never fabricates provider measurements when configured external runtimes are unavailable.

```bash
sage-bench observations.json
```

## sage-sim

Offline communication simulator/evaluator over JSON/JSONL cases. Options include `--budget-tokens` (default 1200), `--workspace`, and `--output`.

```bash
sage-sim cases.jsonl --budget-tokens 1200 --output results.json
```

## sage-learn

Codebook and learned-language operations — inspecting and managing concepts, patterns, and the learned-language lifecycle.

```bash
sage-learn --help
```

Next: [Adapters](Adapters.md)
