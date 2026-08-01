
# Production

Production mode fails closed: `SAGE_ENV=production` requires authentication, a server (PostgreSQL) database, managed migrations, explicit allowed hosts, and disabled interactive docs — otherwise the service refuses to start (full rules in [Configuration](Configuration.md)).

## The production Compose topology (docker-compose.yml)

The root `docker-compose.yml` is the single-node production topology:

- **postgres** — `postgres:18-alpine`, database/user `sage`, password from `SAGE_POSTGRES_PASSWORD` (required), with a `pg_isready` healthcheck.
- **migrate** — one-shot service running `alembic upgrade head` with production settings (`SAGE_ENV=production`, `SAGE_AUTO_CREATE_SCHEMA=false`, `SAGE_DOCS_ENABLED=false`, `SAGE_AUTH_REQUIRED=true`), started only after postgres is healthy, `restart: "no"`.
- **sage** — the application container, started only after `migrate` completes successfully. Runs with `read_only: true`, a temporary writable `/tmp`, `cap_drop: [ALL]`, and `security_opt: [no-new-privileges:true]`. Requires `SAGE_DATABASE_URL`, `SAGE_API_KEYS`, and `SAGE_ALLOWED_HOSTS` from the environment.

Bring it up with (all four variables must be provided by the deployment environment):

```bash
docker compose -f docker-compose.yml up --build -d
```

Required environment: `SAGE_POSTGRES_PASSWORD`, `SAGE_DATABASE_URL`, `SAGE_API_KEYS`, `SAGE_ALLOWED_HOSTS`. The container runs as a non-root user (`sage`) with automatic schema creation disabled (the Dockerfile also sets `SAGE_AUTO_CREATE_SCHEMA=false`).

## Staging / horizontally scaled topology (deploy/staging/compose.yml)

The production-shape staging topology (also used as a CI gate) is:

```text
client
  |
  | https://host:8443
  v
gateway (nginx:1.29-alpine, TLS 1.2/1.3, least_conn)
  |--------------------|--------------------|
  v                    v                    v
sage-a              sage-b              sage-c      (3 independent SAGE workers,
  |--------------------|--------------------|         non-root, read-only,
  v                                            )      cap_drop ALL, no-new-privileges)
migrate (one-shot: alembic upgrade head)
  |
  v
postgres (postgres:18-alpine, volume sage_staging_pg)
```

