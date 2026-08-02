# SAGE v0.2.6

Patch release over v0.2.5. Protocol `sage/0.2`, wire version `2`, migration
baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged — no
breaking changes, and v0.2.5 peers interoperate with v0.2.6 peers.

## What's new — Issue #22: sealed unseen-data model evaluation

The model-evaluation harness gains a **sealed, unseen-data evaluation mode**
(opt-in `--sealed` / `--held-out`; every non-sealed artifact stays
byte-identical), delivered as four additive, independently verified stages:

- **PR #23 — sealed model boundary.** The adapter (model runner) receives only
  `{task, model_facing_packet, allowed_decoder_metadata}` plus identity fields —
  never uncompressed source content, answer keys, change markers, receiver
  prior, or example meanings. Task success and critical-fact recall are scored
  deterministically harness-side against the private answer key;
  adapter-reported scores are ignored in sealed mode. `SAGE_*` environment
  variables are scrubbed from adapter subprocesses (a hostile adapter cannot
  read the evaluator's ground-truth database through the inherited
  environment).
- **PR #24 — actual packet rendering.** Sealed `direct-symbolic` SAGE variants
  (v09–v12) face a canonical compact-JSON rendering of the REAL codec packet —
  atom codes + cv, literals, refs, base, delta ops, prov, and meta filtered to
  the wire whitelist `{state, revision, budget_exceeded, memory_tier}` — plus a
  `bindings` legend mapping each code to its canonical clause. Wire-byte
  honesty and round-trip gates are tested; the full codebook/pattern store
  stays evaluator-side.
- **PR #25 — unseen conversations.** `--held-out` (requires `--sealed`)
  evaluates on the "Orion" fixture: an establishment phase followed by eight
  held-out updates covering paraphrases, unseen values, new combinations,
  changed state, contradictions, negation, numeric constraints, and
  delayed-relevance. The SAGE codebook is frozen from establishment material
  only; SAGE variants run in both explicitly labeled modes —
  `oracle_codebook: true` (upper bound) and `false` (frozen re-encode
  measurement; unseen content codes as inlined literals).
- **PR #26 — lifecycle-primed warm receiver.** Sealed warm rows are established
  through the real lifecycle (encode shared context → decode with acknowledge →
  verify receiver knowledge committed → encode follow-ups with
  `use_receiver_knowledge=True`); a priming failure raises (`refusing to
  fabricate a warm benefit`). Every sealed row carries `mechanism_used`
  (codebook / learned_pattern / state_delta / reference / capability /
  literal) and the artifact gains an additive `mechanism_summary`. **Verified
  finding, documented plainly:** on the current fixtures primed warm wire bytes
  equal cold — receiver knowledge is decoder-side — so the measured benefit is
  the verified lifecycle + mechanism attribution, not a wire saving; the
  harness never claims one.

Docs: the [Benchmark](https://neuralbinary.github.io/SAGE/Benchmark/) page
gains a "Sealed evaluation mode (issue #22)" section; README and the docs
site's current-release page updated.

## Verification

- Full test suite: **236 tests pass** with the `[dev,mcp,bench,otel]` extras
  (trajectory 184 → 236 across the four stages).
- Each stage independently verified from a clean `git archive` (verifier),
  reviewed (reviewer), and adversarially probed (adversary); all findings
  fixed in hardening commits with regression tests (env-leak detection,
  task-response cap, wire-meta whitelist, scenario-globals restore).
- `scripts/compression_benchmark.py` stayed byte-identical throughout the
  cycle (frozen benchmark golden rule).
- `scripts/release_check.py` → `{"ok":true,"version":"0.2.6","tck_vectors":13}`;
  `package_check.py` passes source / wheel / hermes / openclaw; release CI runs
  the conformance runners, wheel-install, and Docker quick-start gates.

## Assets

| Asset | Name |
| --- | --- |
| Python wheel | `sage_agent_protocol-0.2.6-py3-none-any.whl` |
| Hermes plugin ZIP | `sage-hermes-plugin-v0.2.6.zip` |
| OpenClaw package | `sage-agent-openclaw-sage-0.2.6.tgz` |
| Source ZIP | `sage-plugin-v0.2.6.zip` |
| Verification report | `SAGE-v0.2.6-VERIFICATION.md` |
| Checksums | `SAGE-v0.2.6-SHA256SUMS.txt` |
