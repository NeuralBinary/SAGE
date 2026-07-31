# Threat model

SAGE assumes that agents, adapters, networks, federation peers, model output, and semantic learning input may be malicious or compromised. The security boundary is the SAGE runtime plus its configured database, cryptographic keys, authentication policy, and deployment controls.

## Assets

SAGE protects semantic packets, references, shared states, learned concepts and patterns, receiver knowledge, provenance, audit history, credentials, signing keys, encryption keys, routing policy, calibration evidence, and federation policy.

## Trust boundaries

The primary boundaries are:

- agent runtime to SAGE adapter
- adapter to SAGE HTTP or MCP endpoint
- SAGE process to PostgreSQL
- SAGE process to embedding/tokenizer services
- local SAGE instance to federation peer
- SAGE telemetry to monitoring backend
- operator control plane to agent-scoped data plane

A successful authentication at one boundary does not grant authority at another.

## Attacker capabilities

The design considers an attacker able to:

- control an agent and submit repeated semantic observations
- inject untrusted model or tool output
- replay, duplicate, delay, reorder, or truncate network traffic
- submit malformed or oversized packets
- attempt reference enumeration and cross-workspace access
- claim another agent identity through request fields
- poison learned vocabulary or receiver calibration
- provide conflicting facts or stale derived knowledge
- manipulate federation input
- force expensive fuzzy matching or pattern mining
- attempt signature bypass or key confusion
- infer private information through telemetry or derived semantic artifacts
- crash a consumer after claim and before acknowledgement

Compromise of the host operating system, database administrator, or active cryptographic private key is outside the guarantees of the application layer and requires infrastructure incident response.

## Identity and authorization

Service credentials authorize control-plane operations. Agent credentials bind to a workspace and agent identity. Request fields cannot override that authenticated identity.

Content identity and authorization are separate. A `sage:sha256:` reference identifies bytes; access is controlled by grants. Delegation and policy mutation require the explicit owner or a service credential. Selective field resolution is constrained by the grant.

## Learned-language poisoning

Pattern learning is treated as security-sensitive state mutation.

Normal agent sends contribute source evidence only from the authenticated logical sender. Arbitrary provenance fields do not create source diversity. Source identity is persisted as a SHA-256 hash in the learning evidence table.

Promotion requires configured source diversity, maximum dominant-source share, minimum trust, utility, savings, lifecycle validation, and counterfactual evidence. Trust scopes become progressively stricter from session through federation scope. One sender cannot obtain broader vocabulary authority through repetition alone.

Receiver/model/task calibration is stored separately. An active pattern is suppressed for a receiver when observed fidelity is below policy. Compression falls back to richer semantics instead of selecting an unsafe near match.

## Semantic integrity

The semantic-loss firewall treats negation, authorization, identities, irreversible instructions, quantities, money, deadlines, environments, security constraints, and other critical values as high-risk information.

Epistemic types distinguish facts, observations, inferences, hypotheses, predictions, preferences, instructions, and constraints. Contradictory claims coexist with provenance. Dependency invalidation marks downstream knowledge stale rather than silently rewriting history.

## Packet integrity and replay

Ed25519 signatures cover canonical MessagePack bytes with the signature removed from the signed body. Signature-required deployments reject unsigned traffic and require a configured verification key.

Delivery is at-least-once. Message IDs and correlation IDs provide idempotency keys for consumers. Claim leases recover work after consumer failure. ACK is the point at which receiver knowledge changes.

Trace context is diagnostic metadata, not authentication data. `traceparent` and `tracestate` are validated but never used as authorization input.

## Denial of service

HTTP request bodies, packet size, atom count, inline data, stored data, claim batch size, semantic candidate count, fuzzy vocabulary scans, and pattern observations are bounded.

Large-vocabulary fuzzy search uses deterministic LSH buckets and a bounded candidate set. If the bounded set cannot establish a safe semantic match, SAGE preserves the literal/reference form rather than performing an unbounded scan.

PostgreSQL connection pooling, query-count qualification, latency gates, and bus concurrency qualification detect growth in database work before release.

## Federation

Federation is deny-by-policy. Peers can have independent verification keys, namespace allowlists, and trust configuration. Remote concepts and patterns enter local lifecycle controls; peer assertion alone cannot activate local vocabulary.

Federated pattern scope has the highest default source-diversity requirement. Production operators should use separate trust policy for internal and external peers.

## Telemetry

Telemetry exports operational metadata only by default. SAGE does not emit message content, literals, reference payloads, secrets, credentials, or raw model prompts as span attributes.

W3C trace context is propagated so one distributed trace can correlate agent, SAGE, database, adapter, and downstream operations without copying semantic content into telemetry.

## Required operator controls

Production startup fails unless authentication, server database, managed migrations, explicit allowed hosts, and disabled interactive documentation are configured. Operators must provide TLS, network policy, secret storage, key rotation, database backup, audit retention, dependency monitoring, and infrastructure access control.
