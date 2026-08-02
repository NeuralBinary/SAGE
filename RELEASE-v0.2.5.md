# SAGE v0.2.5

Patch release over v0.2.4. Protocol `sage/0.2`, wire version `2`, migration
baseline `0001_sage_0_2`, and the 13 normative TCK vectors are unchanged.

## What's new in v0.2.5

v0.2.5 ships the Issue #16 semantic-context-compression cycle — measuring and
closing the loop on "does SAGE reduce model-visible context while preserving
the downstream result?" — as four additive stages, each merged to main as its
own PR. See https://github.com/NeuralBinary/SAGE/issues/16

- **Context accounting (stage 1, PR #17).** Default-off
  (`SAGE_CONTEXT_ACCOUNTING_ENABLED`) instrumentation
  (`src/sage_plugin/context_accounting.py`) records per-exchange transport
  bytes, model-facing token estimates, codebook/pattern setup cost,
  decoding/expansion cost, and reference-fetch volume through the real
  `codec.py` encode/decode paths — wire byte-identical, with the existing TCK
  vectors unchanged.
- **Deterministic multi-turn compression benchmark (stage 2, PR #18).**
  `scripts/compression_benchmark.py` carries a fixed six-turn conversation
  through twelve RFC "Phoenix" context-compression variants (1–8 plain
  serialization; 9–12 the real `SageCodec`: codebooks, +learned patterns,
  references/state deltas, full ACKed receiver knowledge), separating
  transport, model-visible, and semantic compression into efficiency, task,
  fidelity, and amortization tables. Fully deterministic (no RNG, no
  wall-clock output, fixed timestamp, pinned packet ids, isolated scratch
  database per variant). Honest headline: v09 carries the conversation in
  1,172 wire bytes vs 2,027 for the full-context baseline — about 42% less
  wire — with full semantic fidelity (task success 1.0) and a break-even of 5
  uses; v10 breaks even at 9; v11/v12 do not break even on this short fixture.
- **Model evaluation harness (stage 3, PR #19).** `scripts/model_eval_harness.py`
  measures the same variants' downstream task success on real model runtimes
  through configured external adapters — cold vs warm receivers, at least two
  distinct model families, decoder-assisted token accounting, and the RFC's
  six-column public result table. With no `--adapters` config or
  `SAGE_BENCH_LLM_PROVIDER` it prints `not run, no provider` and exits 0 —
  provider numbers are never fabricated.
- **Benchmark feedback loop (stage 4, PR #20).** The harness's
  `--record-feedback` flag (default off) records each SAGE variant's measured
  task success into the codec's pattern store (`PatternStore.record_feedback`,
  `runtime.feedback` semantics) as an additive `feedback` JSON summary key,
  with zero wire-byte change. Benchmark docs ship in the README and the docs
  site's new Benchmark page.

## Install

### Python wheel

Python 3.11 or newer is required. Download the wheel from the
[v0.2.5 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.5),
then install it and start a local service with authentication disabled only on
a trusted interface:

```bash
python -m venv .venv
. .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install https://github.com/NeuralBinary/SAGE/releases/download/v0.2.5/sage_agent_protocol-0.2.5-py3-none-any.whl
export SAGE_AUTH_REQUIRED=false  # PowerShell: $env:SAGE_AUTH_REQUIRED="false"
sage-api
```

Then verify with `sage-doctor` and `sage-demo --single-agent`.

### Hermes plugin

Download `sage-hermes-plugin-v0.2.5.zip` from the
[v0.2.5 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.5),
then install the plugin:

```bash
unzip sage-hermes-plugin-v0.2.5.zip
cd sage-hermes-plugin-v0.2.5
./install.sh
```

### OpenClaw plugin

Download `sage-agent-openclaw-sage-0.2.5.tgz` from the
[v0.2.5 GitHub release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.5),
then install the native plugin:

```bash
openclaw plugins install npm-pack:./sage-agent-openclaw-sage-0.2.5.tgz
openclaw plugins enable sage
openclaw plugins inspect sage --runtime --json
```

## Release assets

| Asset | Description |
| --- | --- |
| `sage-plugin-v0.2.5.zip` | Source archive |
| `sage-hermes-plugin-v0.2.5.zip` | Hermes plugin |
| `sage_agent_protocol-0.2.5-py3-none-any.whl` | Python wheel |
| `sage-agent-openclaw-sage-0.2.5.tgz` | OpenClaw plugin |
| `SAGE-v0.2.5-VERIFICATION.md` | Verification report |
| `SAGE-v0.2.5-SHA256SUMS.txt` | SHA-256 checksums |

## Upgrade and rollback

Upgrade from v0.2.4 by installing the v0.2.5 wheel and refreshing the Hermes
and OpenClaw plugins from this release. The protocol, wire version, migration
baseline, and TCK vectors are unchanged, so no data migration is required.

To roll back, reinstall the v0.2.4 wheel
(`sage_agent_protocol-0.2.4-py3-none-any.whl` from the
[v0.2.4 release](https://github.com/NeuralBinary/SAGE/releases/tag/v0.2.4))
and re-extract the v0.2.4 Hermes and OpenClaw plugins over the current ones.
