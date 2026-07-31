# Operations

## Database

SQLite is for local/single-process development. Use PostgreSQL in production. Set `SAGE_AUTO_CREATE_SCHEMA=false` and run `alembic upgrade head` during deploy. v0.2 has one baseline migration: `0001_sage_0_2`.

## Horizontal scaling and delivery

The durable bus uses row locks with `SKIP LOCKED` where supported plus claim leases. Delivery is at-least-once; downstream side effects must be idempotent by message/correlation ID.

## Maintenance

`POST /v1/maintenance/cleanup` expires cache/ref grants/messages/audits and runs pattern garbage collection. Pattern GC moves old active vocabulary through cooling and retirement rather than allowing unlimited codebook growth.

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

The release checker enforces version `0.2.0`, protocol `sage/0.2`, wire `2`, one baseline migration, repo/package schema equality, spec/protobuf equality and TCK equality.

## Backups

Back up PostgreSQL plus ref encryption/signing keys separately. Treat federation trust configuration as security-sensitive configuration.
