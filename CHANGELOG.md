# Changelog

## 0.2.7

- **License Change:** SAGE is now dual-licensed under AGPL-3.0 and a commercial license.
  The MIT license was used for versions 0.2.6 and earlier. See LICENSE and COMMERCIAL.md
  for details.

- **New Files:** Added COMMERCIAL.md explaining the commercial licensing terms and
  .github/FUNDING.yml for GitHub Sponsors.

- **Updated:** CONTRIBUTING.md now reflects the dual-licensing terms for contributors.

## 0.2.6

- Patch release over 0.2.5. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Ships the Issue #22 sealed unseen-data evaluation cycle as four additive stages, each merged to main as its own PR, all default-off (`--sealed`, `--held-out`) with every non-sealed artifact byte-identical:
  - Stage 1 — sealed model boundary (PR #23): the model-evaluation harness gains an opt-in `--sealed` mode. The adapter (model runner) receives only `{task, model_facing_packet, allowed_decoder_metadata}` plus identity fields — never uncompressed source content, answer keys, change markers, receiver prior, or example meanings. Task success and critical-fact recall are scored deterministically harness-side against the private answer key (reusing the benchmark's `evaluate_turn`/`read_state`/`fidelity_critical` checkers); adapter-reported scores are ignored in sealed mode. `SAGE_*` environment variables are scrubbed from adapter subprocesses so a hostile adapter cannot read the evaluator's ground-truth database through the inherited environment.
  - Stage 2 — actual packet rendering (PR #24): sealed `direct-symbolic` SAGE variants (v09–v12) now face a canonical compact-JSON rendering of the REAL codec packet (atom codes + cv, literals, refs, base, delta ops, prov, meta filtered to the wire whitelist `{state, revision, budget_exceeded, memory_tier}`) plus a `bindings` legend mapping each code to its canonical clause. Wire-byte honesty gate (the re-encoded packet's wire bytes equal the benchmark's recorded bytes) and round-trip gate (the rendering decodes to the recorded reconstruction) are tested. Sealed cold v11/v10-turn-0 packets are documented as a reconstruction-fidelity signal (a cold receiver cannot resolve base-state/reference content).
  - Stage 3 — unseen conversations (PR #25): `--held-out` (requires `--sealed`) evaluates on the "Orion" fixture — an establishment phase followed by eight held-out updates covering paraphrases, unseen values, new combinations, changed state, contradictions, negation, numeric constraints, and delayed-relevance. The SAGE codebook is frozen from establishment material only (verified: no held-out canonical leaks in); SAGE variants run in both explicitly labeled modes — `oracle_codebook: true` (upper bound) and `false` (frozen re-encode measurement, held-out content codes as inlined literals).
  - Stage 4 — lifecycle-primed warm receiver (PR #26): sealed warm rows are established through the real lifecycle (encode shared context → decode with acknowledge → verify receiver knowledge committed → encode follow-ups with `use_receiver_knowledge=True`); a priming failure raises (`refusing to fabricate a warm benefit`). Every sealed row carries `mechanism_used` (codebook/learned_pattern/state_delta/reference/capability/literal) and the artifact gains an additive `mechanism_summary`. Verified finding, documented plainly: on the current fixtures primed warm wire bytes equal cold — receiver knowledge is decoder-side — so the measured benefit is the verified lifecycle + mechanism attribution, not a wire saving.
- Updates the docs-site Benchmark page (sealed evaluation mode section), README, documentation, and verification status for v0.2.6.

## 0.2.5

- Patch release over 0.2.4. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Ships the Issue #16 semantic-context-compression cycle as four additive stages. Stage 1 adds context-accounting instrumentation (`src/sage_plugin/context_accounting.py`): per-exchange transport bytes, model-facing token estimates, codebook/pattern setup cost, decoding/expansion cost, and reference-fetch volume recorded through the real `codec.py` encode/decode paths. Default-off (`SAGE_CONTEXT_ACCOUNTING_ENABLED`, default `false`), additive, and wire byte-identical — existing TCK vectors remain byte-identical.
- Stage 2 adds a deterministic multi-turn semantic-context compression benchmark (`scripts/compression_benchmark.py`): twelve RFC "Phoenix" context-compression variants (1–8 plain serialization/string strategies; 9–12 the real `SageCodec`: codebooks only, codebooks + learned patterns, references + state deltas, full SAGE with ACKed receiver knowledge) over a fixed six-turn conversation, separating transport, model-visible, and semantic compression into efficiency, task, fidelity, and amortization tables. Fully deterministic: no RNG, no wall-clock output, a fixed timestamp, pinned packet ids, and an isolated scratch database per variant. Honest headline: the codebook variant (v09) carries the conversation in 1,172 wire bytes vs 2,027 for the full-context baseline (v01) — about 42% less wire — with full semantic fidelity (task success 1.0) and a break-even of 5 uses; v10 (learned patterns) breaks even at 9; the reference/delta (v11) and ACKed-knowledge (v12) variants do not break even within this short fixture.
- Stage 3 adds a model-evaluation harness (`scripts/model_eval_harness.py`) measuring the same variants' downstream task success on real model runtimes through configured external adapters — cold vs warm receivers, at least two distinct model families, decoder-assisted token accounting, and the RFC's six-column public result table. It requires an `--adapters` config and `SAGE_BENCH_LLM_PROVIDER`; with neither it prints `not run, no provider` and exits 0 — provider numbers are never fabricated.
- Stage 4 closes the RFC's feedback loop: the harness's `--record-feedback` flag (default off, so deterministic output is unchanged) records each SAGE variant's measured downstream task success into the codec's pattern store via `PatternStore.record_feedback` (`runtime.feedback` semantics) as an additive `feedback` JSON summary key, with zero wire-byte change. Adds benchmark documentation (README and docs-site Benchmark page).
- Updates documentation, release artifacts, and verification status for v0.2.5.

## 0.2.4

- Patch release over 0.2.3. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Fixes the MCP integration for repeated application startups (Issue #11): the FastMCP server is now built fresh on every app lifespan behind a stable delegating mount at `/mcp`, with an owner-guarded live-install stack so overlapping lifespans hand the mount back instead of clobbering it. Repeated app startups with the `mcp` extra now work, and pytest phases plus the release workflow install `[dev,mcp,bench,otel]` again.
- Hardens the latency gate on shared CI runners: `--best-of 3` rounds (was best-of-2), with all limits unchanged.
- Ships the wiki-styled GitHub Pages documentation site (MkDocs Material: sidebar navigation, search, dark mode) as the project's public docs.
- Updates documentation, release artifacts, and verification status for v0.2.4.

## 0.2.3

- Patch release over 0.2.2. Protocol `sage/0.2`, wire version `2`, migration baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.
- Fixes a concurrency race in the receiver knowledge store: `ensure()` and `_add_value()` are now race-safe (savepoint + integrity handling), eliminating `IntegrityError: duplicate key ... uq_receiver_knowledge` under concurrent qualification load (PostgreSQL and SQLite).
- Restores the CI pipeline to green: fixes `release_check.py` ordering (OpenClaw `dist` built before the check, `node_modules`/caches cleaned), stale `0.2.2` artifact names in the package/openclaw jobs, the staging PostgreSQL volume mount for the postgres 18 image, and the staging recovery verification (correct `/v1/bus/{message_id}/ack` endpoint; stop-based worker failover; bounded retries for load-balancer failover).
- Pins the `mcp` extra to `mcp>=1.9,<2` so `sage-mcp`'s FastMCP integration builds again (mcp 2.x removed `mcp.server.fastmcp`).
- Makes the latency gate robust on shared CI runners: steady-state sampling (warmup, outlier trimming, best-of-2 rounds) with unchanged limits.
- Documents the mcp streamable-session-manager single-run limitation (Issue #11) and keeps pytest phases on `[dev]`; MCP is qualified via the package job's `build_server()` assertion.
- Updates documentation, release artifacts, and verification status for v0.2.3.

## 0.2.1

- Keeps protocol `sage/0.2`, wire version `2`, and migration baseline `0001_sage_0_2` unchanged.
- Constrains Hermes `sage_handoff.content` to raw structured application data.
- Defensively recovers JSON object strings while rejecting plain text and already-encoded SAGE semantic envelopes.
- Applies the same structured-content boundary to the OpenClaw adapter.
- Ships a standalone Hermes plugin that does not require package installation inside Hermes.
- Adds direct source-checkout and GitHub release install paths for Hermes and OpenClaw.
- Adds workspace-aware `sage-integrate` output and release-asset guidance.
- Adds regression coverage for the adapter boundary found during live Hermes integration testing.
