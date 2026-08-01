
# Protocol

SAGE v0.2 writes and reads only `sage/0.2` with numeric wire version `2`; other wire versions are rejected. The normative frozen v0.2 specification is `spec/SAGE-0.2.md`; JSON Schemas are in `spec/schemas/` (11 normative schemas packaged with the Python distribution under `sage_plugin/spec/schemas/`), and an optional protobuf binding ships as `spec/sage-v0.2.proto`.

## Layers

SAGE deliberately separates four layers:

1. **Semantic representation** — concepts, literals, refs, state IDs, deltas, provenance.
2. **SAGE wire** — canonical compact JSON/MessagePack packet (`wire v2`).
3. **Durable bus** — receiver mailbox, correlation ID, priority, TTL, claim lease, ACK/NACK.
4. **Adapters** — Python, REST, A2A, MCP, Hermes, OpenClaw, and future frameworks.

No adapter owns the semantic protocol.

## Semantic envelope

The readable model is `Packet(v="sage/0.2", ...)`. A packet can carry semantic atoms, refs, base state + JSON-Patch delta, provenance, and small protocol metadata. Unknown or ambiguous concepts stay recoverable through literals or references.

Wire v2 uses compact keys (frozen for 0.2.x):

| Key | Meaning |
|---|---|
| `v` | wire version, integer `2` |
| `c` | codebook namespace |
| `a` | act/intention |
| `i` | packet ID |
| `s` | sender |
| `r` | receiver |
| `x` | semantic atoms |
| `R` | references |
| `b` | base state ID |
| `d` | delta |
| `p` | provenance |
| `m` | protocol metadata |
| `g` | optional packet signature object (`alg`, `kid`, `sig`) |
| `z` | optional W3C trace context (`p` traceparent, `s` tracestate) |

Atom keys are `c` (concept code), `v` (concept version), `l` (literal), `h` (literal-presence marker), `p` (path), `q` (confidence), and `e` (epistemic type). `h=1` is required when a literal is intentionally JSON `null`, so absence and explicit null remain distinguishable. `e` distinguishes facts/observations/inferences/hypotheses/predictions/preferences/instructions/constraints; omitted `e` means `fact`.

**Unknown top-level and atom fields are invalid in wire v2** — optional-field drift cannot silently fork implementations. New optional fields require a new wire version.

## Canonical encoding and digests

Canonical encoding exists for hashing, signatures, test vectors, caches, and cross-language conformance:

1. Objects MUST use string keys.
2. Object keys are recursively sorted lexicographically by Unicode code point.
3. Arrays retain order.
4. NaN and infinities are forbidden.
5. Canonical JSON is UTF-8, unescaped Unicode where JSON permits it, no insignificant whitespace, and no NaN/Infinity. Canonical JSON is a **normalized readable representation**, not the cross-runtime identity primitive for floating-point text.
6. Canonical MessagePack uses the same recursively sorted structure, `bin` for bytes, UTF-8 strings, and 64-bit floats.
7. A canonical SAGE digest is `sha256:` followed by the SHA-256 hex digest of canonical MessagePack bytes. **Canonical MessagePack bytes and this digest are the cross-runtime protocol identity.**

The Python reference functions are `canonical_json_bytes`, `canonical_msgpack_bytes`, and `canonical_digest` in `sage_plugin.protocol_spec`.

Protobuf field numbers are frozen for the 0.2.x line, but protobuf bytes are **not** canonical SAGE bytes and MUST NOT be used for the canonical digest.

## Packet signatures and trace context

- Wire v2 may carry `g`, an Ed25519 signature object (`alg`, `kid`, URL-safe-base64 `sig`). The signature covers canonical MessagePack bytes of the entire wire object with `g` removed. Signature-required deployments reject unsigned packets and verification failures, and require a configured verification public key at startup.
- Wire v2 may carry W3C Trace Context in `z` (`z.p` = validated `traceparent`, `z.s` = optional `tracestate`). REST send boundaries import validated `traceparent`/`tracestate` headers when the request body does not already carry trace context. Trace context is diagnostic metadata — excluded from authorization decisions and preserved through canonical serialization and cross-runtime TCK validation.

## TCK and conformance

The language-neutral TCK in `tck/` carries **13 normative vectors: 6 valid + 7 invalid**, consumed independently by Python, JavaScript, and Go (`tck/implementations.json` declares all three as required). The TCK is normative for canonical MessagePack, digest identity, structural JSON equivalence, validation failure, trace context, signature shape, and A2A wrapping.

Conformance matrix (v0.2 verification):

| Runtime | Result |
| --- | ---: |
| Python | 13/13 |
| JavaScript | 13/13 |
| Go | 13/13 |

Release CI requires all three independent runners plus differential fuzzing so protocol identity is not proven by a single implementation family. The Python malformed-wire campaign passes 1,000/1,000 mutations.

Run the conformance checks:

