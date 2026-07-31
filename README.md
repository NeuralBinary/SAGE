# SAGE

SAGE is a vendor-neutral semantic communication runtime and durable context bus for AI agents. It reduces repeated model context by carrying minimum-sufficient semantic state, content-addressed references, immutable deltas, learned compositional patterns, provenance, and receiver knowledge across agent boundaries.

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Version | v0.2 |
| Package version | 0.2.1 |
| Protocol | `sage/0.2` |
| Wire | `2` |
| License | MIT |

SAGE core is independent of model providers and agent frameworks. Native and protocol adapters connect the same runtime to Hermes, OpenClaw, Claude, OpenAI, A2A, MCP, REST, Python, and custom orchestrators.

## Start in five minutes

The local quick start requires Docker and stores its SQLite database in a named
volume. It is intended for evaluation and trusted local development.

Linux/macOS:

```bash
./quickstart.sh
```

Windows PowerShell:

```powershell
.\quickstart.ps1
```

The script starts SAGE, waits for health, and runs a real handoff → claim → ACK
check. Then open `http://127.0.0.1:8080/docs` or run another demonstration:

```bash
docker compose -f docker-compose.quickstart.yml exec -T sage \
  sage-demo --url http://127.0.0.1:8080
```

To verify any existing deployment from an installed wheel:

```bash
sage-doctor --url http://127.0.0.1:8080
sage-demo --url http://127.0.0.1:8080 --single-agent
```

Next, install the adapter for [Hermes](integrations/hermes/README.md),
[OpenClaw](integrations/openclaw/README.md), or use the REST/Python API.

## Design goals

SAGE v0.2 is built around these invariants:

- Meaning required for a downstream decision is preserved before compression is optimized.
- Critical semantics fail open to literals or references when confidence is insufficient.
- Agent-to-agent delivery is durable, at-least-once, lease-based, and idempotency-friendly.
- Receiver knowledge advances only after acknowledgement.
- Large content is referenced rather than repeatedly copied.
- State updates are represented as lossless deltas when a shared base state exists.
- Learned patterns remain compositional, inspectable, reversible, receiver-aware, trust-scoped, holdout-validated, drift-aware, and counterfactually validated.
- SAGE semantics do not depend on MCP, A2A, a model vendor, or a hidden model state.
- Production configuration fails closed for authentication, database selection, host policy, documentation exposure, and optional signature enforcement.
- Protocol, package, migration, schema, adapter, and conformance metadata remain locked to v0.2 until the project version is intentionally changed.
- Workspace and per-agent fairness, backpressure, ordering, partitioning, and idempotency protect shared infrastructure under retry storms and uneven tenants.
- Cross-runtime protocol identity is independently checked in Python, JavaScript, and Go; canonical MessagePack plus SHA-256 is the wire identity.

## Architecture

```text
Agent runtimes and model hosts
        |
        | native hooks / A2A / MCP / REST / Python
        v
+--------------------------------------------------+
| SAGE                                             |
| semantic firewall                               |
| semantic compiler and codebooks                 |
| recursive learned patterns                      |
| receiver knowledge                              |
| content-addressed references                    |
| immutable state and deltas                      |
| contradiction-aware semantic memory             |
| durable bus and acknowledgement                 |
| semantic pub/sub and routing                    |
| federation                                      |
| signatures, ACLs, encryption, TTLs              |
| Inspector, metrics, OpenTelemetry, replay       |
+---------------------------+----------------------+
                            |
                            v
                    PostgreSQL in production
```

SAGE owns semantic payload and shared-context behavior. A2A owns peer-agent lifecycle. MCP is an optional tool/context surface. Framework adapters use each host's supported lifecycle hooks.

## Install without Docker

