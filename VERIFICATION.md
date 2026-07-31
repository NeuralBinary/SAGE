# SAGE v0.2 Verification Report

## Release identity

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Public version | v0.2 |
| Package version | 0.2.0 |
| Protocol | sage/0.2 |
| Wire | 2 |
| Database baseline | 0001_sage_0_2 |

This report records the local qualification performed on July 31, 2026 for the clean v0.2 first-deployment baseline. No pre-v0.2 compatibility reader or migration path is shipped.

## Functional verification

The final working tree contains 81 automated tests. The full suite passes and covers transport encode/decode, durable handoff/claim/ACK behavior, identity-scoped authorization, semantic memory, contradictions, causal invalidation, content-addressed references, selective disclosure, state transitions, concepts, learned patterns, trust scopes, counterfactual validation, receiver calibration, semantic safety, signatures, federation, pub/sub, routing, A2A, economics, Inspector behavior, adapter-facing delivery, configuration validation, HTTP limits, wire-v2 trace context, deterministic serialization properties, state patch properties, concurrency, and large-vocabulary lookup.

The Python protocol conformance kit passes all 13 normative vectors. A deterministic malformed-wire campaign passes 1,000 of 1,000 cases with the expected accept/reject behavior.

An independent JavaScript conformance implementation passes the same 13 vectors. `scripts/conformance_matrix.py` executes every required implementation from `tck/implementations.json` and passes for Python and JavaScript.

The property suite runs 250 nested canonical-serialization cases and 250 state diff/apply round trips. All pass.

Python byte compilation passes for source, tests, and release scripts.

## Learned-language security

Pattern evidence is source-aware and trust-scoped. Normal encoding attributes learning evidence to the authenticated logical sender; arbitrary provenance identifiers do not increase source diversity.

Promotion thresholds become stricter across session, project, workspace, domain, and federation scope. The default minimum distinct source counts are 2, 3, 4, 6, and 8 respectively. Dominant-source share and minimum trust are enforced in addition to lifecycle, savings, utility, semantic stability, and counterfactual requirements.

Concurrent pattern observations use database conflict updates for evidence and candidate counters. Promotion uses row locking and rechecks for a concurrently created learned pattern before transition. The local contention qualification with six workers and four observations per worker records all 24 observations, preserves six-source diversity, stores all 24 evidence observations, and produces one promoted lifecycle result.

Receiver/model/task reliability is stored in calibration buckets. Compression can be suppressed for a receiver when measured fidelity is below policy. Calibration tracks empirical success, predicted confidence, expected calibration error, Brier score, and calibrated probability.

## Semantic safety

The semantic firewall preserves high-risk meaning through stricter thresholds and lossless fallback. Critical categories include negation, authorization, identity, irreversible instructions, quantities, money, deadlines, environment markers, and security constraints.

Epistemic types distinguish fact, observation, inference, hypothesis, prediction, preference, instruction, and constraint. Contradictory claims coexist with provenance rather than overwriting one another. Dependency invalidation marks derived knowledge stale transitively.

Large-vocabulary semantic matching never requires an unbounded scan. Exact lookup remains indexed. Fuzzy lookup permits exhaustive comparison only through 1,000 compatible concepts by default; larger vocabularies use deterministic LSH neighbor buckets with at most 512 selected candidates. If no safe candidate exists, the original semantic form is retained.

## Concurrency and delivery

The local durable-bus qualification runs eight concurrent producers with 20 messages each. All 160 messages are produced and all 160 are consumed without duplicate claims or lost delivery.

The learned-pattern contention qualification runs six concurrent sources with four observations each. It records all 24 observations and six distinct source identities without splitting one semantic signature across duplicate lifecycle rows.

SQLite qualification deliberately uses one consumer where database semantics do not provide PostgreSQL-style `SKIP LOCKED`. The PostgreSQL CI job runs configured multi-consumer qualification with eight workers and 20 messages per worker after applying the v0.2 migration.

Delivery remains at-least-once. Receiver knowledge advances only on acknowledgement. NACK and lease expiry preserve redelivery behavior.

## Database verification

A fresh SQLite database upgrades from empty state directly to the sole `0001_sage_0_2` migration. `alembic check` returns `No new upgrade operations detected`, confirming that the baseline migration matches the current SQLAlchemy models. `alembic current` reports `0001_sage_0_2 (head)`.

The PostgreSQL CI job uses PostgreSQL 18 and sets `SAGE_TEST_USE_CONFIGURED_DB=true`, so the suite and configured concurrency qualification use PostgreSQL rather than the local SQLite test fixture.

## API and protocol verification

The FastAPI OpenAPI document builds as OpenAPI 3.1.0 with 73 HTTP paths, title `SAGE`, and package version 0.2.0.

Wire v2 carries validated W3C `traceparent` and optional `tracestate` metadata. REST transport imports valid trace headers only when the body has not already provided trace context. Invalid `traceparent` values return HTTP 422. Trace metadata participates in canonical encoding and signatures but never in authentication or authorization.

The repository protocol specification, protobuf binding, JSON Schemas, packaged protocol files, TCK vectors, and implementation matrix are release-checked for byte or semantic parity as applicable.

## Performance verification

The final deterministic local latency gate uses 200 iterations on SQLite and passes all configured ceilings:

