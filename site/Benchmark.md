
# Semantic context compression benchmark

SAGE ships a deterministic multi-turn compression benchmark and an opt-in
model-evaluation harness that answer the RFC question — *does SAGE reduce
model-visible context while preserving the downstream result?* — as a
measurable, reproducible capability (Issue #16).

## Compression levels

`scripts/compression_benchmark.py` measures how twelve context-compression
strategies (the RFC "Phoenix" variants) carry a fixed six-turn conversation,
separating three compression levels:

- **transport compression** — wire bytes actually transmitted (canonical JSON and MessagePack),
- **model-visible compression** — the tokens the receiver model must consume (input/output of the transmitted representation),
- **semantic compression** — downstream task success, state reconstruction, and per-fact-type fidelity against an embedded ground-truth answer key.

## Variants

Variants 1–8 are plain serialization/string strategies; variants 9–12 run the
real `SageCodec`:

| Variant | Strategy |
| --- | --- |
| v01–v08 | plain serialization/string strategies (v01 = full-context baseline) |
| v09 | codebooks only |
| v10 | codebooks + learned patterns |
| v11 | references + state deltas |
| v12 | full SAGE with ACKed receiver knowledge |

The benchmark is fully deterministic: no RNG, no wall-clock output, a fixed
timestamp, pinned packet ids, and an isolated scratch database per variant.

## Results from the deterministic run

Honest headline (all numbers reproducible locally, see below): the SAGE
codebook variant (v09) carries the full conversation in **1,172 wire bytes vs
2,027 for the full-context baseline (v01) — about 42% less wire — with full
semantic fidelity (task success 1.0, all fidelity checks 1.0)**. Its
amortization break-even is 5 uses: the 675-byte codebook setup is repaid after
five exchanges of this fixture. Adding learned patterns (v10) costs more setup
(946 bytes, break-even 9) and saves less per use on a conversation this short;
the reference/delta (v11) and ACKed-knowledge (v12) variants post negative
per-use savings (break-even equals setup cost, i.e. they do not break even
within the fixture). Patterns amortize over longer conversations than this
fixture shows — the benchmark measures the RFC's "shared shorthand may
initially cost more" question honestly rather than manufacturing a win. The
ACKed-knowledge rows are honest that this short fixture cannot repay
receiver-knowledge setup.

## Running the benchmark

Run it (deterministic, no provider required):

```bash
uv run --with '.[dev,mcp]' python scripts/compression_benchmark.py            # printed tables
uv run --with '.[dev,mcp]' python scripts/compression_benchmark.py --out DIR  # + JSON/CSV artifacts
```

## Model evaluation harness

The model-evaluation harness (`scripts/model_eval_harness.py`) measures the
same variants' downstream task success on real model runtimes through
configured external adapters — cold vs warm receivers, at least two distinct
model families, decoder-assisted token accounting, and the RFC's six-column
public result table. It requires an `--adapters` config (see its module
docstring) and `SAGE_BENCH_LLM_PROVIDER`; with neither it prints
`not run, no provider` and exits 0 — provider numbers are never fabricated.
With `--record-feedback` it also records each SAGE variant's measured task
success into the codec's pattern store (`PatternStore.record_feedback`,
`runtime.feedback` semantics) as an additive `feedback` JSON summary key, with
zero wire-byte change. Raw artifacts are written outside the repository.

```bash
SAGE_BENCH_LLM_PROVIDER=fake uv run --with '.[dev,mcp]' \
    python scripts/model_eval_harness.py --adapters adapters.json --output /path/outside/repo
```

## Sealed evaluation mode (issue #22)

Issue #22 adds an opt-in **sealed** evaluation mode to the harness so real
models are tested on the actual compact SAGE packet under a hard boundary:
the model runner never sees uncompressed source content, answer keys, or any
other evaluator-only knowledge, and the SAGE variants can be evaluated on
**unseen conversations** against a **frozen codebook**, with a warm receiver
established through the **real SAGE lifecycle** instead of a simulated prior.
Both new flags default OFF — every non-sealed artifact stays byte-identical.

### The sealed boundary

With `--sealed` the adapter (model runner) receives ONLY:

- `task` — a deterministic per-variant instruction derived from the exchange;
- `model_facing_packet` — the compact representation;
- `allowed_decoder_metadata` — `codebook_version`, `receiver_state`, `decoder_configuration`;
- identity fields — `variant`, `variant_name`, `turn`, `phase`, `receiver_state`,
  `decoder_configuration`, `wire_bytes` (and `symbolic_examples`, always
  `false` in sealed mode).

It NEVER receives `content`, `expected`, `change_markers`, `receiver_prior`,
or `examples` — the model runner cannot see the evaluator's ground truth. The
adapter replies with a `task_response` text (plus token/cost figures); the
harness scores that text **deterministically harness-side** against the
private answer key, reusing the benchmark's `evaluate_turn` / `read_state` /
`fidelity_critical` checkers. Adapter-reported `task_success` /
`critical_fact_recall` are **ignored in sealed mode** — the adapter has no
answer key. `--sealed` also rejects `--with-examples` (example meanings are
evaluator-side decoder knowledge), and the harness scrubs `SAGE_*` environment
variables from adapter subprocesses — a hostile adapter cannot read the
evaluator's ground-truth database through the inherited environment
(verified locally with an env-leak-detecting fake adapter).

### The actual packet (sealed direct-symbolic)

