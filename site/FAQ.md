
# FAQ

## Why does `sage-api` fail to start from a read-only or unexpected directory?

This was a bug fixed in **v0.2.2** (Issue #1). Earlier versions defaulted to `sqlite:///./sage.db`, which resolved relative to the process working directory — starting the service from a non-writable or unexpected directory could fail or create an unexpected database file there.

Since v0.2.2, the default database is the current user's home directory: `sqlite:///$HOME/sage.db`, independent of the working directory. If you set `SAGE_DATABASE_URL`, that explicit value is authoritative and preserved exactly. See [Quickstart](Quickstart.md) and [Configuration](Configuration.md).

## How do I change the database?

Set `SAGE_DATABASE_URL` to any SQLAlchemy URL. For example:

```bash
export SAGE_DATABASE_URL=postgresql+psycopg://sage:password@dbhost:5432/sage
```

An explicit value always takes precedence over the default `sqlite:///$HOME/sage.db`. The `postgres` optional dependency group (`psycopg[binary]`) is required for PostgreSQL URLs. Production requires a server database — SQLite is rejected in `SAGE_ENV=production`. After changing the URL in production, run migrations (`PYTHONPATH=src alembic upgrade head`) before starting application workers.

## How does authentication work?

Authentication is bearer-token based, enabled with `SAGE_AUTH_REQUIRED=true`:

- **Service keys** (`SAGE_API_KEYS`, comma-separated or JSON array): authorize control-plane operations and MCP; each key must be at least 32 characters.
- **Agent keys** (`SAGE_AGENT_KEYS`): a JSON mapping from secret key to a scope of `agent` or `workspace:agent`. An agent credential binds the request to that workspace/agent identity, and request fields cannot change it.
- Service and agent keys must be disjoint sets, and both must be ≥ 32 characters when auth is enabled.
- Clients send `Authorization: Bearer <key>`. Adapters accept an `apiKey`/`SAGE_API_KEY` setting for this.

Production requires `SAGE_AUTH_REQUIRED=true` and at least one service key. Metrics stay service-authenticated unless `SAGE_METRICS_PUBLIC=true` is intentionally set. See [Configuration](Configuration.md).

## Why does production reject SQLite?

SQLite is a local, single-process embedded database. Production mode requires a server database because SAGE's durable bus, horizontal scaling, row-lock claim handling (`SKIP LOCKED`), quotas, and multi-worker deployments depend on a shared server database. `SAGE_ENV=production` fails at startup if `SAGE_DATABASE_URL` starts with `sqlite`. Use PostgreSQL in production (`postgresql+psycopg://...`).

## How do I run multiple agents?

Each agent that needs a separate mailbox gets a unique identity:

- **Hermes**: unique `SAGE_AGENT_ID` per agent (e.g. `hermes-a`, `hermes-b`).
- **OpenClaw**: unique `agentId` per agent.
- **REST/Python**: pass the receiver/sender identity in bus calls, and claim per-agent with `GET /v1/bus/pull/{agent}` or `GET /v1/bus/context/{receiver}`.

Messages are deterministically partitioned (`SAGE_BUS_PARTITION_COUNT`, default 64), so partition-scoped workers can claim only their shard. An optional ordering key allocates contiguous per-stream sequence numbers while unrelated streams remain parallel. Workspace and per-agent quotas apply independently.

## What is an idempotency key?

Mutating HTTP routes that support retryable writes honor the `X-Idempotency-Key` header. A key is scoped by authenticated principal/workspace and route:

- Repeating the same key **and** request returns the stored logical result (no duplicate write).
- Reusing the key with a **different** request is rejected.

Server-side idempotency records live for `SAGE_IDEMPOTENCY_TTL_SECONDS` (default 86400 s = 24 h). Idempotency keys, along with `message_id`/`correlation_id`, are how consumers stay safe under at-least-once redelivery and retry storms.

## How do I acknowledge messages?

- Single: `POST /v1/bus/{message_id}/ack` (body: receiver/workspace).
- Batch: `POST /v1/bus/ack-batch` with `message_ids` — acknowledges a successfully consumed set in one transaction-facing call.
- NACK: `POST /v1/bus/{message_id}/nack` returns an unacknowledged message to pending.

Acknowledge **only after successful consumption**: receiver knowledge advances only on ACK, never on pull/claim alone. Unacknowledged claims expire after the claim lease (`SAGE_BUS_CLAIM_LEASE_SECONDS`, default 60 s) and become claimable again — this is how crashed consumers are recovered.

## How do I upgrade from v0.2.1 to v0.2.2?

v0.2.2 is a drop-in patch release:

1. Install the new artifacts — `sage_agent_protocol-0.2.2-py3-none-any.whl`, `sage-hermes-plugin-v0.2.2.zip`, and/or `sage-agent-openclaw-sage-0.2.2.tgz` ([Quickstart](Quickstart.md)).
2. Verify your deployment's `SAGE_DATABASE_URL` — an explicit value continues to take precedence over the new home-directory default.
3. No data migration is required: protocol `sage/0.2`, wire version `2`, the `0001_sage_0_2` migration baseline, and the 13 TCK vectors are unchanged, so v0.2.1 peers and v0.2.2 peers interoperate.

## How do I roll back?

v0.2.1 remains available on the GitHub releases page with its original assets. To roll back:

1. Reinstall the v0.2.1 artifacts.
2. Restore your previous `SAGE_DATABASE_URL` configuration.

Because the database schema, protocol, and wire version are unchanged between 0.2.1 and 0.2.2, no data migration is required to roll back.

## Other questions

- **What is the default database path?** `$HOME/sage.db` (SQLite) — see [Configuration](Configuration.md).
- **What does `sage-doctor` check?** Liveness, database readiness, `sage/0.2` wire identity, handoff, context claim, ACK, and removal from the pending mailbox ([CLI-Tools](CLI-Tools.md)).
- **Can I use MCP in production?** Yes — through the authenticated `/mcp` mount on `sage-api`. Direct `sage-mcp` mode is development-only because it lacks the FastAPI authentication wrapper ([Adapters](Adapters.md)).
- **What latency should I expect?** The repo ships deterministic local regression gates (core encode p95 ≤ 40 ms, core decode p95 ≤ 10 ms, HTTP send p95 ≤ 75 ms, HTTP receive p95 ≤ 50 ms locally on SQLite). These are engineering regression gates, not cross-machine service-level objectives — production latency depends on database placement, network distance, embedding provider latency, payload size, storage tier, and enabled security features.
- **Where is the generated OpenAPI document?** Interactive docs at `/docs` when `SAGE_DOCS_ENABLED=true` (non-production). The generated OpenAPI document is the authoritative HTTP request/response contract: OpenAPI 3.1.0, title `SAGE`, 81 paths.

Back to [Home](index.md)
