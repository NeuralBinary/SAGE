# SAGE v0.1 Verification Report

## Release identity

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Public version | v0.1 |
| Package version | 0.1.0 |
| Protocol | sage/0.1 |
| Wire | 1 |
| Database baseline | 0001_sage_0_1_baseline |

This report covers the production-hardening pass completed on July 31, 2026. No version bump was performed.

## Functional verification

The final working tree passed 70 automated tests. The suite covers transport encode/decode, durable handoff/claim/ACK behavior, receiver-scoped authentication, semantic memory, references, state transitions, concepts, adaptive patterns, pattern counterfactual validation, semantic safety, signatures, federation, pub/sub, routing, A2A, economics, Inspector behavior, adapter-facing batch context delivery, configuration validation, and HTTP body limits.

The protocol conformance kit passed all 11 normative vectors. A deterministic malformed-wire campaign passed 1,000 of 1,000 cases with the expected accept/reject behavior.

Python byte compilation passed for source, scripts, and tests.

## Security verification

Production configuration fails closed unless authentication is enabled, at least one service credential is configured, a server database is used, managed migrations are selected, explicit allowed hosts are supplied, and interactive API documentation is disabled.

Service and agent credentials cannot overlap. Agent credentials are bound to a workspace and agent identity. Agent calls cannot impersonate another agent or cross workspace boundaries. Control-plane routes remain service-only. Agent negotiation is restricted to the configured codebook. A grantee of an unowned shared reference cannot delegate that reference to additional agents.

HTTP request bodies are bounded by configured size. Production host validation uses TrustedHostMiddleware. API and MCP responses use no-store caching policy. Responses include content-type, referrer, frame, and permissions protections; production responses also emit HSTS. MCP and private metrics require a valid service bearer credential. Authentication responses advertise the Bearer challenge.

Prometheus route labeling uses declared route paths and a fixed unmatched label, preventing arbitrary request paths from creating unbounded label cardinality.

Reference storage uses SHA-256 content identities. Authorization, selective field disclosure, TTL, invalidation, and memory tier are maintained separately as grants. Optional AES-GCM reference encryption validates a 32-byte key. Ed25519 packet signing validates key material at startup, and signature-required mode cannot start without a verification key.

The repository security gate parses all Python files under `src` and `scripts`, rejects dynamic code execution primitives, unsafe serialization imports, shell-enabled subprocess execution, disabled TLS verification, embedded Compose database passwords, disabled production authentication, root runtime containers, and repository metadata drift. The final gate passed.

## Database verification

A fresh SQLite database was upgraded from an empty file to the sole `0001_sage_0_1_baseline` migration. `alembic check` returned `No new upgrade operations detected`, confirming the baseline migration matches the final SQLAlchemy model set.

Production deployment targets PostgreSQL 18 through the `postgres` dependency extra. The Compose deployment requires the database password, database URL, service keys, and allowed hosts from the runtime environment rather than embedding credentials in source.

## API verification

The final FastAPI OpenAPI document builds successfully with 71 HTTP paths and reports package version 0.1.0. Production disables the interactive documentation and OpenAPI routes by configuration.

The native adapter context path claims and decodes mailbox messages server-side in one batch. Batch ACK processing removes the earlier per-message acknowledgement round-trip. Failed OpenClaw runs do not ACK claimed messages; claim leases permit redelivery.

## Performance verification

The deterministic local latency gate ran 200 core iterations and 100 HTTP iterations on SQLite with learning and semantic cache disabled. Results from the final run:

| Operation | p50 | p95 | max | Gate |
| --- | ---: | ---: | ---: | ---: |
| Core encode | 9.899 ms | 13.149 ms | 30.507 ms | p95 <= 40 ms |
| Core decode | 0.007 ms | 0.009 ms | 0.086 ms | p95 <= 10 ms |
| HTTP transport send | 12.796 ms | 14.596 ms | 19.062 ms | p95 <= 75 ms |
| HTTP transport receive | 1.420 ms | 1.795 ms | 2.199 ms | p95 <= 50 ms |

The gate passed. These numbers are local-process measurements and are not claims about network, model-provider, or remote-database latency.

## Package verification

The Python wheel built successfully with no dependency resolution during the build. It was then installed into an isolated target directory. The installed package imported as 0.1.0, exposed author `NeuralBinary`, exposed the Hermes entry point `sage_plugin.hermes_plugin`, contained the v0.1 protocol specification, protobuf binding, normative schemas, and TCK vectors, and passed all 11 packaged TCK vectors.

The OpenClaw TypeScript source passed Node's TypeScript syntax parser. The committed JavaScript runtime passed `node --check`. The npm package packed successfully and contains only the runtime, plugin manifest, README, and package metadata required for distribution.

JSON, TOML, and YAML project artifacts parsed successfully: 28 JSON files, `pyproject.toml`, Compose, CI workflow, and Hermes manifest.

## Observability verification

OpenTelemetry is optional. With telemetry enabled in the local environment, a real SAGE encode completed successfully and produced a compact packet without changing encode semantics. Prometheus metrics remain available through the protected metrics endpoint.

## Release consistency

The release checker passed after runtime artifacts and caches were removed. It enforces:

- project, author, repository, credits, and v0.1 identity;
- package 0.1.0, protocol sage/0.1, and wire 1;
- matching repository and packaged protocol/TCK files;
- exactly one v0.1 database migration;
- required packet signature and epistemic schema fields;
- absence of obsolete development-era version markers;
- absence of development filler prose in shipped documentation;
- absence of runtime databases, Python bytecode, caches, nested package archives, and egg metadata in the source tree.

## Local environment limits

The execution environment did not provide Docker, Ruff, mypy, protoc, or the optional MCP Python package. Those tools were therefore not counted as locally executed checks. CI contains dedicated jobs for linting, PostgreSQL, dependency auditing, MCP construction, OpenClaw dependency-backed TypeScript checking/building, wheel packaging, and Docker image building in environments where those dependencies are available.

The local npm mirror did not provide the current OpenClaw package, so a dependency-backed OpenClaw host load was not performed locally. Source and committed runtime syntax checks and npm packaging passed locally; CI installs the current declared OpenClaw dependency before type checking and rebuilding the adapter.

The current execution environment used Python 3.13.5 and Node 22.16.0. The production container is pinned to the Python 3.14 slim line, and CI spans Python 3.11 through 3.14.

## Result

No known functional, protocol, security-gate, migration, packaging, or latency-gate failures remain in this v0.1 build. This verification does not claim that undiscovered defects are impossible; it records the checks actually executed and the checks that require dependency-available CI infrastructure.

## Source archive verification

The release source archive was extracted into a separate directory and verified independently of the working tree. The extracted archive passed the release consistency checker, repository security gate, all 70 tests, all 11 TCK vectors, 250 of 250 malformed-wire checks, both OpenClaw syntax checks, a fresh migration followed by `alembic check`, and a 100-iteration latency gate. The extracted latency p95 measurements were 12.922 ms for core encode, 0.010 ms for core decode, 14.917 ms for HTTP transport send, and 1.984 ms for HTTP transport receive. The final release consistency checker passed again after test artifacts were removed.
