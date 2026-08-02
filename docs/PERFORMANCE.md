# Performance and latency

SAGE performance work is directed at reducing both model-context cost and runtime overhead. Wire size alone is insufficient; latency, database operations, network round trips, token usage, cache behavior, and downstream task fidelity are measured separately.

## Local regression gate

Run:

```bash
python scripts/performance_check.py --iterations 200
```

The deterministic local gate measures:

| Operation | p95 ceiling |
| --- | ---: |
| Core encode | 40 ms |
| Core decode | 10 ms |
| REST transport send | 75 ms |
| REST transport receive | 50 ms |

The gate uses local SQLite, disables pattern learning and semantic caching for repeatability, warms the process before measurement, and reports p50, p95, maximum latency, and pass/fail state. The thresholds are regression ceilings for the development/CI workload rather than production service-level objectives.

## Adapter latency

Native adapters use `/v1/bus/context/{receiver}` to claim and decode a bounded set of messages in one server round trip. Successful turns use `/v1/bus/ack-batch` to acknowledge the consumed set in one request. This avoids one decode request and one acknowledgement request per message.

OpenClaw uses `agent_turn_prepare`, the host lifecycle phase intended for same-turn queued context injection, and retains `agent_end` for terminal success state. Hermes performs the same claim/decode and batch acknowledgement flow through its native hooks.

## Database

Production uses PostgreSQL. Pool defaults are:

- pool size: 10
- max overflow: 20
- pool wait timeout: 30 seconds
- connection recycle: 1800 seconds
- pool pre-ping enabled

Tune these values to deployment concurrency and database limits. Connection pooling is not applied to SQLite development databases.

The codebook keeps per-runtime concept-chain caches and invalidates them on vocabulary mutation to avoid repeated full concept queries during encoding.

## Context economics

The economics API separates structural SAGE, learned codebook use, receiver knowledge, state/reference strategies, raw context, and caller-supplied summary/retrieval results. Provider token usage can be submitted as observed measurements so cost-per-success is based on actual usage rather than inferred provider behavior.

The benchmark supports deterministic character-based estimates for engineering comparison, exact local counting through the optional tokenizer package, and an HTTP tokenizer boundary for providers or local runtimes with independent tokenization.

## Production factors

Production latency is affected by:

- database network distance and transaction contention
- reference object size and encryption
- external embedding/tokenizer services
- claim volume and bus backlog
- payload size and atom count
- semantic pattern matching volume
- signature verification
- federation requests
- telemetry exporters
- host adapter scheduling

Keep SAGE, PostgreSQL, and latency-sensitive agent runtimes within low-latency network boundaries when possible. Large content should remain reference-backed rather than materialized into the handoff path.

## Measurement policy

Performance changes should be accepted only when semantic fidelity and correctness remain unchanged. A smaller packet that changes downstream task behavior is considered a regression regardless of byte or token reduction.

## v0.2 qualification

`SAGE` includes a qualification runner:

```bash
sage-qualify --configured-concurrency --workers 8 --messages 20
```

On PostgreSQL this runs concurrent producers and consumers against the configured database and requires every durable message to be consumed once by the qualification run with no pending remainder. SQLite runs concurrent producers but uses one consumer because SQLite does not provide PostgreSQL `FOR UPDATE SKIP LOCKED` semantics.

The Python profiler also records SQL statement count per encode operation. Release tests enforce a query ceiling so a change cannot hide N+1 database growth behind a small fixture.

## Large vocabulary

Exact concept lookup remains indexed. Fuzzy matching uses exhaustive comparison only below `SAGE_SEMANTIC_FUZZY_SCAN_LIMIT`. Larger vocabularies use deterministic locality-sensitive-hash buckets, bounded Hamming-neighbor search, and `SAGE_SEMANTIC_CANDIDATE_LIMIT`.

If the bounded candidate set cannot establish a safe match, SAGE transmits a lossless literal/reference representation. Runtime cost therefore remains bounded rather than falling back to an unbounded full-vocabulary scan.

Scale qualification should record exact and fuzzy p50/p95/p99 latency at increasing vocabulary sizes and treat both latency and semantic fidelity as release gates.

The dispatch-only `.github/workflows/scale.yml` extends qualification to 1,000,000 concepts by default and runs a configurable PostgreSQL/TLS staging soak without slowing ordinary pull-request gates.

