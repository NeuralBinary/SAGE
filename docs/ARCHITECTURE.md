# Architecture

SAGE v0.2 separates semantic protocol behavior from transport adapters and framework integrations.

## Core boundaries

`protocol_spec.py`, `codec.py`, semantic memory, patterns, references, state, routing, reliability, and the durable bus form the vendor-neutral core. The core has no MCP dependency.

The REST surface is decomposed into domain routers:

- `api_transport.py`: bus, A2A binding, protocol conformance, transport, replay, feedback, integration profiles.
- `api_memory.py`: references, immutable state, concepts.
- `api_learning.py`: patterns, calibration, negotiation, latent transport.
- `api_semantic.py`: facts, contradictions, routing, federation, economics, backpressure, model identity, codebook synchronization/releases, checkpoints, maintenance, readiness.
- `api_helpers.py`: shared response and trace-boundary helpers.
- `api.py`: authenticated `/v1` router assembly only.

Pattern structure/canonicalization is isolated in `pattern_structure.py`; promotion policy and reliability/calibration live in separate modules so serving does not depend on learner activation.

## Interoperability

A2A is the generic peer-agent envelope. SAGE occupies structured payloads and does not redefine A2A task lifecycle, streaming, cancellation, or discovery.

MCP is an optional tool/context adapter. The MCP server is stateless over Streamable HTTP and delegates semantic behavior to SAGE core.

Hermes and OpenClaw adapters use their native lifecycle hooks while exchanging the same SAGE wire and durable-bus state.

## Persistence

Production persistence is PostgreSQL. The initial v0.2 schema contains semantic memory, immutable state/checkpoints, content-addressed references/grants, receiver knowledge, learned-pattern evidence, reliability windows, codebook releases, delivery state, quota/backpressure state, ordering counters, information-flow labels, federation data, and audit/replay records.

SAGE application nodes never race migrations. Deployment manifests run Alembic once before serving nodes become ready.

## Failure domains

Durable delivery, references, and state are critical. Pattern learning, fuzzy embeddings, semantic cache, telemetry, federation, and inspection are isolated optional subsystems. Optional failures must preserve lossless delivery or return an explicit failure without altering acknowledged knowledge.

## Canonical identity

Wire identity is deterministic canonical MessagePack plus SHA-256. JSON is a normalized readable representation and is not used as cross-language identity for floating-point text.

Codebook releases are immutable Merkle-rooted manifests signed with Ed25519. State and reference identities are content-derived where their semantics require global deduplication.
