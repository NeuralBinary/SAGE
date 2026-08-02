# SAGE

SAGE is a vendor-neutral semantic communication runtime and durable context bus for AI agents. It reduces repeated model context by carrying minimum-sufficient semantic state, content-addressed references, immutable deltas, learned compositional patterns, provenance, and receiver knowledge across agent boundaries.

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Version | v0.2 |
| Package version | 0.2.6 |
| Protocol | `sage/0.2` |
| Wire | `2` |
| License | MIT |

SAGE core is independent of model providers and agent frameworks. Native and protocol adapters connect the same runtime to Hermes, OpenClaw, Claude, OpenAI, A2A, MCP, REST, Python, and custom orchestrators.

## Table of Contents

- [Quickstart](#quickstart)
  - [Docker quickstart](#docker-quickstart)
  - [Python release install](#python-release-install)
  - [Hermes plugin](#hermes-plugin)
  - [OpenClaw plugin](#openclaw-plugin)
- [Design goals](#design-goals)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Command-line tools](#command-line-tools)
- [Production deployment](#production-deployment)
- [Core operation](#core-operation)
- [Semantic safety](#semantic-safety)
- [Learned patterns](#learned-patterns)
- [Content-addressed memory](#content-addressed-memory)
- [Protocol and conformance](#protocol-and-conformance)
- [A2A and MCP boundaries](#a2a-and-mcp-boundaries)
- [Native adapters](#native-adapters)
- [Performance and latency](#performance-and-latency)
- [Security](#security)
- [Observability](#observability)
- [Verification](#verification)
- [Development](#development)
- [Release process](#release-process)
- [Repository structure](#repository-structure)
- [License and attribution](#license-and-attribution)

## Quickstart

### Docker quickstart

The local Docker quick start requires Docker with the Compose plugin and stores its SQLite database in a named volume. It is intended for evaluation and trusted local development.

Linux/macOS:

```bash
./quickstart.sh
```

Windows PowerShell:

```powershell
.\quickstart.ps1
```

The script starts SAGE from `docker-compose.quickstart.yml`, waits for health, and runs a real handoff → claim → ACK check. Then open `http://127.0.0.1:8080/docs` or run another demonstration:

```bash
docker compose -f docker-compose.quickstart.yml exec -T sage \
  sage-demo --url http://127.0.0.1:8080 --single-agent
```

### Python release install

Python 3.11 or newer is required. Download the v0.2.6 release wheel from the
[GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6), then
install it and start a local service with authentication disabled only on a
trusted interface:

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install https://github.com/NeuralBinary/SAGE/releases/download/v0.2.6/sage_agent_protocol-0.2.6-py3-none-any.whl
export SAGE_AUTH_REQUIRED=false  # PowerShell: $env:SAGE_AUTH_REQUIRED="false"
sage-api
```

`sage-api` serves on `0.0.0.0:8080`. In another terminal, verify the service and
run a self-addressed delivery:

```bash
sage-doctor
sage-demo --single-agent
```

`sage-doctor` checks liveness, database readiness, `sage/0.2` wire identity,
handoff, context claim, ACK, and removal from the pending mailbox.
`sage-demo --single-agent` sends, decodes, and acknowledges one message to
itself, which exercises the same durable lifecycle as two-agent delivery.

### Hermes plugin

Download `sage-hermes-plugin-v0.2.6.zip` from the
[v0.2.6 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6),
then install the plugin:

```bash
unzip sage-hermes-plugin-v0.2.6.zip
cd sage-hermes-plugin-v0.2.6
./install.sh
```

Set `SAGE_URL`, `SAGE_AGENT_ID`, and `SAGE_WORKSPACE` in the environment used to
start Hermes. Set `SAGE_API_KEY` when authentication is enabled. Full Docker and
Windows instructions are in `integrations/hermes/README.md`.

### OpenClaw plugin

Download `sage-agent-openclaw-sage-0.2.6.tgz` from the
[v0.2.6 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6),
then install the native plugin:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.6.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

Configure `url`, `agentId`, `workspace`, and optionally `apiKey`. Full details
are in `integrations/openclaw/README.md`.

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

## Configuration

SAGE reads `SAGE_`-prefixed environment variables (and an optional `.env` file).
Development defaults favor local operation; `SAGE_ENV=production` enables strict
fail-closed validation. The complete reference, including every documented
default, is `docs/CONFIGURATION.md`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SAGE_ENV` | `development` | Runtime environment; `production` enables strict startup validation. |
| `SAGE_DATABASE_URL` | `sqlite:///$HOME/sage.db` | SQLAlchemy database URL; the default is the current user's home-directory `sage.db`, independent of the working directory. Production rejects SQLite. |
| `SAGE_AUTH_REQUIRED` | `false` | Enables bearer authentication. Production requires `true`. |
| `SAGE_API_KEYS` | empty | Comma-separated service keys, each at least 32 characters when auth is enabled. |
| `SAGE_AGENT_KEYS` | empty | JSON mapping from secret key to `agent` or `workspace:agent` scope. |
| `SAGE_ALLOWED_HOSTS` | empty | Comma-separated Host allowlist. Production requires explicit entries. |
| `SAGE_DOCS_ENABLED` | `true` | Exposes interactive docs/OpenAPI. Production requires `false`. |
| `SAGE_AUTO_CREATE_SCHEMA` | `true` | Development schema creation. Production requires `false` and Alembic migrations. |
| `SAGE_METRICS_PUBLIC` | `false` | Allows unauthenticated Prometheus metrics when intentionally enabled. |

Pool sizing, payload and token budgets, semantic compiler and codebook
thresholds, pattern learning policy, embeddings, references, cache, bus and
retention windows, signatures, federation, observability, and routing weights
are all configurable; see `docs/CONFIGURATION.md` for the full table. A local
environment template ships as `.env.example`.

## Command-line tools

The wheel installs these commands:

| Command | Purpose |
| --- | --- |
| `sage-api` | Start the HTTP service on `0.0.0.0:8080`. |
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
| `sage-mcp` | Standalone MCP adapter mode; development only because it lacks the FastAPI authentication wrapper. |

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

SAGE v0.2 writes and reads only `sage/0.2`, wire `2`. The frozen protocol is in `spec/SAGE-0.2.md`. Normative JSON Schemas and the protobuf binding are under `spec/` and are packaged with the Python distribution. The language-neutral TCK in `tck/` carries 13 normative vectors (6 valid, 7 invalid), consumed independently by Python, JavaScript, and Go.

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

### Semantic context compression benchmark

`scripts/compression_benchmark.py` measures how twelve context-compression strategies (the RFC "Phoenix" variants) carry a fixed six-turn conversation, separating three compression levels:

- **transport compression** — wire bytes actually transmitted (canonical JSON and MessagePack),
- **model-visible compression** — the tokens the receiver model must consume (input/output of the transmitted representation),
- **semantic compression** — downstream task success, state reconstruction, and per-fact-type fidelity against an embedded ground-truth answer key.

Variants 1–8 are plain serialization/string strategies; variants 9–12 run the real `SageCodec` (codebooks only; codebooks + learned patterns; references + state deltas; full SAGE with ACKed receiver knowledge). The benchmark is fully deterministic: no RNG, no wall-clock output, a fixed timestamp, pinned packet ids, and an isolated scratch database per variant.

Honest headline from the deterministic run (all numbers reproducible locally, see below): the SAGE codebook variant (v09) carries the full conversation in **1,172 wire bytes vs 2,027 for the full-context baseline (v01) — about 42% less wire — with full semantic fidelity (task success 1.0, all fidelity checks 1.0)**. Its amortization break-even is 5 uses: the 675-byte codebook setup is repaid after five exchanges of this fixture. Adding learned patterns (v10) costs more setup (946 bytes, break-even 9) and saves less per use on a conversation this short; the reference/delta (v11) and ACKed-knowledge (v12) variants post negative per-use savings (break-even equals setup cost, i.e. they do not break even within the fixture). Patterns amortize over longer conversations than this fixture shows — the benchmark measures the RFC's "shared shorthand may initially cost more" question honestly rather than manufacturing a win. The ACKed-knowledge rows are honest that this short fixture cannot repay receiver-knowledge setup.

Run it (deterministic, no provider required):

```bash
uv run --with '.[dev,mcp]' python scripts/compression_benchmark.py            # printed tables
uv run --with '.[dev,mcp]' python scripts/compression_benchmark.py --out DIR  # + JSON/CSV artifacts
```

The model-evaluation harness (`scripts/model_eval_harness.py`) measures the same variants' downstream task success on real model runtimes through configured external adapters — cold vs warm receivers, at least two distinct model families, and the RFC's six-column public result table. It requires an `--adapters` config (see its module docstring) and `SAGE_BENCH_LLM_PROVIDER`; with neither it prints `not run, no provider` and exits 0 — provider numbers are never fabricated. With `--record-feedback` it also records each SAGE variant's measured task success into the codec's pattern store (`PatternStore.record_feedback`, `runtime.feedback` semantics) as an additive `feedback` JSON summary key, with zero wire-byte change. Raw artifacts are written outside the repository.

```bash
SAGE_BENCH_LLM_PROVIDER=fake uv run --with '.[dev,mcp]' \
    python scripts/model_eval_harness.py --adapters adapters.json --output /path/outside/repo
```

The harness also ships a sealed evaluation mode (issue #22): with `--sealed`
the adapter sees only the compact packet — never source content or answer
keys — scores are computed harness-side against the private answer key, and
`--held-out` evaluates the SAGE variants on unseen conversations with a frozen
codebook and a lifecycle-primed warm receiver. See the
[Benchmark page](https://neuralbinary.github.io/SAGE/Benchmark/) of the docs
site.

No-fabrication rule: every figure in these tools is either deterministic (measured locally) or comes from a configured external runtime's reply; a missing provider is reported as `not run, no provider`, never estimated.

## Development

Install an editable development environment with the dev tooling:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Optional dependency groups are `postgres`, `mcp`, `bench`, and `otel`. Run the
test, lint, security, and release-consistency gates:

```bash
pytest -q
ruff check src tests scripts
python scripts/security_check.py
python scripts/release_check.py
```

`make verify` runs the full local sequence: security, architecture, invariants,
generated schema/artifact checks, TCK, the three-runtime conformance matrix,
differential fuzzing, chaos recovery, the full test suite, latency and query
budget gates, byte compilation, cleanup, and the final source-tree release
consistency check. The TCK vectors are exercised per runtime with:

```bash
sage-tck --json
python scripts/conformance_matrix.py
```

## Release process

Version identity is locked across `pyproject.toml`, `plugin.json`, the Python
package, the Hermes manifest and adapter, the OpenClaw package and manifest, the
spec, the TCK, and this documentation. Release commits prepare that identity
(e.g. `release: prepare v0.2.6`).

Pushing a tag matching `v*` triggers the `.github/workflows/release.yml`
workflow, which:

- installs and qualifies the Python source (`pytest`, `release_check.py`,
  generated spec and protocol artifact checks);
- builds and qualifies the OpenClaw adapter (type-check, build, TCK);
- builds every release asset with `scripts/build_release.py --output dist`;
- verifies the packaged assets with `scripts/package_check.py` and the
  OpenClaw adapter check;
- tests the installed wheel in a fresh virtual environment;
- runs the Docker quick-start gate;
- publishes the GitHub release with the asset set.

Release assets:

```text
Python/runtime   -> sage_agent_protocol-0.2.6-py3-none-any.whl
Hermes Agent     -> sage-hermes-plugin-v0.2.6.zip
OpenClaw         -> sage-agent-openclaw-sage-0.2.6.tgz
Source           -> sage-plugin-v0.2.6.zip
Verification     -> SAGE-v0.2.6-VERIFICATION.md
Checksums        -> SAGE-v0.2.6-SHA256SUMS.txt
```

The release notes and verification records for the current release are
`RELEASE-v0.2.6.md` and `VERIFICATION.md`.

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
