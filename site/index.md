
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
| Package version | 0.2.6 |
| Protocol | `sage/0.2` |
| Wire version | `2` |
| License | AGPL-3.0 + Commercial (dual-license) |

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

- [Quickstart](Quickstart.md) — install the v0.2.6 release, run the service, Docker quickstart, Hermes and OpenClaw plugins
- [Configuration](Configuration.md) — full environment-variable reference and production rules
- [Architecture](Architecture.md) — semantic bus, references, deltas, patterns, adapters, deployment topology
- [Protocol](Protocol.md) — the `sage/0.2` wire protocol, canonical encoding, TCK, delivery semantics
- [CLI-Tools](CLI-Tools.md) — the 12 console scripts shipped with the wheel
- [Adapters](Adapters.md) — Hermes and OpenClaw plugin integration
- [Development](Development.md) — repo layout, tests, checks, building a release, CI
- [Production](Production.md) — Compose topologies, TLS, migrations, containers, monitoring
- [FAQ](FAQ.md) — common questions

## Current release: v0.2.6

v0.2.6 is a patch release over v0.2.5. Protocol `sage/0.2`, wire version `2`, the `0001_sage_0_2` migration baseline, and the 13 normative TCK vectors are unchanged — no breaking changes, and v0.2.5 peers interoperate with v0.2.6 peers.

Release assets (published on the [v0.2.6 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.6)):

| Asset | Name |
| --- | --- |
| Python wheel | `sage_agent_protocol-0.2.6-py3-none-any.whl` |
| Hermes plugin ZIP | `sage-hermes-plugin-v0.2.6.zip` |
| OpenClaw package | `sage-agent-openclaw-sage-0.2.6.tgz` |
| Source ZIP | `sage-plugin-v0.2.6.zip` |
| Verification report | `SAGE-v0.2.6-VERIFICATION.md` |
| Checksums | `SAGE-v0.2.6-SHA256SUMS.txt` |

What's new in v0.2.6 (the [Issue #22](https://github.com/NeuralBinary/SAGE/issues/22) sealed unseen-data evaluation cycle):

- **Sealed model boundary (PR #23).** The model-evaluation harness gains an opt-in `--sealed` mode: the adapter receives only `{task, model_facing_packet, allowed_decoder_metadata}` plus identity fields — never uncompressed source content, answer keys, change markers, receiver prior, or example meanings. Task success is scored deterministically harness-side; adapter-reported scores are ignored; `SAGE_*` env vars are scrubbed from adapter subprocesses.
- **Actual packet rendering (PR #24).** Sealed `direct-symbolic` SAGE variants face a canonical rendering of the REAL codec packet (atom codes + cv, literals, refs, base, delta ops, prov, wire-whitelisted meta) plus a `bindings` legend — self-contained codes + bindings while the full codebook stays evaluator-side, with wire-byte honesty and round-trip gates.
- **Unseen conversations (PR #25).** `--held-out` evaluates on the Orion fixture with the SAGE codebook frozen from establishment material only; SAGE variants run in both labeled modes (`oracle_codebook: true` upper bound / `false` frozen measurement).
- **Lifecycle-primed warm receiver (PR #26).** Sealed warm rows are established through the real encode → decode(ack) → verify-knowledge lifecycle with a refusing-to-fabricate honesty gate; every sealed row carries `mechanism_used` + the artifact gains `mechanism_summary`. Verified finding documented plainly: primed warm wire bytes equal cold on the current fixtures — the measured benefit is the verified lifecycle + mechanism attribution, not a wire saving. See the [Benchmark](Benchmark.md) page.

What's new in v0.2.5 (the [Issue #16](https://github.com/NeuralBinary/SAGE/issues/16) semantic-context-compression cycle):

- **Context accounting (PR #17).** Default-off (`SAGE_CONTEXT_ACCOUNTING_ENABLED`) instrumentation records per-exchange transport bytes, model-facing token estimates, codebook/pattern setup cost, and reference-fetch volume through the real codec paths — wire byte-identical.
- **Deterministic multi-turn compression benchmark (PR #18).** `scripts/compression_benchmark.py` carries a fixed six-turn conversation through twelve RFC "Phoenix" variants with efficiency, task, fidelity, and amortization tables; the codebook variant (v09) uses 1,172 wire bytes vs 2,027 for the full-context baseline — about 42% less wire — with full semantic fidelity.
- **Model evaluation harness (PR #19).** `scripts/model_eval_harness.py` measures downstream task success on real model runtimes — cold vs warm receivers, at least two model families, RFC six-column result table; provider numbers are never fabricated.
- **Benchmark feedback loop (PR #20).** The harness's `--record-feedback` flag records measured task success via `PatternStore.record_feedback` as an additive `feedback` JSON key, with zero wire-byte change. See the [Benchmark](Benchmark.md) page.

## Verification

The repository ships a verification record (`VERIFICATION.md` in the repo root). v0.2.6 was qualified against the installed wheel with 236 passing tests, 13/13 Python TCK vectors, and a passing `scripts/release_check.py`. Release CI independently runs the JavaScript and Go conformance runners, differential fuzzing, the Docker quick-start gate, and the staging cluster.

## License and attribution

SAGE is dual-licensed:

- **AGPL-3.0** — Free for open source projects, research, and community use, subject to the terms in the repository [LICENSE](https://github.com/NeuralBinary/SAGE/blob/main/LICENSE).
- **Commercial License** — For organizations that want to use SAGE in proprietary products, closed-source services, or SaaS offerings without the AGPL's source-disclosure requirements. See [COMMERCIAL.md](https://github.com/NeuralBinary/SAGE/blob/main/COMMERCIAL.md) or contact **sage@digitalacre.org**.

Author: NeuralBinary. Credits: @NeuralBinary, @ro0ti.

Next: [Quickstart](Quickstart.md)
