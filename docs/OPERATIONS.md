# Operations

## Database

SQLite is for local/single-process development. Use PostgreSQL in production. Set `SAGE_AUTO_CREATE_SCHEMA=false` and run `alembic upgrade head` as a one-shot deployment step before application workers start. v0.2 has one baseline migration: `0001_sage_0_2`. The supplied Compose topologies use a dedicated migration service so horizontally scaled workers do not race schema changes.

## Horizontal scaling and delivery

The durable bus uses row locks with `SKIP LOCKED` where supported plus claim leases. Delivery is at-least-once; downstream side effects must be idempotent by message/correlation ID.

## Maintenance

`POST /v1/maintenance/cleanup` expires cache/ref grants/messages/audits and runs pattern garbage collection. Reference deletion is reachability-based: active grants, unacknowledged packets, retained audit/replay packets, and receiver-known refs remain roots. Pattern GC moves old active vocabulary through cooling and retirement. State history remains immutable; checkpoints bound normal replay cost without deleting ancestry needed for deterministic reconstruction.

## Inspector and OpenTelemetry

Use:

```bash
sage-inspect --packet P...
sage-inspect --run run-... --json
```

`/v1/inspect/{packet_id}` and `/v1/inspect/run/{run_id}` expose compression waterfalls, semantic loss, receiver-known ratio, pattern/ref decisions and token estimates. Agent-scoped credentials can inspect only packets in their workspace where they are sender/receiver.

Install `.[otel]` and set `SAGE_OTEL_ENABLED=true` for OpenTelemetry spans/counters. SAGE emits `gen_ai.operation.name` plus `sage.*` protocol metrics; configure exporters through your normal OTel SDK/environment deployment.

## Conformance

Run before adapter/deployment qualification:

```bash
sage-conform
sage-conform --fuzz 1000
python scripts/release_check.py
```

The release checker enforces source version `0.2.7`, protocol `sage/0.2`, wire `2`, one baseline migration, repo/package schema equality, spec/protobuf equality and TCK equality. `python scripts/conformance_matrix.py` requires Python, JavaScript, and Go. `python scripts/differential_fuzz.py` compares canonical MessagePack identity and validation behavior across the independent runtimes.

## Backups

Back up PostgreSQL plus ref encryption/signing keys separately. Treat federation trust configuration as security-sensitive configuration.

## Cluster staging and soak qualification

`deploy/staging/compose.yml` provisions PostgreSQL, a one-shot migration service, three independent SAGE workers, and a TLS Nginx load balancer. The runtime workers are non-root, read-only, capability-dropped containers.

Run end-to-end soak traffic through the load balancer with `scripts/soak_cluster.py`. Every counted operation completes handoff, claim, decode transport, and acknowledgement. `scripts/cluster_chaos.py` pauses a worker, verifies load-balancer failover, can stop PostgreSQL, requires readiness to fail, restores PostgreSQL, and verifies durable delivery recovery. The default soak duration is 24 hours; CI uses a shorter gating duration while preserving the same lifecycle.
The `scale-qualification` workflow is dispatch-only and accepts vocabulary-size and soak-duration inputs for sustained release-candidate qualification.

## Queue fairness and ordering

Workspace and per-agent handoff quotas are consumed atomically. Failed agent-scoped quota checks cannot consume shared workspace allowance. Queue state reports normal, degraded, throttled, or unavailable. Throttled/unavailable states reject new work with retryable HTTP status. Messages are deterministically partitioned, and an optional ordering key allocates a contiguous per-stream sequence while unrelated streams remain parallel.

All mutating HTTP routes that support retryable writes honor `X-Idempotency-Key`. A key is scoped by authenticated principal/workspace and route; reusing it with a different request is rejected.

## Reachability cleanup

Reference cleanup retains live grants, undelivered packets, receiver knowledge, and configured audit/replay roots. Immutable state cleanup starts from checkpoints, receiver current-state pointers, undelivered packets, and configured audit/replay roots, then follows parent ancestry before removing states older than `SAGE_STATE_RETENTION_DAYS`. Learned patterns cool and retire rather than being physically removed from semantic history.
