# SAGE semantic fabric

SAGE v0.1 is a vendor-neutral semantic transport/runtime. The model/framework adapters are thin; semantic safety, learned patterns, memory, routing, signatures, and conformance live in core.

## Semantic safety

Every compiled unit is classified for semantic risk and epistemic type. Critical meanings such as negation, amounts, identity, authorization, deadlines, production/staging markers, instructions, and constraints use the strict preservation threshold. If SAGE cannot establish a sufficiently reliable mapping, it sends the literal or a reference instead of assigning an uncertain interpretation.

Semantic memory distinguishes `fact`, `observation`, `inference`, `hypothesis`, `prediction`, `preference`, `instruction`, and `constraint`. Contradictory subject/predicate claims coexist as explicit conflict records. Facts may declare dependencies; invalidating a source recursively marks derived facts stale.

## Recursive learned patterns

Patterns have a lossless flattened template plus an optional graph of child patterns. This lets SAGE learn reusable concepts recursively without making decoding depend on hidden model state.

Promotion uses frequency, estimated savings, stability, utility, ambiguity, and interoperability. New patterns enter shadow mode. Task feedback can move them to validated, but the production default requires counterfactual full-vs-compressed evidence before activation. Reliability is tracked by receiver/model; a pattern that is poor for one receiver is suppressed there while remaining usable elsewhere.

Namespaces form an inheritance chain such as:

```text
core
software
software.python
software.python.project
```

High-utility local patterns can be promoted to a parent namespace. Unused active patterns cool and eventually retire; use reactivates a cooling pattern.

## Content-addressed memory

Canonical content maps to a global identity:

```text
sage:sha256: followed by 64 lowercase hexadecimal characters
```

The object identity is independent of workspace policy. ACLs, allowed field paths, TTL, tier, owner and provenance are stored as grants. Identical content deduplicates globally while different workspaces can hold different grants.

Selective disclosure resolves only permitted paths. Zero-copy forwarding adds a receiver grant to the existing ref and sends the ref; it does not duplicate the blob.

## Semantic pub/sub and routing

Agents can subscribe to semantic concepts plus filters. Publication compiles content and enqueues only matching subscribers.

Capability routing considers required capability/authority, availability, cost, latency, receiver knowledge and declared semantic expertise. The routing weights are configurable.

## Federation

Federation exchanges selected codebook namespaces, not an entire private SAGE instance. Peers have explicit allowed namespace prefixes and optional Ed25519 public keys. Exported bundles can be signed; imports verify peer identity/namespace and re-observe learned patterns locally so foreign patterns must earn local trust.

## Inspector and telemetry

`Inspector` exposes packet/run compression waterfalls, receiver-known ratio, semantic-loss score, refs, pattern decisions and estimated token counts.

```bash
sage-inspect --packet P...
sage-inspect --run run-123 --json
```

With the `otel` extra and `SAGE_OTEL_ENABLED=true`, SAGE emits OpenTelemetry spans/counters using `gen_ai.operation.name` for the operation and `sage.*` measurements for protocol-specific signals. Useful metrics include packet bytes, original/sent token estimates, semantic loss, receiver-known ratio, pattern count and bytes avoided by refs.

## Conformance

```bash
sage-conform
sage-conform --fuzz 1000
```

The TCK verifies canonical JSON/MessagePack, digest, schema rejection, and A2A DataPart round trips. The mutation pass deliberately corrupts frozen wire invariants and requires the validator to reject them. Language/framework adapters should run the same packaged vectors.