- **gateway** — nginx TLS load balancer on port `8443`; upstream `sage_pool` uses `least_conn` across `sage-a/b/c:8080` (`max_fails=3`, `fail_timeout=5s`), TLSv1.2/TLSv1.3, `client_max_body_size 50m`, `proxy_read_timeout 120s`, forwards `X-Forwarded-Proto https` and `X-Request-ID`. The gateway container is `read_only` with tmpfs for `/var/cache/nginx` and `/var/run`.
- **migrate** — one-shot Alembic service (`alembic upgrade head`) that must complete successfully before any worker starts (`depends_on: migrate: service_completed_successfully`). SAGE application nodes never race migrations.
- **sage-a / sage-b / sage-c** — three identical hardened workers (shared YAML anchor): `SAGE_ENV=production`, `SAGE_AUTH_REQUIRED=true`, `SAGE_AUTO_CREATE_SCHEMA=false`, `SAGE_DOCS_ENABLED=false`, `SAGE_METRICS_PUBLIC=false`, pool `SAGE_DB_POOL_SIZE=20`, `SAGE_DB_MAX_OVERFLOW=40`; `read_only: true`, `tmpfs: [/tmp]`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`.

Run:

```bash
docker compose -f deploy/staging/compose.yml up --build -d
```

with `SAGE_POSTGRES_PASSWORD`, `SAGE_API_KEYS`, `SAGE_ALLOWED_HOSTS`, `SAGE_TLS_CERT`, and `SAGE_TLS_KEY` provided by the deployment environment.

## TLS certificates

- `SAGE_TLS_CERT` — path to the TLS certificate file mounted into nginx at `/etc/nginx/tls/tls.crt`.
- `SAGE_TLS_KEY` — path to the TLS private key file mounted into nginx at `/etc/nginx/tls/tls.key`.

Both are required by the staging/gateway Compose file (the compose file fails fast with `:?` required-variable errors if they are missing). For CI, a one-day self-signed certificate is generated with:

```bash
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -keyout server.key -out server.crt \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost"
```

TLS termination, network policy, secret storage, key rotation, backup policy, and database high availability remain deployment responsibilities — SAGE does not manage them.

## Migrations

- Production requires `SAGE_AUTO_CREATE_SCHEMA=false`; schema is managed exclusively by Alembic.
- v0.2 has a single baseline migration: `0001_sage_0_2`. A fresh database upgrades directly to it; `alembic check` reports no new upgrade operations.
- Run as a one-shot step before application workers start:

```bash
PYTHONPATH=src alembic upgrade head
```

Both supplied Compose topologies run this in a dedicated `migrate` service so horizontally scaled workers do not race schema changes.

## Containers and healthchecks

- The application image is built from the repo `Dockerfile` (`python:3.14-slim`, non-root user `sage`, `SAGE_AUTO_CREATE_SCHEMA=false`, installs `.[postgres,mcp]`, runs uvicorn on `0.0.0.0:8080` with `--proxy-headers`).
- Built-in healthcheck: `GET /health/live` every 30 s (`--interval=30s --timeout=3s --start-period=10s --retries=3`).
- Application containers are `read_only` with a temporary writable `/tmp`, dropped capabilities, and `no-new-privileges`.

## Database and delivery in production

- SQLite is for local/single-process development. Production uses PostgreSQL; the durable bus uses row locks with `SKIP LOCKED` where supported plus claim leases. Delivery is at-least-once — downstream side effects must be idempotent by message/correlation ID.
- The connection pool is configurable: `SAGE_DB_POOL_SIZE` (default 10), `SAGE_DB_MAX_OVERFLOW` (default 20), `SAGE_DB_POOL_TIMEOUT_SECONDS` (default 30), `SAGE_DB_POOL_RECYCLE_SECONDS` (default 1800). The staging topology uses pool size 20 / max overflow 40.
- `POST /v1/maintenance/cleanup` expires cache/ref grants/messages/audits and runs pattern garbage collection; reference deletion is reachability-based, and state cleanup starts from checkpoints/receiver pointers and follows parent ancestry before removing states older than `SAGE_STATE_RETENTION_DAYS`.
- Back up PostgreSQL plus ref encryption/signing keys separately; treat federation trust configuration as security-sensitive configuration.

## Monitoring and metrics

- **Prometheus**: metrics cover HTTP volume and latency (`sage_http_requests_total`, `sage_http_request_seconds`). Metrics are service-authenticated unless `SAGE_METRICS_PUBLIC=true` is intentionally set (production topology keeps it `false`).
- **Inspector**: JSON, CLI (`sage-inspect`), and HTML surfaces expose compression waterfall, semantic loss, receiver-known ratio, reference savings, pattern decisions, and replay context. `/v1/inspect/{packet_id}`, `/v1/inspect/run/{run_id}`, and `/v1/runs/{run_id}/replay`. Agent-scoped credentials can inspect only packets in their workspace where they are sender/receiver.
- **OpenTelemetry**: optional (`.[otel]` + `SAGE_OTEL_ENABLED=true`). SAGE emits `gen_ai.operation.name` plus `sage.*` protocol metrics; it emits operational metadata by default — never message content, literals, reference payloads, secrets, credentials, or raw model prompts as span attributes. W3C trace context propagates through wire v2 so one distributed trace can correlate agent, SAGE, database, adapter, and downstream operations.

## Staging qualification

- `scripts/soak_cluster.py` measures completed handoff → claim → ACK lifecycles through the TLS load balancer; default duration is 24 hours (CI runs a short gate).
- `scripts/cluster_chaos.py` can pause an application node, verify load-balancer failover, disrupt PostgreSQL, require readiness failure, restore the database, and verify durable delivery recovery.
- The dispatch-only scale workflow (`scale-qualification`) accepts vocabulary-size and soak-duration inputs for sustained release-candidate qualification.

Next: [FAQ](FAQ.md)
