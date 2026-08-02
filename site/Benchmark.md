
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

## No-fabrication rule

Every figure in these tools is either deterministic (measured locally) or
comes from a configured external runtime's reply; a missing provider is
reported as `not run, no provider`, never estimated.

Next: [Protocol](Protocol.md)
