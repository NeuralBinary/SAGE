
# Architecture

SAGE v0.2 separates semantic protocol behavior from transport adapters and framework integrations.

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

## Semantic bus and the delivery pipeline

The primary durable bus flow is:

```text
handoff -> pending -> claimed -> acknowledged
                       |
                       +-> lease expiry -> claimable again
```

- A sender hands off raw application-level JSON to `POST /v1/bus/handoff`. SAGE performs semantic encoding (compiler/codebooks) and stores a durable message.
- A receiver claims context with `GET /v1/bus/context/{receiver}` — claim **plus** semantic decoding in one server round trip — or polls without claiming via `GET /v1/bus/pull/{agent}`.
- The receiver acknowledges successful consumption with `POST /v1/bus/{message_id}/ack` or the transaction-facing batch endpoint `POST /v1/bus/ack-batch`. A `NACK` (`POST /v1/bus/{message_id}/nack`) returns a message to pending.
- Unacknowledged claims expire after the claim lease (`SAGE_BUS_CLAIM_LEASE_SECONDS`, default 60 s) and become claimable again. Delivery is at-least-once; consumers use `message_id`/`correlation_id` as idempotency keys.

**Receiver knowledge advances only on ACK** — pull/claim alone never marks knowledge as received. Future sends can use the receiver's immutable state as a delta base and respect negotiated capabilities.

## Content-addressed references

Stored content uses a SHA-256 content identity with the `sage:sha256:` URI prefix. Content identity and authorization are separate: grants carry access policy, so identical bytes deduplicate across workspaces without sharing authorization.

Grants support:

- workspace and owner scope
- agent ACLs
- allowed field paths (selective disclosure/selective resolution)
- memory tier
- TTL
- provenance
- optional AES-GCM at-rest encryption

Forwarding a reference delegates policy to the receiver without duplicating the underlying object.

## Immutable state and deltas

State updates are represented as lossless deltas when a shared base state exists (JSON-Patch-style `add`/`remove`/`replace` transitions). State snapshots are immutable and content-addressed; checkpoints are chosen only from the target state's ancestry chain, and checkpoint lookup cannot cross a divergent state branch. State and reference identities are content-derived where global deduplication is required.

## Learned patterns

Pattern learning is persistent and compositional. Recurring semantic structures are stored as candidates, then move through shadow validation and counterfactual evaluation before becoming active (`candidate → shadow → validated → active`, with `cooling`/`deprecated`/`retired` operational states). Active patterns emit an ordinary concept code plus typed dynamic bindings, so the wire protocol needs no special pattern field; the flattened lossless composition remains available for interoperability and decoding.

Pattern decisions incorporate frequency, estimated savings, semantic stability, task utility, ambiguity, interoperability, source trust/diversity, holdout evidence, and receiver/model-specific fidelity. Receiver reliability is bound to provider/model build, runtime build/configuration, and task family; low-fidelity or drifting patterns are suppressed for the affected receiver identity while remaining available where measured fidelity is sufficient. Pattern namespaces are hierarchical, with cooling/retirement preventing unbounded vocabulary growth. Foreign patterns imported through federation must earn local trust before active use.

## Provenance and semantic memory

Every semantic unit carries provenance (source IDs, observation time, confidence, derivation, producer). Semantic memory differentiates epistemic types: fact, observation, inference, hypothesis, prediction, preference, instruction, constraint. Conflicting claims coexist with provenance and confidence instead of overwriting each other. Dependency edges allow derived claims to be invalidated transitively when an upstream claim is no longer valid. Derived information inherits the union of upstream sensitivity labels; sensitivity cannot be silently downgraded.

## Encode/decode pipeline

The readable packet model is `Packet(v="sage/0.2", ...)`; wire v2 is the compact transport form. Encoding compiles raw structured content into semantic atoms (concepts, literals, refs, state ID + delta, provenance) under the semantic-loss firewall. Unknown or ambiguous concepts stay recoverable through literals or references — compression fails open when preservation cannot be demonstrated. Decoding reconstructs receiver context, applying delta bases and learned-pattern bindings. Wire identity is canonical MessagePack plus SHA-256; JSON is the normalized readable representation (see [Protocol](Protocol.md)).

## Adapters

- **Hermes** uses its native Python plugin entry point and lifecycle hooks. The adapter claims already-decoded SAGE context in one request and acknowledges the successful batch after the model call lifecycle completes.
- **OpenClaw** uses the current `agent_turn_prepare` hook for same-turn context injection and `agent_end` for success-aware batch acknowledgement. Claimed run state is bounded in memory and failed runs are left for lease-based redelivery.
- **Claude, OpenAI, and other MCP-capable hosts** use the authenticated remote MCP surface (the `/mcp` mount on `sage-api`).
- **A2A-capable peer runtimes** may carry SAGE wire payloads directly as structured data parts.
- **Custom orchestrators** use `SageRuntime.handoff/poll/ack` — the smallest dependency surface, below the model.

See [Adapters](Adapters.md) and the repo's `docs/INTEGRATIONS.md`.

## A2A and MCP boundaries

- **A2A** is the generic peer-agent envelope. SAGE is carried as a structured `DataPart` with media type `application/vnd.sage.packet+json` and advertised as an AgentCard extension. A2A retains ownership of peer discovery, task lifecycle, streaming, cancellation, and collaboration semantics.
- **MCP** is an optional adapter. SAGE core imports no MCP types; `scripts/architecture_check.py` enforces the adapter-only MCP boundary. Production MCP access is served through the authenticated `/mcp` mount on `sage-api`. Direct `sage-mcp` mode is restricted to development because it does not provide the FastAPI authentication wrapper.

The same wire packet must keep identical canonical MessagePack identity whether carried by a native adapter, A2A, MCP, REST, queue, or custom transport.

## Persistence

Production persistence is PostgreSQL. The initial v0.2 schema (baseline migration `0001_sage_0_2`) contains semantic memory, immutable state/checkpoints, content-addressed references/grants, receiver knowledge, learned-pattern evidence, reliability windows, codebook releases, delivery state, quota/backpressure state, ordering counters, information-flow labels, federation data, and audit/replay records.

SAGE application nodes never race migrations. Deployment manifests run Alembic once (`alembic upgrade head`) before serving nodes become ready.

## Failure domains

Durable delivery, references, and state are critical. Pattern learning, fuzzy embeddings, semantic cache, telemetry, federation, and inspection are isolated optional subsystems. Optional failures must preserve lossless delivery or return an explicit failure without altering acknowledged knowledge.

## Production deployment topology

Production mode fails closed (see [Configuration](Configuration.md)). The repo ships two Compose topologies:

- `docker-compose.yml` (root): PostgreSQL 18 + a one-shot `migrate` service + a single hardened `sage` application container, with `read_only: true`, a temporary writable `/tmp`, dropped Linux capabilities, and `no-new-privileges`.
- `deploy/staging/compose.yml`: PostgreSQL 18, one-shot `migrate`, **three independent SAGE workers** (`sage-a`, `sage-b`, `sage-c`), and an nginx TLS load balancer (`gateway`, port 8443) using `least_conn` balancing. TLS certificates are mounted from `SAGE_TLS_CERT`/`SAGE_TLS_KEY`.

Production-shape qualification runs end-to-end soak traffic through the load balancer (`scripts/soak_cluster.py`) and worker/database disruption recovery (`scripts/cluster_chaos.py`). See [Production](Production.md).

Next: [Protocol](Protocol.md)
