# SAGE v0.2 Verification Report

## Release identity

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Public version | v0.2 |
| Package version | 0.2.3 |
| Protocol | sage/0.2 |
| Wire | 2 |
| Database baseline | 0001_sage_0_2 |

This report records qualification of the clean v0.2 first-deployment baseline on July 31, 2026. No pre-v0.2 protocol reader, compatibility layer, or migration chain is shipped.

## v0.2.3 patch verification

v0.2.3 is a patch release over the v0.2.2 baseline. Protocol `sage/0.2`, wire
version `2`, the `0001_sage_0_2` migration baseline, and the 13 normative TCK
vectors are unchanged.

Verified for v0.2.3:

- Full CI matrix green on the merged main (`ci` workflow, commit
  `d2f6ddad`): Python 3.11/3.12/3.13/3.14 (ruff, TCK, conformance matrix
  incl. JavaScript and Go, differential fuzzing, chaos suite, compileall,
  pytest, latency gate, qualification), PostgreSQL qualification,
  OpenClaw adapter (type-check, build, TCK, package check), package job
  (release_check, build_release, package_check, Docker quick start),
  dependency audit, and the staging TLS cluster (soak, TLS delivery,
  worker/database recovery, stop logs).
- `scripts/release_check.py` passes every version-consistency, protocol,
  migration, schema, spec/protobuf, TCK-drift, and artifact gate for
  v0.2.3 (`{"ok":true,"version":"0.2.3",...}`).