```bash
sage-tck --json
sage-conform --fuzz 1000
python scripts/conformance_matrix.py
python scripts/differential_fuzz.py --iterations 1000
python scripts/generate_protocol_artifacts.py --check
```

## Durable bus and delivery semantics

Bus delivery is **at-least-once**:

- A handoff creates a pending message for a receiver mailbox.
- A claim is a **lease** (`SAGE_BUS_CLAIM_LEASE_SECONDS`, default 60 s); stale claims can be reclaimed after expiry.
- **ACK is terminal** — receiver knowledge changes only on ACK, never on pull/claim alone.
- **NACK** returns an unacknowledged message to pending.
- TTL expires stale work (`SAGE_DEFAULT_BUS_TTL_SECONDS`).

Consumers use `message_id`/`correlation_id` for idempotency. `GET /v1/bus/context/{receiver}` performs claim plus semantic decoding in one server round trip; `POST /v1/bus/ack-batch` acknowledges a consumed set in one transaction-facing call, avoiding per-message decode and ACK network fan-out.

Key REST endpoints:

| Area | Paths |
| --- | --- |
| Durable bus | `POST /v1/bus/handoff`, `GET /v1/bus/pull/{agent}`, `GET /v1/bus/context/{receiver}`, `POST /v1/bus/{message_id}/ack`, `POST /v1/bus/{message_id}/nack`, `POST /v1/bus/ack-batch` |
| Transport | `POST /v1/transport/send`, `POST /v1/transport/receive` |
| Protocol conformance | `GET /v1/protocol`, `GET /v1/protocol/wire-schema`, `POST /v1/protocol/validate`, `GET /v1/protocol/tck` |
| A2A binding | `POST /v1/a2a/pack`, `POST /v1/a2a/unpack`, `POST /v1/a2a/message/pack`, `POST /v1/a2a/message/unpack`, `GET /v1/a2a/extension`, `GET /v1/a2a/agent-card` |
| Inspector | `GET /v1/inspect/{packet_id}`, `GET /v1/inspect/run/{run_id}`, `GET /v1/runs/{run_id}/replay` |
| References | `/v1/refs`, resolution, grants, invalidation, forwarding |
| State | state creation, lookup, delta generation, delta application |
| Concepts | concept registration, aliases, lifecycle, negotiation |
| Patterns | observation, lifecycle, counterfactual feedback, receiver reliability |
| Semantic memory | facts, contradictions, invalidation, dependencies |
| Routing | capabilities, subscriptions, publication, semantic route selection |
| Federation | peer administration, export, import |
| Economics | structural/token/cost measurements and observed provider usage |

The generated OpenAPI document is the authoritative HTTP request/response contract when documentation is enabled in a non-production environment (OpenAPI 3.1.0, title `SAGE`, 81 paths).

## Idempotency and ordering

- **Idempotency keys**: all mutating HTTP routes that support retryable writes honor the `X-Idempotency-Key` header. A key is scoped by authenticated principal/workspace and route; repeating the same key and request returns the stored logical result; reusing the key with a **different** request is rejected. Server-side idempotency records live for `SAGE_IDEMPOTENCY_TTL_SECONDS` (default 86400 s).
- **Ordering keys**: an optional ordering key allocates contiguous monotonic sequence numbers per stream; unrelated streams remain parallel. Messages can also be claimed by deterministic partition (`SAGE_BUS_PARTITION_COUNT`, default 64); partition-scoped workers receive only the requested shard.
- **Fairness/backpressure**: workspace and per-agent handoff quotas are updated atomically. Queue state reports normal, degraded, throttled, or unavailable; throttled and unavailable states reject new work explicitly with retryable HTTP status.

## Receiver model and budgets

On ACK, SAGE records receiver-known codes/refs, state pointer, and negotiated capabilities. Future sends can use the receiver's immutable state as a delta base and respect packet/fallback capabilities. `send()` accepts token/byte budgets; legacy in-runtime token budgeting remains an estimate unless a model-aware tokenizer is supplied by the surrounding adapter. The v0.2 economics benchmark separately supports exact tokenizer adapters and never labels estimates as provider billing truth.

## A2A and MCP bindings

- **A2A 1.0** owns peer discovery, Message/Task lifecycle, streaming, cancellation, and collaboration semantics. SAGE is carried as a structured `DataPart` with media type `application/vnd.sage.packet+json` and advertised as an AgentCard extension (a SAGE-enabled AgentCard still includes A2A's required `defaultInputModes`, `defaultOutputModes`, and `skills`).
- **MCP** is an optional tool/context adapter. SAGE core imports no MCP types; the adapter exposes SAGE operations (`send`, `receive`, memory, bus, explain, eval) and may be replaced without altering SAGE wire semantics. v0.2 packages against the current MCP Python SDK v2 stable line.

Next: [CLI-Tools](CLI-Tools.md)