| Operation | p50 | p95 | max | Gate |
| --- | ---: | ---: | ---: | ---: |
| Core encode | 13.352 ms | 16.533 ms | 29.638 ms | p95 <= 40 ms |
| Core decode | 0.007 ms | 0.009 ms | 0.070 ms | p95 <= 10 ms |
| HTTP transport send | 16.222 ms | 19.843 ms | 26.262 ms | p95 <= 75 ms |
| HTTP transport receive | 1.299 ms | 1.770 ms | 3.157 ms | p95 <= 50 ms |

A 30-iteration encode query profile with pattern learning and semantic cache disabled reports 6.127 ms p50, 8.329 ms p95, 26.613 ms p99, a median of 21 SQL statements, and a maximum of 26 statements. The qualification ceiling is below 40 statements.

Local vocabulary qualification after the bounded-LSH tuning reports:

| Concepts | Exact p95 | Fuzzy p95 |
| ---: | ---: | ---: |
| 100 | 0.250 ms | 1.372 ms |
| 1,000 | 0.424 ms | 7.471 ms |
| 5,000 | 0.347 ms | 14.097 ms |

These are local SQLite regression measurements. They are not service-level claims for remote databases, networks, embedding providers, or model providers.

## Security verification

Production configuration fails closed unless authentication is enabled, service credentials are configured, a server database is selected, managed migrations are enabled, explicit allowed hosts are provided, and interactive API documentation is disabled.

Service and agent credentials cannot overlap. Agent credentials bind to workspace and agent identity. Control-plane routes remain service-only. Reference delegation and policy mutation require the explicit owner or service authority. Body sizes are bounded. Host validation is enabled in production. Private metrics and MCP require service authentication. Security headers and no-store behavior are applied on sensitive paths.

Reference objects use SHA-256 content identity while grants hold access, selective-field policy, tier, TTL, and provenance. Optional AES-GCM encryption validates key material. Ed25519 signature-required mode cannot start without verification key material.

The repository security gate passes across 47 Python files and checks AST safety, TLS settings, Compose credentials, container hardening, and project metadata.

## Traceability and telemetry

OpenTelemetry remains optional. A live local encode with telemetry enabled succeeds, records a valid packet, keeps payload content out of SAGE telemetry attributes, and leaves semantic behavior unchanged.

Wire v2 propagates W3C trace context so distributed adapters can correlate agent, SAGE, storage, and downstream work without using trace metadata as an authorization signal.

## Package verification

The Python wheel builds successfully without dependency resolution during the build. It installs into an isolated target directory, imports as 0.2.0, exposes author `NeuralBinary`, exposes the Hermes entry point `sage_plugin.hermes_plugin`, and contains the v0.2 protocol specification, protobuf binding, wire schema, TCK vectors, and implementation matrix. The isolated installed package passes 13 of 13 TCK vectors and 250 of 250 malformed-wire checks.

The OpenClaw package packs as `@sage-agent/openclaw-sage@0.2.0`. The tarball contains the runtime, independent JavaScript conformance runner, v0.2 TCK vectors, plugin manifest, package metadata, and package documentation. The committed JavaScript runtime and conformance runner both pass `node --check`.

Project metadata parsing succeeds for 31 JSON files, `pyproject.toml`, YAML manifests, Compose, and CI configuration.

## Release consistency

The release checker enforces:

- SAGE, NeuralBinary, repository, credits, and v0.2 identity;
- package 0.2.0, protocol sage/0.2, and wire 2;
- one `0001_sage_0_2_baseline.py` migration;
- repository/package protocol and TCK parity;
- Python and JavaScript conformance matrix presence;
- required trace, signature, epistemic, and pattern schema fields;
- absence of obsolete development version markers;
- absence of development filler prose in shipped documentation;
- absence of runtime databases, caches, bytecode, nested package output, and egg metadata in the release source tree.

## Local environment limits

The local execution environment uses Python 3.13.5 and Node 22.16.0. Docker, Ruff, mypy, protoc, and the optional MCP Python SDK are not installed locally and are not counted as locally executed checks.

CI provides dependency-backed jobs for Python 3.11 through 3.14, Ruff, PostgreSQL 18, dependency auditing, MCP server construction, OpenClaw dependency-backed type checking/building, Python wheel construction, the cross-runtime conformance matrix, and Docker image construction.

The local PostgreSQL multi-consumer qualification is not executed because no PostgreSQL service is available in this environment. The local concurrency suite verifies producer contention, durable delivery, redelivery, and learned-pattern contention with SQLite; CI verifies the database-specific multi-consumer path on PostgreSQL.

## Source archive verification

The source ZIP is extracted into a separate directory and qualified independently of the working tree. The extracted source passes the release consistency gate, security gate, all 81 automated tests, all 13 Python TCK vectors, 250 of 250 malformed-wire checks, the required Python/JavaScript conformance matrix, and both OpenClaw JavaScript syntax checks.

A fresh database created from the extracted source reaches the sole `0001_sage_0_2` head and `alembic check` reports no new upgrade operations.

The extracted archive also passes a 100-iteration local latency gate with p95 measurements of 14.511 ms for core encode, 0.010 ms for core decode, 17.803 ms for HTTP transport send, and 1.845 ms for HTTP transport receive.

## Result

All locally executable v0.2 functional, protocol, security, migration, packaging, interoperability, and performance gates pass. This report records executed qualification and declared CI coverage; it does not claim that undiscovered defects are impossible.