- Full automated suite: 113 tests pass (pytest phase runs without the `mcp`
  extra; see Issue #11 for the mcp single-run session-manager limitation).
- `scripts/build_release.py` produces all six v0.2.3 assets, and
  `scripts/package_check.py` verifies the source archive, wheel, Hermes
  plugin, and OpenClaw package for v0.2.3.
- The packaged wheel `sage_agent_protocol-0.2.3-py3-none-any.whl` installs
  into a fresh virtual environment and imports as 0.2.3.

The sections below record the v0.2.1 baseline qualification and remain the
reference for surfaces unchanged by v0.2.3.

## v0.2 hardening scope

The release implements the full v0.2 hardening program across interoperability, concurrency, failure recovery, semantic reliability, scaling, observability, distribution, and release engineering.

Implemented capabilities include:

- multi-runtime protocol conformance across Python, JavaScript, and Go;
- PostgreSQL/TLS three-node staging topology with migration-before-start orchestration;
- end-to-end soak and worker/database disruption runners;
- deterministic property and differential protocol checks;
- decomposed HTTP domain routers and separated pattern structure/policy/reliability layers;
- generated protocol artifacts with repository/package drift checks;
- source-diverse holdout validation and receiver/model/task reliability calibration;
- rolling reliability windows and automatic safe fallback on drift;
- model identity pinned to provider, model build, runtime build, and configuration identity;
- Merkle-partitioned codebook synchronization;
- immutable content-addressed state checkpoints;
- reachability-aware reference and state cleanup;
- information-flow sensitivity propagation;
- workspace and agent quotas, backpressure states, deterministic queue partitioning, and ordered streams;
- idempotent mutating HTTP operations and durable at-least-once delivery;
- critical/optional failure-domain isolation;
- three-runtime TCK and differential fuzzing;
- deterministic chaos qualification and explicit invariant catalog;
- HTML and CLI Inspector surfaces with compression waterfall and decision trace;
- provider/infrastructure/retrieval/retry economics and task utility per transmitted bit;
- reproducible JSONL corpus format and model-matrix benchmark runner;
- controlled candidate/shadow/holdout/active learned-language lifecycle;
- deterministic signed codebook releases;
- OpenTelemetry integration with W3C trace context and content-safe default attributes;
- MCP isolated to the adapter boundary;
- A2A binding kept at the peer-agent envelope boundary;
- protocol wire version held at 2 throughout the hardening release.

## Functional qualification

The final working tree contains 107 automated tests. The full suite passes.

Coverage includes transport encode/decode, durable handoff/claim/ACK/NACK, lease recovery, partition claims, ordering, idempotency, quotas, backpressure, identity-scoped authorization, semantic memory, contradictions, causal invalidation, information-flow labels, content-addressed references, selective disclosure, zero-copy forwarding, immutable states, checkpoints, reachability cleanup, concepts, learned patterns, source trust, holdout validation, counterfactual validation, receiver calibration, drift handling, semantic safety, signatures, federation, pub/sub, routing, A2A, economics, Inspector output, adapter-facing delivery, configuration validation, HTTP limits, W3C trace context, serialization properties, state patch properties, concurrency, codebook releases, Merkle synchronization, and bounded large-vocabulary lookup.

The invariant catalog contains 21 release invariants. Every invariant maps to executable tests or conformance tooling. `scripts/invariant_check.py` passes.

## Protocol conformance

The normative TCK contains 13 vectors.

| Runtime | Result |
| --- | ---: |
| Python | 13/13 |
| JavaScript | 13/13 |
| Go | 13/13 |

`scripts/conformance_matrix.py` executes all required runtimes from `tck/implementations.json` and passes.

The differential protocol runner executes 250 generated inputs and compares both independent runtimes against Python for canonical MessagePack identity and validation behavior. Each independent runtime passes 500 comparisons, for 1,000 cross-runtime comparisons total.

The Python malformed-wire campaign passes 1,000/1,000 mutations with the required accept/reject behavior.

Protocol identity is deterministic canonical MessagePack plus SHA-256. Canonical JSON remains the readable normalized form but is not used as cross-language byte identity because runtime floating-point string rendering is not guaranteed to be byte-identical.

## Learned-language security and reliability

Pattern observations are source-aware and carry trust scope. Repetition from one logical source cannot manufacture source diversity.

Default distinct-source requirements are:

| Scope | Minimum distinct sources |
| --- | ---: |
| Session | 2 |
| Project | 3 |
| Workspace | 4 |
| Domain | 6 |
| Federation | 8 |

Promotion also evaluates source dominance, trust score, semantic stability, savings, task utility, lifecycle evidence, counterfactual fidelity, and holdout traffic.

Holdout traffic is distinct from candidate-learning evidence. A candidate progresses through candidate, shadow, validated, active, cooling, and retired states under policy. Production compression falls back to richer semantics when validation, receiver reliability, or drift policy is not satisfied.

Receiver reliability is scoped to receiver, provider, model identifier, model version, runtime identifier, runtime version, runtime configuration hash, and task family. Calibration records empirical success, predicted confidence, calibrated probability, expected calibration error, and Brier score.

Rolling reliability windows detect meaningful fidelity decline and move affected learned patterns toward safe fallback without globally disabling unrelated receiver/model combinations.

## Semantic safety and information flow

The semantic firewall applies stricter preservation rules to negation, authorization, identity, irreversible instructions, quantities, money, deadlines, environment markers, explicit constraints, and security controls.

Epistemic types distinguish fact, observation, inference, hypothesis, prediction, preference, instruction, and constraint. Contradictory claims coexist with provenance. Dependency invalidation marks downstream derived knowledge stale transitively.

Derived information inherits the union of upstream sensitivity labels. Sensitivity cannot be silently downgraded through derivation.

Uncertain semantic optimization fails open to a richer literal or reference-backed representation. Failure of pattern learning, caching, telemetry, federation, or other optional optimization does not corrupt core lossless delivery.

## Durable delivery, fairness, and ordering

Local concurrency qualification runs eight producers with 20 messages each. All 160 messages are produced and consumed.

Messages can be claimed by deterministic partition. Partition-scoped workers receive only the requested shard. An optional ordering key allocates contiguous monotonic sequence numbers per stream while unrelated streams remain parallel.

Workspace and agent handoff quotas are updated atomically. A failed agent-scoped quota check cannot consume shared workspace allowance. Queue state reports normal, degraded, throttled, or unavailable. Throttled and unavailable states reject new work explicitly.

Mutating HTTP operations support principal/workspace/route-scoped idempotency keys. Repeating the same key and request returns the stored logical result; reusing the key with a different payload is rejected.

Delivery remains at-least-once. Receiver knowledge advances only after acknowledgement. NACK and lease expiration preserve redelivery.

The local deterministic chaos suite processes 64 messages, verifies one logical idempotent write path, and recovers 32 messages after claim-lease expiration.

## Pattern contention

The learned-pattern contention qualification runs six concurrent sources with four observations each. It records all 24 observations, all 24 source-evidence observations, and six distinct sources without splitting one semantic signature across duplicate candidate lifecycle rows.

The qualification intentionally does not activate an unvalidated pattern. Activation requires holdout/counterfactual policy after source-diverse observation.

## State, checkpoints, and cleanup

State deltas are lossless and deterministic. Generated property checks verify that applying a computed delta reconstructs the exact target nested state.

Checkpoints are content-addressed and chosen only from the target state's ancestry chain. Checkpoint lookup cannot cross a divergent state branch.

Reference and state cleanup is reachability-aware. Live reference grants, undelivered packets, receiver knowledge, checkpoints, receiver current-state pointers, retained audit data, replay roots, and parent ancestry are retained according to policy. Expired unreachable objects are eligible for cleanup.

## Codebook synchronization and releases

Codebooks expose deterministic Merkle manifests. Synchronization compares roots and only descends into differing partitions. Diff logic derives partition width from compared manifests rather than assuming a fixed prefix length.

Signed codebook releases are immutable and deterministic. The signed payload excludes wall-clock creation time so two nodes releasing identical semantic content with the same release identity produce the same signed content identity. Release signatures are verified with Ed25519 public keys.

## Large-vocabulary qualification

Exact lookup remains indexed. Fuzzy matching performs exhaustive comparison only below the configured scan limit. Larger vocabularies use deterministic locality-sensitive-hash buckets with bounded Hamming-neighbor search and a bounded candidate ceiling. If no safe match is found, SAGE retains the richer semantic representation.

Final local SQLite measurements:

| Concepts | Exact p50 | Exact p95 | Exact p99 | Fuzzy p50 | Fuzzy p95 | Fuzzy p99 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 0.199 ms | 0.267 ms | 0.516 ms | 1.191 ms | 1.446 ms | 4.948 ms |
| 1,000 | 0.294 ms | 0.433 ms | 0.571 ms | 5.107 ms | 5.608 ms | 21.684 ms |
| 5,000 | 0.293 ms | 0.438 ms | 0.561 ms | 5.967 ms | 14.563 ms | 15.552 ms |

The dispatch-only scale workflow extends vocabulary qualification to 1,000,000 concepts by default and runs configurable sustained staging traffic without slowing ordinary pull-request qualification.

## Latency and database query budget

The final 200-iteration local SQLite latency gate passes all configured ceilings:

| Operation | p50 | p95 | max | Gate |
| --- | ---: | ---: | ---: | ---: |
| Core encode | 13.232 ms | 17.926 ms | 81.182 ms | p95 <= 40 ms |
| Core decode | 0.007 ms | 0.009 ms | 0.216 ms | p95 <= 10 ms |
| HTTP send | 15.686 ms | 20.172 ms | 39.107 ms | p95 <= 75 ms |
| HTTP receive | 1.588 ms | 1.992 ms | 2.531 ms | p95 <= 50 ms |

The final 30-iteration encode query profile records 5.965 ms p50, 9.881 ms p95, 27.936 ms p99, 22 SQL statements at median, and 27 SQL statements maximum. The release ceiling is 40 statements.

These values are local regression measurements and are not service-level claims for remote databases, networks, embedding services, telemetry exporters, or model providers.

## Economics and model-matrix tooling

The economics layer records model-provider cost, SAGE infrastructure cost, retrieval cost, retry cost, total cost, task success, semantic loss, wire bytes, model tokens, and task utility per transmitted bit.

`scripts/model_matrix_benchmark.py` consumes a reproducible SAGE corpus and explicitly configured model commands. It compares raw context, caller-supplied summary/retrieval representations, state/reference strategies, structural SAGE, learned SAGE, and receiver-aware SAGE when those runtime strategies are supplied.

No external model-provider result is reported in this local verification because provider credentials and heterogeneous model runtimes are not present in the execution environment. The benchmark runner does not fabricate provider measurements.

## Inspector and observability

SAGE exposes JSON, CLI, and HTML Inspector surfaces. Reports contain original/sent bytes, token estimates, receiver-known ratio, semantic-loss score, learned-pattern decisions, references, and a compression waterfall.

OpenTelemetry is optional and isolated from core delivery. SAGE emits operational protocol attributes by default rather than semantic message content. W3C `traceparent` and optional `tracestate` propagate through wire v2. Invalid trace context is rejected. Trace metadata is never used as an authorization signal.

## Adapter architecture

SAGE Core owns semantic representation, durable state, references, learned language, routing, authorization state, and delivery semantics.

A2A remains the generic peer-agent lifecycle envelope. MCP remains an optional tool/context adapter. Hermes and OpenClaw use native lifecycle adapters. REST and Python provide framework-neutral runtime access.

The HTTP implementation is decomposed into transport, memory/state, learning/calibration, and semantic/routing routers. Pattern structure, policy, calibration, and reliability logic are separated from the core pattern lifecycle module. Architecture checks enforce the adapter-only MCP boundary and domain-router layout.

## Staging, soak, and disruption qualification

The repository contains a production-shape staging topology with PostgreSQL 18, a one-shot migration service, three independent SAGE application nodes, TLS termination/load balancing, and non-root/read-only application containers.

`scripts/soak_cluster.py` measures completed handoff -> claim -> ACK lifecycles through the TLS load balancer. Its default duration is 24 hours. `scripts/cluster_chaos.py` can pause an application node, verify load-balancer failover, disrupt PostgreSQL, require readiness failure, restore the database, and verify durable delivery recovery.

Normal CI runs a short staging gate. `.github/workflows/scale.yml` is dispatch-only and accepts vocabulary-size and soak-duration inputs for extended release-candidate qualification.

Docker and a local PostgreSQL service are unavailable in this execution environment, so the multi-node staging topology and PostgreSQL-specific multi-consumer path are configured and CI-gated but are not represented as locally executed passes in this report.

## Database verification

A fresh SQLite database upgrades directly to the sole `0001_sage_0_2` migration. `alembic check` reports no new upgrade operations. `alembic current` reports `0001_sage_0_2 (head)`.

The PostgreSQL CI job uses PostgreSQL 18 with configured-database mode and runs the full suite plus multi-consumer delivery and ordered-stream qualification against PostgreSQL.

## API and protocol artifacts

The FastAPI OpenAPI document builds as OpenAPI 3.1.0 with 81 paths, title `SAGE`, and version 0.2.3.

Normative JSON Schemas, protobuf binding, Markdown protocol specification, generated TypeScript/Go wire metadata, and TCK artifacts are generated or checked from the frozen v0.2 protocol model. The installed Python package mirrors the repository hierarchy under `sage_plugin/spec/schemas/`.

Schema generation and generated-artifact checks pass. Repository/package schema bytes, protocol specification bytes, protobuf bytes, TCK vectors, and implementation matrix are checked for drift.

## Security qualification

Production configuration fails closed unless required authentication, service credentials, server database, managed migration mode, explicit hosts, and documentation policy are valid.

Service and agent credentials cannot overlap. Agent credentials bind to workspace and agent identity. Control-plane routes remain service-only. Reference delegation and policy mutation require the explicit owner or service authority. Unowned shared references cannot be delegated by ordinary grantees.

Request bodies are bounded. Production host validation is enabled. Sensitive metrics and MCP access require service authentication. Security headers and no-store behavior are applied on sensitive paths.

References use SHA-256 content identity while grants carry access, selective-field policy, tier, TTL, sensitivity, and provenance. Optional AES-GCM encryption validates key material. Ed25519 signature-required mode cannot start without verification material.

`scripts/security_check.py` passes across 77 Python files and checks AST safety, TLS/deployment policy, Compose credentials, container hardening, and project metadata.

## Quick-start and first-user qualification

The release adds a local Docker Compose path with persistent SQLite storage,
Linux/macOS and Windows launchers, `.env.example`, `sage-doctor`, and
`sage-demo`. The doctor command verifies liveness, database readiness,
`sage/0.2` wire identity, handoff, context claim, ACK, and removal from the
pending mailbox.

Automated tests exercise both two-agent delivery and a self-addressed
single-agent lifecycle. The installed wheel was also run as an isolated package
against a fresh SQLite service; `sage-doctor` completed every check and
`sage-demo --single-agent` sent, decoded, and acknowledged its message.

The standalone Hermes ZIP now extracts into one versioned directory and ships
Linux/macOS and PowerShell installers, its own README, license, plugin manifest,
and adapter. The source ZIP also extracts into one versioned directory.

Environment parsing accepts both comma-separated and JSON-array forms for
service API keys and allowed-host lists, matching Compose, shell, and managed
deployment conventions.

## Distribution qualification

The Python wheel builds as `sage_agent_protocol-0.2.3-py3-none-any.whl`. `scripts/package_check.py` verifies package metadata, author, Hermes entry point, protocol specification, protobuf binding, nested JSON Schemas, TCK implementation matrix, and TCK vectors directly from the wheel archive. The source tree also ships a standalone Hermes plugin directory and installer; release consistency requires the standalone adapter to remain byte-identical to the packaged Hermes adapter.

The wheel installs into an isolated target, imports as 0.2.3 with author NeuralBinary, exposes `sage = sage_plugin.hermes_plugin`, contains all 11 normative JSON Schemas under `sage_plugin/spec/schemas/`, and passes 13/13 TCK vectors plus 250/250 malformed-wire checks from the installed package.

The OpenClaw archive builds as `@sage-agent/openclaw-sage@0.2.3`. `scripts/package_check.py` verifies its metadata, author, credits, plugin manifest, runtime, conformance runner, and TCK content. The packed JavaScript runtime and conformance runner pass syntax checking, its independent TCK passes 13/13 vectors, and the adapter harness verifies object content, defensive JSON-object recovery, plain-text rejection, and semantic-envelope rejection.

## Reproducibility and release policy

`make verify` runs security, architecture, invariants, generated schema/artifact checks, TCK, the three-runtime conformance matrix, differential fuzzing, chaos recovery, full tests, latency, encode query budget, byte compilation, cleanup, and final source-tree release consistency.

The dispatch scale workflow provides sustained vocabulary and staging soak qualification. The normal CI matrix covers Python 3.11 through 3.14, PostgreSQL 18, dependency auditing, OpenClaw install/type/build/TCK, MCP construction, Python wheel construction, cross-runtime conformance, Docker image construction, and the short staging cluster gate.

## Local execution limits

The local environment does not provide Docker, a PostgreSQL server, Ruff, mypy, protoc, or the optional MCP SDK. Those checks are not counted as locally executed.

The local Node runtime is below the OpenClaw package's declared production engine floor, and OpenClaw development dependencies are not installed locally. The committed JavaScript runtime/conformance files and packed archive are locally syntax/TCK checked; dependency-backed TypeScript installation/build is CI-gated on the declared Node runtime.

No live Claude, OpenAI, Hermes model provider, or other external model-provider economics run is claimed because provider credentials and those runtimes are absent.

## Result

All locally executable v0.2 functional, protocol, semantic-safety, security, migration, packaging, interoperability, concurrency, chaos, invariant, performance, query-budget, and release-consistency gates pass in the working tree.

## Source archive qualification

The deterministic source ZIP is extracted into a separate directory and qualified independently from the working tree. The archive-level run passes the release, security, architecture, invariant, generated-schema, and generated-protocol checks. It passes all 107 automated tests, all 13 Python TCK vectors, all 13 JavaScript TCK vectors, all 13 Go TCK vectors, 250/250 malformed-wire mutations, and 1,000 differential cross-runtime comparisons.

A fresh database built from the extracted source reaches `0001_sage_0_2 (head)` and `alembic check` reports no new upgrade operations. OpenAPI builds as 3.1.0 with 81 paths.

The extracted source passes a 100-iteration latency gate with p95 values of 16.577 ms core encode, 0.011 ms core decode, 22.586 ms HTTP send, and 2.131 ms HTTP receive. Its 20-iteration encode database profile records 12.243 ms p95 and 27 SQL statements maximum under the 40-statement ceiling.

The extracted source independently rebuilds both distribution formats. `scripts/package_check.py` passes against the archive-built Python wheel and OpenClaw package. The source archive retains `integrations/openclaw/dist/index.js`, `integrations/openclaw/dist/conformance.js`, and the OpenClaw TCK while excluding runtime databases, bytecode, cache directories, dependency directories, nested distribution archives, and top-level build output.

All locally executable v0.2 gates therefore pass both in the finalized working tree and in an independently extracted source archive. This report distinguishes locally executed qualification from CI-configured qualification and does not claim that undiscovered defects are impossible.