## Vocabulary and query budgets

Run `sage-qualify --vocabulary 100,1000,5000` to measure exact and bounded-fuzzy lookup. Exact lookup remains indexed; vocabularies beyond the configured scan limit use bounded LSH candidate retrieval. Run `sage-qualify --profile-encode --profile-iterations 30 --max-query-count 40` before release. The command fails when the encode SQL statement budget is exceeded even when wall-clock latency remains below the local ceiling.

## Distributed qualification

`deploy/staging/compose.yml`, `scripts/soak_cluster.py`, and `scripts/cluster_chaos.py` provide the production-shape qualification path: PostgreSQL, three SAGE workers, TLS load balancing, durable handoff/claim/ACK, worker loss, database outage, readiness failure, and recovery. CI executes a short gate; long-running release candidates should use the same tooling for sustained load.

## Cross-model task economics

`src/sage_plugin/corpus.py` defines a reproducible JSONL task corpus containing sender state, receiver prior state, full context, task intent, expected outcome, and strategy representations. `scripts/model_matrix_benchmark.py` invokes explicitly configured model commands and records observed task success, input/output tokens, latency, retries, semantic loss, wire bytes, and provider/infrastructure cost. It never fabricates provider measurements when a model adapter or credentials are absent.

Release analysis should compare raw context, caller-supplied retrieval/summary strategies, state+refs, structural SAGE, learned patterns, and receiver-aware SAGE. The primary economic metrics are net successful-task savings and task utility per transmitted bit, not compression ratio alone.

## Semantic context compression benchmark and model evaluation harness

The deterministic compression benchmark (`scripts/compression_benchmark.py`) separates transport, model-visible, and semantic compression for the twelve RFC "Phoenix" variants over a fixed six-turn conversation. It is fully deterministic (no RNG, fixed timestamp, pinned packet ids, isolated per-variant scratch database) and requires no provider. Its honest headline, reproducible with `uv run --with '.[dev,mcp]' python scripts/compression_benchmark.py`:

- v09 SAGE codebooks: 1,172 wire bytes vs 2,027 baseline (v01) — about 42% less wire — with full fidelity (task success 1.0, all per-fact-type fidelity checks 1.0); codebook setup 675 bytes, break-even 5 uses.
- v10 codebooks + learned patterns: 1,341 wire bytes, setup 946 bytes, break-even 9 — the pattern's setup exceeds this short fixture's repayment horizon.
- v11 references + state deltas and v12 ACKed receiver knowledge: negative per-use savings on this fixture (break-even equals setup cost, i.e. no break-even within six turns). These rows are deliberately honest about the short fixture; pattern amortization is a longer-conversation effect.

The model-evaluation harness (`scripts/model_eval_harness.py`, issue #16 stage 3) measures the same variants' downstream task success on real model runtimes through configured external adapters:

- cold vs warm receivers (warm = ACKed shared context prior), both reported, plus warm-vs-cold deltas;
- at least two distinct model families (config gate) and the RFC's six-column public result table (`| Variant | Wire bytes | Input tokens | Total cost | Task accuracy | Critical-fact recall |`);
- decoder-assisted mode counts expansion tokens in `input_tokens` (RFC "prevent hidden decompression costs"): decoding-step tokens are always counted, a conservative upper bound when the adapter already bills the expanded text;
- deterministic artifacts (byte-identical across runs modulo the measured per-adapter-call `latency_ms`); no provider configured means `not run, no provider`, exit 0 — provider numbers are never fabricated.

Stage 4 closes the feedback loop: `--record-feedback` records each SAGE variant's measured task success (the mean of the adapter-reported `task_success` for that variant's rows) into the codec's pattern store through the existing `PatternStore.record_feedback` path — mirroring `runtime.feedback` semantics (`task_success` validated to `[0, 1]`, `KeyError` on an unknown packet id, decisions from the `MessageAudit` rows the real encodes created). The result is an additive top-level `feedback` JSON key in the artifact (patterns updated, `task_utility`/`utility_score` before and after per pattern), with zero wire-byte change: feedback is post-hoc database bookkeeping and never touches encode. Default OFF keeps artifacts byte-identical to a run without the flag.
