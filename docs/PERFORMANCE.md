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