Python 3.11 or newer is required. Install the release wheel and start a local
service with authentication disabled only on a trusted interface:

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install ./sage_agent_protocol-0.2.1-py3-none-any.whl
export SAGE_AUTH_REQUIRED=false  # PowerShell: $env:SAGE_AUTH_REQUIRED="false"
sage-api
```

In another terminal:

```bash
sage-doctor
sage-demo
```

Release assets:

```text
Python/runtime   -> sage_agent_protocol-0.2.1-py3-none-any.whl
Hermes Agent     -> sage-hermes-plugin-v0.2.1.zip
OpenClaw         -> sage-agent-openclaw-sage-0.2.1.tgz
Source           -> sage-plugin-v0.2.1.zip
Checksums        -> SHA256SUMS
```

Development installs may use `python -m pip install -e '.[dev]'`. Optional
dependency groups are `postgres`, `mcp`, `bench`, and `otel`.

## Production deployment

Production mode requires all of the following before the service will start:

- `SAGE_ENV=production`
- `SAGE_AUTH_REQUIRED=true`
- one or more service API keys of at least 32 characters
- a server database URL; SQLite is rejected
- `SAGE_AUTO_CREATE_SCHEMA=false`
- explicit `SAGE_ALLOWED_HOSTS`; wildcard-only configuration is rejected
- `SAGE_DOCS_ENABLED=false`

Run migrations before starting application workers:

```bash
PYTHONPATH=src alembic upgrade head
```

Compose requires `SAGE_POSTGRES_PASSWORD`, `SAGE_DATABASE_URL`, `SAGE_API_KEYS`, and `SAGE_ALLOWED_HOSTS` to be provided by the deployment environment:

```bash
docker compose -f docker-compose.yml up --build -d
```

The container runs as a non-root user with a read-only root filesystem, dropped Linux capabilities, `no-new-privileges`, a temporary writable `/tmp`, and automatic schema creation disabled.

TLS termination, network policy, secret storage, key rotation, backup policy, and database high availability remain deployment responsibilities.

## Core operation

The preferred integration boundary is below the model. Custom orchestrators use `SageRuntime` to hand off semantic state, poll durable context, acknowledge successful consumption, store references, create state, and inspect transport decisions. Model-visible tool calls are not required when the host runtime can integrate directly.

The primary durable bus flow is:

```text
handoff -> pending -> claimed -> acknowledged
                       |
                       +-> lease expiry -> claimable again
