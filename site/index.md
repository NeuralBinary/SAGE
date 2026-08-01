
# Home

**SAGE** is a vendor-neutral **semantic communication runtime and durable context bus for AI agents**. It reduces repeated model context by carrying minimum-sufficient semantic state, content-addressed references, immutable deltas, learned compositional patterns, provenance, and receiver knowledge across agent boundaries.

SAGE core is independent of model providers and agent frameworks. Native and protocol adapters connect the same runtime to Hermes, OpenClaw, Claude, OpenAI, A2A, MCP, REST, Python, and custom orchestrators.

| Field | Value |
| --- | --- |
| Project | SAGE |
| Author | NeuralBinary |
| Repository | https://github.com/NeuralBinary/SAGE |
| Credits | @NeuralBinary, @ro0ti |
| Public version | v0.2 |
| Package version | 0.2.2 |
| Protocol | `sage/0.2` |
| Wire version | `2` |
| License | MIT |

## Key capabilities

- **Semantic bus**: durable, at-least-once, lease-based delivery with claim/ACK semantics (`handoff → pending → claimed → acknowledged`, with lease expiry making stale claims reclaimable).
- **Content-addressed memory**: stored content uses a SHA-256 content identity (`sage:sha256:` prefix); authorization and lifetime policy are separate grants, so identical bytes deduplicate without sharing authorization.
- **Immutable state + lossless deltas**: state updates are represented as JSON-Patch-style deltas when a shared base state exists.
- **Learned compositional patterns**: persistent, receiver-aware, trust-scoped, holdout-validated, drift-aware, counterfactually validated pattern learning with a `candidate → shadow → validated → active` lifecycle.
- **Receiver knowledge**: advances only after acknowledgement, enabling delta-base sends and receiver-aware compression.
- **Semantic safety**: a semantic-loss firewall preserves negation, amounts, identities, authorization, deadlines, and constraints; uncertain optimization fails open to literals or references.
- **Vendor neutrality**: semantics do not depend on MCP, A2A, a model vendor, or hidden model state. A2A carries SAGE as a structured data part; MCP is an optional adapter-only surface.
- **Cross-runtime conformance**: canonical MessagePack plus SHA-256 is the wire identity, independently checked in Python, JavaScript, and Go against 13 normative TCK vectors.
- **Production fail-closed posture**: production mode requires authentication, a server (PostgreSQL) database, managed migrations, explicit allowed hosts, and disabled interactive docs.

## Quick links

- [Quickstart](Quickstart.md) — install the v0.2.2 release, run the service, Docker quickstart, Hermes and OpenClaw plugins
- [Configuration](Configuration.md) — full environment-variable reference and production rules
- [Architecture](Architecture.md) — semantic bus, references, deltas, patterns, adapters, deployment topology
- [Protocol](Protocol.md) — the `sage/0.2` wire protocol, canonical encoding, TCK, delivery semantics
- [CLI-Tools](CLI-Tools.md) — the 12 console scripts shipped with the wheel
- [Adapters](Adapters.md) — Hermes and OpenClaw plugin integration
- [Development](Development.md) — repo layout, tests, checks, building a release, CI
- [Production](Production.md) — Compose topologies, TLS, migrations, containers, monitoring
- [FAQ](FAQ.md) — common questions

## Current release: v0.2.2

v0.2.2 is a patch release over v0.2.1. Protocol `sage/0.2`, wire version `2`, the `0001_sage_0_2` migration baseline, and the 13 normative TCK vectors are unchanged — no breaking changes, and v0.2.1 peers interoperate with v0.2.2 peers.

Release assets (published on the [v0.2.2 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.2)):

| Asset | Name |
| --- | --- |
| Python wheel | `sage_agent_protocol-0.2.2-py3-none-any.whl` |
| Hermes plugin ZIP | `sage-hermes-plugin-v0.2.2.zip` |
| OpenClaw package | `sage-agent-openclaw-sage-0.2.2.tgz` |
| Source ZIP | `sage-plugin-v0.2.2.zip` |
| Verification report | `SAGE-v0.2.2-VERIFICATION.md` |
| Checksums | `SAGE-v0.2.2-SHA256SUMS.txt` |

Key v0.2.2 fixes:

- **Default SQLite path independent of the working directory (Issue #1).** The default database is now `sqlite:///$HOME/sage.db` (the current user's home directory), never a working-directory-relative `./sage.db`. An explicit `SAGE_DATABASE_URL` remains authoritative.
- **OpenClaw adapter type-check/build and conformance surface restored (Issue #3).**

## Verification

The repository ships a verification record (`VERIFICATION.md` in the repo root). v0.2.2 was qualified against the installed wheel with 111 passing tests, 13/13 Python TCK vectors, and a passing `scripts/release_check.py`. Release CI independently runs the JavaScript and Go conformance runners, differential fuzzing, the Docker quick-start gate, and the staging cluster.

## License and attribution

SAGE is licensed under the MIT License. Author: NeuralBinary. Credits: @NeuralBinary, @ro0ti.

Next: [Quickstart](Quickstart.md)