In sealed `direct-symbolic` mode the SAGE variants' (v09–v12)
`model_facing_packet` is no longer a clause proxy: it is a canonical
compact-JSON rendering of the **real codec packet** for that `(variant,
turn)` — deterministically re-encoded through the codec exactly like the
benchmark (pinned packet ids, fixed provenance). The rendering carries the
packet's atom codes + cv bindings + literals, refs, base, delta ops, prov,
and `meta` **filtered to the wire whitelist** `{state, revision,
budget_exceeded, memory_tier}` — the exact subset the wire codec exports;
evaluator-side meta (codebook fingerprint, strategy, receiver-knowledge
counts) never leaves the evaluator — plus a `bindings` legend mapping each
`code:cv` to its canonical clause (learned-pattern atoms expand to the
pattern's canonical). The packet is self-contained: a model can answer from
codes + bindings while the full codebook/pattern store stays evaluator-side.

Two honesty gates are tested: the re-encoded packet's **wire bytes equal the
benchmark's recorded bytes** for the same `(variant, turn)` (the rendering
corresponds to the packet the benchmark actually measured), and the rendering
**round-trips** — parsed back and decoded by the real codec it yields the
benchmark's recorded reconstruction. Sealed cold v11 (base-hash + delta) and
v10 turn-0 packets are a reconstruction-fidelity signal, not a rendering
defect: a cold receiver cannot resolve base-state/reference content, so those
scores are structurally bounded — the real SAGE cold-receiver behavior; the
lifecycle-primed warm rows below anchor base-state resolution exactly as the
codec's own primed lifecycle provides it.

### The held-out split

`--held-out` (requires `--sealed`; a clean exit-2 error otherwise) evaluates
the sealed harness on an **unseen conversation**: a new fixture
(`scripts/heldout_scenario.py`) — project "Orion", distinct from the RFC
Phoenix fixture — with an establishment phase (shared context transmitted
once) followed by **8 held-out updates** covering paraphrased concepts, unseen
values, new combinations of known concepts, changed state, contradictions,
negation, numeric constraints, and delayed-relevance, with matching state
dicts and change markers. The SAGE variants' codebook is **FROZEN from the
establishment material only** (verified: none of the held-out updates'
canonicals leak into the frozen list).

Every SAGE variant runs in **both labeled modes**: `oracle_codebook: true`
(the codebook was allowed to see everything — the benchmark-recorded upper
bound) and `oracle_codebook: false` (the frozen re-encode — the real
measurement). The frozen variants' wire bytes come from the deterministic
re-encode against the frozen codebook; held-out content genuinely codes as
inlined literals. Measured locally on the Orion fixture (reproducible with
the commands below): v09 carries the six turns in **1,607 wire bytes with the
frozen codebook vs 1,248 with the oracle codebook** — about 29% more wire —
with the divergence concentrated in the held-out turns (turn 1: 244 B frozen
vs 182 B oracle; the frozen rows' `mechanism_used` is `literal`). The
compression cost of novelty is measured honestly. One label caveat for
v11/v12: their oracle codebook is not the frozen codebook plus the updates —
v11's oracle codebook is empty (references + state deltas) and v12's is the
state-field keys — so their frozen-vs-oracle delta mixes codebook-kind with
frozen-ness; the rows stay labeled, never merged.

### The lifecycle-primed warm receiver

In sealed mode the warm receiver is no longer simulated: sealed warm rows are
established through the **real lifecycle**. Before each SAGE variant's warm
exchanges the harness encodes the shared context with a pinned packet id,
delivers it, decodes with `acknowledge=True`, **verifies** the receiver
knowledge committed in the store (known codes / known refs / current state),
and only then encodes the follow-up turns with
`use_receiver_knowledge=True`. A priming failure **raises** — a warm row is
never emitted with a fabricated benefit (`refusing to fabricate a warm
benefit`). Every sealed row carries `mechanism_used` (the primary compression
mechanism of the turn's real encode: `codebook` / `learned_pattern` /
`state_delta` / `reference` / `capability` / `literal`, derived from the
packet's strategy + atoms/refs/base), and the artifact gains an additive
`mechanism_summary` (per-variant mechanism counts).

**Honest finding (verified, not manufactured):** on the current fixtures the
primed warm wire bytes **equal** the cold wire bytes — receiver knowledge is
decoder-side and does not change the wire on this fixture (verified locally:
every sealed row's warm-vs-cold wire delta is 0). The measured benefit of the
warm mode is therefore the **verified lifecycle + mechanism attribution**, not
a wire saving — and the harness never claims one. The tests assert that
equality rather than hiding it.

### Running sealed evaluation

```bash
SAGE_BENCH_LLM_PROVIDER=<provider> uv run --with '.[dev,mcp,bench,otel]' \
    python scripts/model_eval_harness.py --adapters adapters.json --sealed \
    --output /path/outside/repo            # sealed, standard scenario

SAGE_BENCH_LLM_PROVIDER=<provider> uv run --with '.[dev,mcp,bench,otel]' \
    python scripts/model_eval_harness.py --adapters adapters.json --sealed \
    --held-out --output /path/outside/repo # sealed, held-out Orion scenario
```

As with the non-sealed harness, a missing provider is reported as
`not run, no provider` (exit 0) — sealed-mode results are never estimated.

## No-fabrication rule

Every figure in these tools is either deterministic (measured locally) or
comes from a configured external runtime's reply; a missing provider is
reported as `not run, no provider`, never estimated.

Next: [Protocol](Protocol.md)