```

`GET /v1/bus/context/{receiver}` performs claim plus semantic decoding in one server round trip. `POST /v1/bus/ack-batch` acknowledges a successfully consumed set in one transaction-facing call. Framework adapters use these paths to avoid per-message decode and acknowledgement network fan-out.

Important REST surfaces:

| Area | Paths |
| --- | --- |
| Transport | `/v1/transport/send`, `/v1/transport/receive` |
| Durable bus | `/v1/bus/handoff`, `/v1/bus/context/{receiver}`, `/v1/bus/ack-batch`, `/v1/bus/{message_id}/nack` |
| References | `/v1/refs`, resolution, grants, invalidation, forwarding |
| State | state creation, lookup, delta generation, delta application |
| Concepts | concept registration, aliases, lifecycle, negotiation |
| Patterns | observation, lifecycle, counterfactual feedback, receiver reliability |
| Semantic memory | facts, contradictions, invalidation, dependencies |
| Routing | capabilities, subscriptions, publication, semantic route selection |
| Federation | peer administration, export, import |
| Inspector | packet and run inspection |
| Conformance | protocol schema, validation, TCK |
| Economics | structural/token/cost measurements and observed provider usage |

The generated OpenAPI document is the authoritative HTTP request/response contract when documentation is enabled in a non-production environment.

## Semantic safety

SAGE classifies semantic units by risk and epistemic type. Negation, amounts, identities, authorization, deadlines, production/staging markers, instructions, and constraints use the strict preservation path. Unknown or ambiguous meaning is retained as a literal or reference rather than silently mapped to an uncertain semantic code.

Semantic memory differentiates:

- fact
- observation
- inference
- hypothesis
- prediction
- preference
- instruction
- constraint

Conflicting claims coexist with provenance and confidence instead of overwriting each other. Dependency edges allow derived claims to be invalidated transitively when an upstream claim is no longer valid.

## Learned patterns

Pattern learning is persistent and compositional. Recurring semantic structures are first stored as candidates, then move through shadow validation and counterfactual evaluation before becoming active. Active patterns emit an ordinary concept code plus typed dynamic bindings. The flattened lossless composition remains available for interoperability and decoding.

Pattern decisions incorporate frequency, estimated savings, semantic stability, task utility, ambiguity, interoperability, source trust/diversity, holdout evidence, and receiver/model-specific fidelity. Receiver reliability is bound to provider/model build, runtime build/configuration, and task family. Low-fidelity or drifting patterns are suppressed for the affected receiver identity while remaining available where their measured fidelity is sufficient.

Pattern namespaces are hierarchical. Cooling and retirement prevent unbounded vocabulary growth. Foreign patterns imported through federation are observed locally and must earn local trust before active use.

See `docs/PATTERNS.md`.

## Content-addressed memory

Stored content uses a SHA-256 content identity with the `sage:sha256:` URI prefix. Authorization and lifetime policy are separate grants so identical bytes can be deduplicated without sharing authorization.

Grants support:

- workspace and owner scope
- agent ACLs
- allowed field paths
- memory tier
- TTL
- provenance
- optional AES-GCM at-rest encryption

Forwarding a reference delegates policy to the receiver without duplicating the underlying object. Selective resolution can return only permitted field paths.

## Protocol and conformance

SAGE v0.2 writes and reads only `sage/0.2`, wire `2`. The frozen protocol is in `spec/SAGE-0.2.md`. Normative JSON Schemas and the protobuf binding are under `spec/` and are packaged with the Python distribution.

Run the conformance checks with:

```bash
sage-tck --json
sage-conform --fuzz 1000
python scripts/conformance_matrix.py
python scripts/differential_fuzz.py --iterations 1000
python scripts/architecture_check.py
python scripts/invariant_check.py
python scripts/generate_protocol_artifacts.py --check
python scripts/release_check.py
```

Python, JavaScript, and Go independently consume the normative vectors. The protocol identity is canonical MessagePack bytes plus SHA-256. JSON remains a normalized/readable representation and is compared structurally where floating-point text can differ between language runtimes.

The release checker enforces package metadata, author/credit metadata, protocol/wire identity, one baseline migration, schema parity, TCK parity, repository hygiene, and v0.2 consistency.

## A2A and MCP boundaries

The A2A binding carries SAGE wire data as a structured data part. A2A retains ownership of peer discovery, task lifecycle, streaming, cancellation, and collaboration semantics.

MCP is an optional adapter. SAGE core imports no MCP types. Production MCP access is served through the authenticated `/mcp` mount on `sage-api`. Direct `sage-mcp` mode is restricted to development because it does not provide the FastAPI authentication wrapper.

## Native adapters

Hermes uses its native Python plugin entry point and lifecycle hooks. The adapter claims already-decoded SAGE context in one request and acknowledges the successful batch after the model call lifecycle completes.

OpenClaw uses the current `agent_turn_prepare` hook for same-turn context injection and `agent_end` for success-aware batch acknowledgement. Claimed run state is bounded in memory and failed runs are left for lease-based redelivery.

Claude, OpenAI, and other MCP-capable hosts use the authenticated remote MCP surface. A2A-capable peer runtimes may carry SAGE wire payloads directly.

See `docs/INTEGRATIONS.md`.

## Performance and latency

SAGE ships a deterministic local performance gate:

```bash
python scripts/performance_check.py --iterations 200
```

The gate measures core encode/decode and REST send/receive p50, p95, and maximum latency against explicit local ceilings. These measurements are engineering regression gates, not cross-machine service-level objectives. Production latency depends on database placement, network distance, embedding provider latency, payload size, storage tier, and enabled security features.

See `docs/PERFORMANCE.md`.

## Security

Production defaults and validation are intentionally strict. Service credentials control administrative surfaces and MCP. Agent-scoped credentials bind a key to a workspace/agent identity and cannot change that identity through request fields. Metrics are service-authenticated unless explicitly made public. Production interactive docs are disabled. Request bodies have a configured upper bound. Host headers are restricted in production.

Optional protections include AES-GCM reference encryption and Ed25519 packet/federation signatures. Signature-required mode will not start without a verification public key.

See `docs/SECURITY.md`, `docs/THREAT_MODEL.md`, and `docs/CONFIGURATION.md`.

## Observability

Prometheus metrics cover HTTP volume and latency. The Inspector exposes compression waterfall, semantic loss, receiver-known ratio, reference savings, pattern decisions, and replay context. Optional OpenTelemetry emits protocol measurements without placing content payloads in telemetry attributes.

See `docs/OPERATIONS.md` and `docs/ARCHITECTURE.md`.

## Verification

The repository verification process covers unit/integration behavior, semantic safety, protocol conformance, malformed-wire rejection, migrations, OpenAPI construction, packaging, adapter syntax/build checks, performance regression gates, repository consistency, and artifact re-validation.

The current verification record is `VERIFICATION.md`. A generated release report is provided beside the packaged artifacts during a verified build. Production-shape qualification uses `deploy/staging/compose.yml`: PostgreSQL, one migration job, three SAGE workers, TLS load balancing, end-to-end soak traffic, worker failover, database outage/readiness failure, and durable recovery.

Task-economics research uses the JSONL corpus format in `sage_plugin.corpus` and `scripts/model_matrix_benchmark.py`. Provider/model measurements must come from configured external runtimes; SAGE does not manufacture token, cost, latency, or task-success results when those runtimes are unavailable.

## Repository structure

```text
src/sage_plugin/          core runtime and Python adapters
spec/                     frozen protocol, schemas, protobuf binding
tck/                      language-neutral conformance vectors
tests/                    behavioral and protocol tests
integrations/             host-specific adapters
docs/                     operations, security, patterns, configuration
alembic/                  single v0.2 database baseline
scripts/                  release, performance, schema, and verification tools
```

## License and attribution

SAGE is licensed under the MIT License.

Author: NeuralBinary

Credits: @NeuralBinary, @ro0ti

Repository: https://github.com/NeuralBinary/SAGE
