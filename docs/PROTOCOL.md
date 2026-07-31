# SAGE protocol model

The normative frozen v0.2 specification is `spec/SAGE-0.2.md`; schemas are in `spec/schemas/` and package data under `sage_plugin/spec/`.

## Layers

SAGE deliberately separates four layers:

1. **Semantic representation** — concepts, literals, refs, state IDs, deltas, provenance.
2. **SAGE wire** — canonical compact JSON/MessagePack packet (`wire v2`).
3. **Durable bus** — receiver mailbox, correlation ID, priority, TTL, claim lease, ACK/NACK.
4. **Adapters** — Python, REST, A2A, MCP, Hermes, OpenClaw, and future frameworks.

No adapter owns the semantic protocol.

## Packet

The readable model is `Packet(v="sage/0.2", ...)`. All v0.2 writers and readers use numeric wire version `2`. Other wire versions are rejected.

A packet can carry semantic atoms, refs, base state + JSON Patch delta, provenance, and small protocol metadata. Unknown or ambiguous concepts stay recoverable through literals or references.

Canonical MessagePack and `sha256(canonical-msgpack)` define protocol identity. Canonical JSON is a normalized readable representation; conforming runtimes must preserve its parsed structure, while floating-point text formatting is not an identity primitive. Unknown wire-v2 fields are rejected so optional-field drift cannot silently fork implementations.

## Receiver model

On ACK, SAGE records receiver-known codes/refs, state pointer, and negotiated capabilities. Pull/claim alone does not mark knowledge as received. Future sends can use the receiver's immutable state as a delta base and respect packet/fallback capabilities.

## Budgets

`send()` accepts token/byte budgets. Legacy in-runtime token budgeting remains an estimate unless a model-aware tokenizer is supplied by the surrounding adapter. The v0.2 economics benchmark separately supports exact tokenizer adapters and never labels estimates as provider billing truth.

## Pattern learning

Higher-order patterns are runtime-learned templates over ordered semantic units. Every learned pattern owns an ordinary concept code; active patterns therefore use normal wire atoms rather than a second message grammar. Constant template literals are implicit in the definition and dynamic values travel as ordered typed bindings in the atom literal.

Lifecycle is `candidate -> shadow -> validated -> active`, with `deprecated` and `retired` terminal/operational states. Shadow patterns never alter live output. The codebook concept status mirrors the pattern lifecycle, so negotiation and semantic-cache fingerprints change when pattern availability changes.

Peers advertise `supports_patterns`. Active definitions missing on the receiver are returned during negotiation. A peer that does not support patterns receives the uncompressed constituent atoms.

## A2A binding

A2A 1.0 owns discovery, Message/Task lifecycle, streaming, cancellation, and peer collaboration. SAGE is carried as a structured DataPart with media type `application/vnd.sage.packet+json` and advertised as an AgentCard extension.

## MCP binding

MCP is an optional tool/context adapter. SAGE core imports no MCP types. The adapter exposes SAGE operations but must not alter packet semantics. v0.2 packages against the current MCP Python SDK v2 stable line.

## Delivery semantics

Bus delivery is at-least-once. A claim is a lease; stale claims can be reclaimed; ACK is terminal; NACK returns an unacknowledged message to pending; TTL expires stale work. Consumers use `message_id`/`correlation_id` for idempotency.

## Codebook lifecycle

Namespaces are hierarchical. Concept registration stores a semantic hash, embedding space, version, status, and aliases. Deprecation can redirect to a replacement ID. Auto-promotion remains conservative and must preserve a lossless fallback.

## Trace context

Wire v2 can carry W3C Trace Context in compact field `z`: `p` contains `traceparent` and `s` contains optional `tracestate`. REST send boundaries import validated `traceparent`/`tracestate` headers when the request body does not already carry trace context.

Trace context is excluded from authorization decisions and is preserved through canonical serialization and cross-runtime TCK validation.

## Cross-runtime conformance

The TCK is normative for canonical MessagePack, digest identity, structural JSON equivalence, validation failure, trace context, signature shape, and A2A wrapping. Python, JavaScript, and Go runners consume the same vector file. Release CI requires all three independent runners plus differential fuzzing so protocol identity is not proven by a single implementation family.
