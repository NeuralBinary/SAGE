"""Opt-in model evaluation harness (issue #16, stage 3).

This script runs the stage-2 compression benchmark's receivers on real model
runtimes through external adapter commands, measuring COLD and WARM receivers
separately.  It is opt-in: with no ``--adapters`` config (or when
``SAGE_BENCH_LLM_PROVIDER`` is unset) it prints ``not run, no provider`` and
exits 0 -- provider numbers are never fabricated (mirroring
``scripts/compression_benchmark.py`` and ``scripts/model_matrix_benchmark.py``).

Design
------
A NEW script that REUSES the stage-2 benchmark
(``scripts/compression_benchmark.py``) instead of mutating it.  The stage-2
benchmark stays byte-deterministic and its determinism tests pass unchanged;
the harness loads it as a module (same importlib pattern the tests use) and
consumes its deterministic per-variant per-turn records (wire bytes,
reconstructions), its scenario fixture (``SHARED_CONTEXT``/``UPDATES``/
``STATE_DICTS``/``CHANGE_MARKERS``), its ground-truth answer key
(``ground_truth_answers``) and its deterministic token estimator.  The
harness itself never calls a model and never fabricates results: every
``task_success``/token/cost figure comes from the adapter's JSON reply.

Adapter convention (mirrors ``scripts/model_matrix_benchmark.py``)
-----------------------------------------------------------------
An adapters JSON config maps ``model_identity -> spec``::

    {
      "acme-gpt-4o": {
        "family": "acme",
        "version": "gpt-4o-2026-05",
        "codebook_version": "global:1",      # optional, default "global:1"
        "command": ["python", "-c", "..."]   # argv; JSON on stdin, JSON on stdout
      },
      "nebula-sonnet": {
        "family": "nebula",
        "version": "sonnet-2026-07",
        "command": [...]
      }
    }

The harness invokes each ``command`` with a compact-JSON payload on stdin
(``separators=(",", ":")``, exactly like ``_invoke`` in
``model_matrix_benchmark.py``) and expects JSON on stdout.  Required reply
fields (model_matrix's full contract is the floor): ``task_success``,
``input_tokens``, ``output_tokens``, ``provider_cost_usd``.  Optional:
``infrastructure_cost_usd``, ``retrieval_cost_usd``, ``retry_cost_usd``,
``cost_usd`` (else the sum of the cost components), ``latency_ms``,
``retrievals``, ``tool_calls``, ``retries``, ``semantic_loss``,
``reconstruction`` (text the receiver produced; used by the harness-side
critical-fact-recall scoring) and ``critical_fact_recall`` (adapter-reported;
preferred over the harness-side score).

Payload contract (per exchange): ``protocol: "sage/0.2"``,
``benchmark: "compression_benchmark:phoenix_rfc"``, ``variant`` /
``variant_name``, ``turn`` / ``phase``, ``receiver_state`` (``"cold"`` =
fresh receiver with no prior state; ``"warm"`` = receiver prior established
from the shared-context phase, e.g. codebook/patterns ACKed), ``receiver_prior``
(ACKed shared context for warm, ``null`` for cold), ``decoder_configuration``
(one of the RFC's three modes), ``symbolic_examples`` (whether the model saw
symbolic-format examples; when true an ``examples`` list with a sample packet
+ its meaning is included), ``representation`` (the symbolic wire form:
the stage-2 reconstruction for plain variants, a deterministic symbolic
packet rendering for SAGE variants), ``wire_bytes``, ``model_facing_text``
(the text the model is asked to consume), ``content`` (the message/state the
sender conveyed), ``expected`` (the per-turn ground-truth answer key) and
``change_markers``.

RFC field mapping (per result row)
----------------------------------
* receiver model        -> ``receiver_model`` (the config identity)
* model version         -> ``model_version`` (config ``version``)
* codebook version      -> ``codebook_version`` (config, default ``global:1``)
* decoder configuration -> ``decoder_configuration`` (one of
  ``direct symbolic`` / ``decoder-assisted`` / ``full natural-language
  expansion``, from ``--decoder-mode``)
* symbolic-format examples -> ``symbolic_examples`` (bool, from
  ``--with-examples``)
* cold vs warm           -> ``receiver_state``

Cold vs warm
------------
Every selected variant's six exchanges are run twice per adapter: once
``cold`` (``receiver_prior: null``) and once ``warm`` (prior = the ACKed
shared context).  Both rows are reported, plus warm-vs-cold deltas (wire
bytes, input tokens, cost, task accuracy, critical-fact recall).

Decoder modes (RFC "Model-facing evaluation modes")
---------------------------------------------------
* ``direct-symbolic`` (default): the model sees the compact representation;
  ``model_facing_text`` == ``representation``; no expansion tokens.
* ``decoder-assisted``: the harness expands the packet to model-facing text
  BEFORE sending (``model_facing_text`` == the stage-2 deterministic
  reconstruction) and ADDS the expansion tokens to the adapter-reported
  ``input_tokens`` (RFC "Prevent hidden decompression costs": decoding-step
  tokens are always counted; the reported input tokens are a conservative
  upper bound when the adapter already bills the expanded text).
* ``full-expansion``: the packet is reconstructed to ordinary language;
  the adapter reports the tokens it actually consumed.

>=2 model families gate
-----------------------
The config must cover at least 2 DISTINCT ``family`` values; a config with
<2 families is rejected with a clear error (RFC acceptance criterion 4 /
stage-3 "run the receiver task using at least two model families").

Public result format (RFC "Proposed public result format")
----------------------------------------------------------
The printed table and ``--output`` artifact use the RFC's six columns,
one row per (variant, receiver, cold/warm) combination, sorted
deterministically::

    | Variant | Wire bytes | Input tokens | Total cost | Task accuracy | Critical-fact recall |
    | --- | --: | --: | --: | --: | --: |

Raw artifacts (``--output <dir>``) are written OUTSIDE the repository:
``model_eval_harness.json`` (per-exchange rows + table rows + deltas) and
``model_eval_harness.md``.  The scratch codec database lives at a
per-process-unique path ``~/.sage-bench/model_eval_harness-<pid>.db`` (the
pid suffix keeps concurrent harness processes on separate files) -- never
inside the output dir -- and is stable for the lifetime of the process (it is
never deleted while the module-level sqlalchemy engine may hold pooled
connections to it); it is removed at process exit.  The output dir contains
only the two artifacts.

Determinism: two runs produce byte-identical printed tables, ``.md``
artifacts and JSON artifacts except for the measured per-adapter-call
``latency_ms`` row values (real wall-clock measurements, deliberately
excluded from determinism comparisons); ``generated_at`` is pinned to the
benchmark's fixed timestamp.

Feedback loop (issue #16, stage 4 -- RFC "learned semantic shorthand"):
with ``--record-feedback`` (default OFF), after the exchanges the harness
records each selected SAGE variant's measured task success (the mean of the
adapter-reported ``task_success`` for that variant's rows) into the codec's
pattern store via ``PatternStore.record_feedback``, mirroring
``runtime.feedback`` semantics: ``task_success`` must be in ``[0, 1]``
(``ValueError``), an unknown ``packet_id`` raises ``KeyError``, and the
decisions come from the ``MessageAudit`` rows the real encodes created
(pinned packet ids per variant/turn, re-encoded deterministically into the
scratch database).  The feedback summary (patterns updated, ``task_utility``
and ``utility_score`` before/after per pattern) is ADDITIVE JSON -- a new
top-level ``feedback`` key in the artifact -- and never alters existing row
fields or the RFC table; wire bytes are byte-identical with or without the
flag (feedback is post-hoc DB bookkeeping, never touches encode).  Without
the flag the artifacts are byte-identical to the stage-3 shape.

``run_harness`` (the public API) refuses to run unless ``SAGE_DATABASE_URL``
is set to a writable scratch database path -- it never operates on the
ambient default database (``~/sage.db``); ``main()`` sets this up
automatically.  It also refuses when ``sage_plugin.db`` is already imported
with an engine bound to a different database than ``SAGE_DATABASE_URL`` (the
module-level engine cannot be rebound in this process).  ``--timeout`` must
be a positive finite number, an empty ``--variants`` value is an error, and
``family``/``version`` values are whitespace-stripped on load.

Run it (provider configured):

    SAGE_BENCH_LLM_PROVIDER=fake uv run --with '.[dev,mcp]' \\
        python scripts/model_eval_harness.py --adapters adapters.json \\
        --output /opt/data/sage/scratch/stage3-smoke
"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

PROVIDER_ENV = "SAGE_BENCH_LLM_PROVIDER"
NO_PROVIDER_NOTE = "not run, no provider"

#: Default codebook release label reported for receivers whose config does
#: not pin one (SAGE codebook releases are signed manifests addressed by
#: namespace/release label -- see ``sage_plugin.codebook_releases``).
DEFAULT_CODEBOOK_VERSION = "global:1"

DECODER_MODES = ("direct-symbolic", "decoder-assisted", "full-expansion")
DECODER_LABELS = {
    "direct-symbolic": "direct symbolic",
    "decoder-assisted": "decoder-assisted",
    "full-expansion": "full natural-language expansion",
}

#: RFC "Proposed public result format" -- exactly these columns/alignment.
RFC_TABLE_HEADER = "| Variant | Wire bytes | Input tokens | Total cost | Task accuracy | Critical-fact recall |"
RFC_TABLE_SEPARATOR = "| --- | --: | --: | --: | --: | --: |"

#: Stage-2 variants whose per-turn content is the state dict, not a message.
_STATE_VARIANTS = frozenset({"v05", "v06", "v11", "v12"})
_ALL_VARIANT_IDS = [f"v{index:02d}" for index in range(1, 13)]


def _scratch_db_path() -> Path:
    """Per-process-unique scratch database path (never deleted mid-process).

    The pid suffix keeps concurrent harness processes on separate files: a
    process's atexit cleanup only ever touches its own file, and per-variant
    schema resets can never race on a shared database.
    """
    return Path.home() / ".sage-bench" / f"model_eval_harness-{os.getpid()}.db"


def _cleanup_scratch_db() -> None:
    """Best-effort removal of the scratch database at process exit.

    The module-level engine is disposed first when it is bound to the scratch
    file, so the file is never unlinked while a pooled connection may still
    target it.  Only runs at interpreter exit; never mid-process.
    """
    path = _scratch_db_path()
    db_module = sys.modules.get("sage_plugin.db")
    if db_module is not None:
        try:
            url = db_module.engine.url
            if url.drivername == "sqlite" and url.database:
                try:
                    engine_path = Path(url.database)
                except TypeError:
                    engine_path = None
                if engine_path is not None and engine_path == path:
                    db_module.engine.dispose()
        except Exception:
            pass
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


atexit.register(_cleanup_scratch_db)


def _load_compression_benchmark() -> Any:
    """Load the stage-2 benchmark as a module (same pattern the tests use)."""
    spec = importlib.util.spec_from_file_location(
        "compression_benchmark", Path(__file__).resolve().parent / "compression_benchmark.py"
    )
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider_available() -> bool:
    """True when ``SAGE_BENCH_LLM_PROVIDER`` is a non-empty environment value."""
    return bool(os.environ.get(PROVIDER_ENV, "").strip())


def validate_adapters(adapters: dict[str, Any]) -> dict[str, Any]:
    """Validate the adapters config and enforce the >=2 families gate."""
    if not isinstance(adapters, dict) or not adapters:
        raise ValueError("adapter configuration must be a non-empty object")
    families: set[str] = set()
    for identity, spec in sorted(adapters.items()):
        if not isinstance(spec, dict):
            raise ValueError(f"adapter {identity}: spec must be an object")
        family = spec.get("family")
        version = spec.get("version")
        command = spec.get("command")
        if not isinstance(family, str) or not family.strip():
            raise ValueError(f"adapter {identity}: 'family' is required")
        if not isinstance(version, str) or not version.strip():
            raise ValueError(f"adapter {identity}: 'version' is required")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise ValueError(f"adapter {identity}: 'command' must be a non-empty list of strings")
        # Normalize: whitespace-padded family/version are accepted but always
        # reported stripped (rows, families gate, artifact).
        spec["family"] = family.strip()
        spec["version"] = version.strip()
        families.add(spec["family"])
    if len(families) < 2:
        raise ValueError(
            "adapter configuration must cover at least 2 distinct model families "
            f"(RFC stage 3); got {sorted(families)}"
        )
    return adapters


def load_adapters(path: str | Path) -> dict[str, Any]:
    """Load and validate an adapters JSON config file."""
    return validate_adapters(json.loads(Path(path).read_text()))


def _invoke(command: list[str], payload: dict[str, Any], timeout: float, identity: str) -> dict[str, Any]:
    """Invoke an adapter command (mirrors ``model_matrix_benchmark._invoke``)."""
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(payload, separators=(",", ":")),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"adapter {identity} timed out after {timeout}s") from exc
    except OSError as exc:
        raise RuntimeError(f"adapter {identity} could not start: {exc}") from exc
    latency_ms = (time.perf_counter() - started) * 1000
    if completed.returncode != 0:
        raise RuntimeError(
            f"adapter {identity} failed (exit {completed.returncode}): "
            f"{completed.stderr.strip() or 'benchmark adapter failed'}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"adapter {identity} returned non-JSON output: {completed.stdout[:200]!r}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"adapter {identity} returned a non-object result")
    result.setdefault("latency_ms", latency_ms)
    return result


def _sage_packet(spec: dict[str, Any], turn: int, content: Any, strategy_note: str) -> str:
    """Deterministic symbolic rendering of a SAGE variant's packet."""
    packet_id = "P" + hashlib.sha256(f"{spec['id']}:{turn}".encode()).hexdigest()[:32]
    if isinstance(content, dict):
        return json.dumps(
            {"packet": packet_id, "strategy_note": strategy_note, "state": content},
            sort_keys=True,
            separators=(",", ":"),
        )
    from sage_plugin.compiler import compile_content  # lazy: standalone binds the DB first

    canonicals = [unit.canonical for unit in compile_content(content)]
    return json.dumps(
        {"packet": packet_id, "strategy_note": strategy_note, "canonicals": canonicals},
        sort_keys=True,
        separators=(",", ":"),
    )


def _build_exchanges(cb: Any, benchmark: dict[str, Any], selected: list[str]) -> list[dict[str, Any]]:
    """Per-variant per-turn exchange records (representation, wire bytes, ...)."""
    plain = {spec["id"]: spec for spec in cb._plain_specs()}
    sage = {spec["id"]: spec for spec in cb._sage_specs()}
    by_id = {row["variant_id"]: row for row in benchmark["variants"]}
    exchanges: list[dict[str, Any]] = []
    for variant_id in selected:
        variant_row = by_id[variant_id]
        if variant_row["status"] != "ok":
            continue
        spec = sage.get(variant_id) or plain.get(variant_id)
        if spec is None:
            continue
        is_sage = variant_id in sage
        for turn_record in variant_row["turns"]:
            if turn_record["turn"] < 0:  # pattern warm-up exchange (variant 10)
                continue
            turn = turn_record["turn"]
            if is_sage:
                content = spec["content_fn"](turn)
                representation = _sage_packet(spec, turn, content, turn_record.get("note", ""))
            else:
                if variant_id in _STATE_VARIANTS:
                    content = cb.STATE_DICTS[turn]
                else:
                    content = cb.SHARED_CONTEXT if turn == 0 else cb.UPDATES[turn - 1]
                representation = turn_record["reconstruction"]
            exchanges.append(
                {
                    "variant": variant_id,
                    "variant_name": variant_row["name"],
                    "turn": turn,
                    "phase": turn_record["phase"],
                    "content": content,
                    "representation": representation,
                    "wire_bytes": turn_record["wire_bytes_json"],
                    "reconstruction": turn_record["reconstruction"],
                    "expected": cb.ground_truth_answers(turn),
                    "change_markers": cb.CHANGE_MARKERS.get(turn, []),
                    "sage": is_sage,
                }
            )
    return exchanges


def _build_payload(
    cb: Any,
    exchange: dict[str, Any],
    receiver_state: str,
    decoder_mode: str,
    symbolic_examples: bool,
) -> dict[str, Any]:
    """The per-exchange JSON payload sent to the adapter."""
    if exchange["sage"] and decoder_mode == "direct-symbolic":
        model_facing = exchange["representation"]
    else:
        model_facing = exchange["reconstruction"]
    prior: dict[str, Any] | None = None
    if receiver_state == "warm":
        prior = {
            "shared_context": cb.SHARED_CONTEXT,
            "codebook_acked": True,
            "patterns_acked": True,
            "note": "receiver prior established in the shared-context phase (codebook/patterns ACKed)",
        }
    payload: dict[str, Any] = {
        "protocol": "sage/0.2",
        "benchmark": "compression_benchmark:phoenix_rfc",
        "variant": exchange["variant"],
        "variant_name": exchange["variant_name"],
        "turn": exchange["turn"],
        "phase": exchange["phase"],
        "receiver_state": receiver_state,
        "receiver_prior": prior,
        "decoder_configuration": DECODER_LABELS[decoder_mode],
        "symbolic_examples": bool(symbolic_examples),
        "representation": exchange["representation"],
        "wire_bytes": exchange["wire_bytes"],
        "model_facing_text": model_facing,
        "content": exchange["content"],
        "expected": exchange["expected"],
        "change_markers": exchange["change_markers"],
    }
    if symbolic_examples:
        payload["examples"] = [{"packet": exchange["representation"], "meaning": exchange["reconstruction"]}]
    return payload


def _critical_fact_recall(
    cb: Any, result: dict[str, Any], exchange: dict[str, Any], identity: str
) -> float:
    """Adapter-reported recall, else the harness's deterministic score of the
    adapter's reconstruction text (RFC fidelity checker), else 0.0."""
    reported = result.get("critical_fact_recall")
    if reported is not None:
        if isinstance(reported, bool) or not isinstance(reported, (int, float)):
            raise RuntimeError(
                f"adapter {identity}: critical_fact_recall must be a finite number, got {reported!r}"
            )
        try:
            value = float(reported)
        except (TypeError, ValueError, OverflowError) as exc:
            raise RuntimeError(
                f"adapter {identity}: critical_fact_recall must be a finite number, got {reported!r}"
            ) from exc
        if not math.isfinite(value):
            raise RuntimeError(
                f"adapter {identity}: critical_fact_recall must be finite, got {reported!r}"
            )
        return min(1.0, max(0.0, value))
    reconstruction = result.get("reconstruction")
    if isinstance(reconstruction, str) and reconstruction.strip():
        return float(cb.fidelity_critical(reconstruction))
    return 0.0


def _finite_float(
    raw: Any,
    identity: str,
    key: str,
    *,
    minimum: float = -math.inf,
    maximum: float | None = None,
) -> float:
    """Coerce to a finite float within [minimum, maximum]; adapter-naming
    RuntimeError on any violation (never silently promotes garbage)."""
    if isinstance(raw, bool):
        raise RuntimeError(f"adapter {identity}: {key} must be a finite number, got {raw!r}")
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError(f"adapter {identity}: {key} must be a finite number, got {raw!r}") from exc
    if not math.isfinite(value):
        raise RuntimeError(f"adapter {identity}: {key} must be finite, got {raw!r}")
    if value < minimum:
        raise RuntimeError(f"adapter {identity}: {key} must be >= {minimum}, got {raw!r}")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"adapter {identity}: {key} must be <= {maximum}, got {raw!r}")
    return value


def _non_negative_int(raw: Any, identity: str, key: str) -> int:
    """Require an integral, non-negative value; strings, bools, fractional
    floats and non-finite numbers are rejected."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise RuntimeError(f"adapter {identity}: {key} must be a non-negative integer, got {raw!r}")
    if isinstance(raw, float) and not raw.is_integer():
        raise RuntimeError(f"adapter {identity}: {key} must be a non-negative integer, got {raw!r}")
    value = int(raw)
    if value < 0:
        raise RuntimeError(f"adapter {identity}: {key} must be a non-negative integer, got {raw!r}")
    return value


def _row_from_result(
    cb: Any,
    identity: str,
    spec: dict[str, Any],
    exchange: dict[str, Any],
    result: dict[str, Any],
    *,
    receiver_state: str,
    decoder_mode: str,
    symbolic_examples: bool,
    payload: dict[str, Any],
) -> dict[str, Any]:
    success = result.get("task_success")
    if success is None:
        raise RuntimeError(f"adapter {identity} did not report task_success")
    provider_cost = _finite_float(
        result.get("provider_cost_usd", 0.0), identity, "provider_cost_usd", minimum=0.0
    )
    infrastructure_cost = _finite_float(
        result.get("infrastructure_cost_usd", 0.0), identity, "infrastructure_cost_usd", minimum=0.0
    )
    retrieval_cost = _finite_float(
        result.get("retrieval_cost_usd", 0.0), identity, "retrieval_cost_usd", minimum=0.0
    )
    retry_cost = _finite_float(
        result.get("retry_cost_usd", 0.0), identity, "retry_cost_usd", minimum=0.0
    )
    if "cost_usd" in result:
        total_cost = _finite_float(result["cost_usd"], identity, "cost_usd", minimum=0.0)
    else:
        total_cost = provider_cost + infrastructure_cost + retrieval_cost + retry_cost
    if not math.isfinite(total_cost):
        raise RuntimeError(f"adapter {identity}: cost_usd must be finite, got {total_cost!r}")
    adapter_tokens = _non_negative_int(result.get("input_tokens", 0), identity, "input_tokens")
    expansion_tokens = cb._estimate_tokens(payload["model_facing_text"]) if decoder_mode == "decoder-assisted" else 0
    return {
        "variant": exchange["variant"],
        "variant_name": exchange["variant_name"],
        "turn": exchange["turn"],
        "phase": exchange["phase"],
        "receiver_model": identity,
        "model_family": spec["family"],
        "model_version": spec["version"],
        "codebook_version": spec.get("codebook_version", DEFAULT_CODEBOOK_VERSION),
        "decoder_configuration": DECODER_LABELS[decoder_mode],
        "symbolic_examples": bool(symbolic_examples),
        "receiver_state": receiver_state,
        "receiver_prior": payload["receiver_prior"],
        "wire_bytes": exchange["wire_bytes"],
        "adapter_input_tokens": adapter_tokens,
        "expansion_tokens": expansion_tokens,
        "input_tokens": adapter_tokens + expansion_tokens,
        "output_tokens": _non_negative_int(result.get("output_tokens", 0), identity, "output_tokens"),
        "provider_cost_usd": provider_cost,
        "infrastructure_cost_usd": infrastructure_cost,
        "retrieval_cost_usd": retrieval_cost,
        "retry_cost_usd": retry_cost,
        "cost_usd": total_cost,
        "retrievals": _non_negative_int(result.get("retrievals", 0), identity, "retrievals"),
        "tool_calls": _non_negative_int(result.get("tool_calls", 0), identity, "tool_calls"),
        "retries": _non_negative_int(result.get("retries", 0), identity, "retries"),
        "semantic_loss": _finite_float(result.get("semantic_loss", 0.0), identity, "semantic_loss"),
        "task_success": _finite_float(success, identity, "task_success", minimum=0.0, maximum=1.0),
        "critical_fact_recall": _critical_fact_recall(cb, result, exchange, identity),
        "latency_ms": _finite_float(result.get("latency_ms", 0.0), identity, "latency_ms", minimum=0.0),
    }


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One RFC-table row per (variant, receiver, cold/warm) combination."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["variant"], row["receiver_model"], row["receiver_state"])].append(row)
    table_rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        items = sorted(grouped[key], key=lambda item: item["turn"])
        first = items[0]
        table_rows.append(
            {
                "variant_cell": (
                    f"{first['variant']} {first['variant_name']} [{first['receiver_model']}] {first['receiver_state']}"
                ),
                "variant": first["variant"],
                "variant_name": first["variant_name"],
                "receiver_model": first["receiver_model"],
                "model_family": first["model_family"],
                "model_version": first["model_version"],
                "codebook_version": first["codebook_version"],
                "decoder_configuration": first["decoder_configuration"],
                "symbolic_examples": first["symbolic_examples"],
                "receiver_state": first["receiver_state"],
                "wire_bytes": sum(item["wire_bytes"] for item in items),
                "input_tokens": sum(item["input_tokens"] for item in items),
                "output_tokens": sum(item["output_tokens"] for item in items),
                "cost_usd": round(sum(item["cost_usd"] for item in items), 6),
                "task_accuracy": round(statistics.mean(item["task_success"] for item in items), 6),
                "critical_fact_recall": items[-1]["critical_fact_recall"],
            }
        )
    return table_rows


def _warm_vs_cold_deltas(table_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Warm-minus-cold deltas per (variant, receiver) pair."""
    by_pair: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in table_rows:
        by_pair[(row["variant"], row["receiver_model"])][row["receiver_state"]] = row
    deltas: list[dict[str, Any]] = []
    for (variant_id, receiver) in sorted(by_pair):
        pair = by_pair[(variant_id, receiver)]
        if "cold" not in pair or "warm" not in pair:
            continue
        cold, warm = pair["cold"], pair["warm"]
        deltas.append(
            {
                "variant": variant_id,
                "variant_name": cold["variant_name"],
                "receiver_model": receiver,
                "wire_bytes_delta": warm["wire_bytes"] - cold["wire_bytes"],
                "input_tokens_delta": warm["input_tokens"] - cold["input_tokens"],
                "cost_usd_delta": round(warm["cost_usd"] - cold["cost_usd"], 6),
                "task_accuracy_delta": round(warm["task_accuracy"] - cold["task_accuracy"], 6),
                "critical_fact_recall_delta": round(
                    warm["critical_fact_recall"] - cold["critical_fact_recall"], 6
                ),
            }
        )
    return deltas


def _format_markdown_table(table_rows: list[dict[str, Any]]) -> str:
    """The RFC's public six-column markdown result table."""
    lines = [RFC_TABLE_HEADER, RFC_TABLE_SEPARATOR]
    for row in table_rows:
        lines.append(
            f"| {row['variant_cell']} | {row['wire_bytes']} | {row['input_tokens']} | "
            f"${row['cost_usd']:.4f} | {round(row['task_accuracy'] * 100)}% | "
            f"{round(row['critical_fact_recall'] * 100)}% |"
        )
    return "\n".join(lines)


def _format_delta_table(deltas: list[dict[str, Any]]) -> str:
    header = "| Variant | Receiver | Wire bytes d | Input tokens d | Cost d | Task accuracy d | Critical recall d |"
    separator = "| --- | --- | --: | --: | --: | --: | --: |"
    lines = [header, separator]
    for delta in deltas:
        lines.append(
            f"| {delta['variant']} {delta['variant_name']} | {delta['receiver_model']} | "
            f"{delta['wire_bytes_delta']:+d} | {delta['input_tokens_delta']:+d} | "
            f"${delta['cost_usd_delta']:+.4f} | {round(delta['task_accuracy_delta'] * 100):+d}% | "
            f"{round(delta['critical_fact_recall_delta'] * 100):+d}% |"
        )
    return "\n".join(lines)


def _urls_point_at_same_database(engine_url: Any, env_url: str) -> bool:
    """True when the two database URLs target the same database.

    SQLite file paths are resolved so equivalent spellings (absolute vs
    relative, symlinked) compare equal; non-sqlite URLs compare by their
    normalized rendering.
    """
    try:
        from sqlalchemy.engine import make_url

        engine_parsed = make_url(str(engine_url))
        env_parsed = make_url(env_url)
    except Exception:
        return str(engine_url) == env_url
    if engine_parsed.drivername != env_parsed.drivername:
        return False
    if engine_parsed.drivername == "sqlite":
        engine_db, env_db = engine_parsed.database, env_parsed.database
        if engine_db is None or env_db is None:
            return engine_db == env_db
        if engine_db == ":memory:" or env_db == ":memory:":
            return engine_db == env_db
        try:
            return Path(engine_db).resolve() == Path(env_db).resolve()
        except OSError:
            return engine_db == env_db
    return str(engine_parsed) == str(env_parsed)


def _prebound_sage_plugin_conflict() -> str | None:
    """Describe a ``sage_plugin.db`` engine that cannot be rebound, else None.

    ``sage_plugin.db`` creates its module-level engine at import time; if it
    is already imported and bound to a database other than the one
    ``SAGE_DATABASE_URL`` names, resetting the schema would hit the pre-bound
    database (data loss), so the harness must refuse instead.
    """
    db_module = sys.modules.get("sage_plugin.db")
    if db_module is None:
        return None
    engine = getattr(db_module, "engine", None)
    if engine is None:
        return None
    engine_url = getattr(engine, "url", None)
    if engine_url is None:
        return None
    env_url = os.environ.get("SAGE_DATABASE_URL", "").strip()
    if _urls_point_at_same_database(engine_url, env_url):
        return None
    return (
        "sage_plugin.db is already imported and its engine is bound to "
        f"{engine_url!r}, which differs from SAGE_DATABASE_URL ({env_url!r}); "
        "the module-level engine cannot be rebound in this process, so the "
        "harness refuses to run (a schema reset would otherwise hit the "
        "pre-bound database). Run in a fresh process or set SAGE_DATABASE_URL "
        "before the first sage_plugin import."
    )


def _record_feedback_for_packets(
    db: Any,
    settings: Any,
    packets: list[tuple[int, str]],
    task_success: float,
) -> dict[str, Any]:
    """Record measured task success against pinned audit rows (issue #16,
    stage 4 -- the RFC "learned semantic shorthand" feedback loop).

    Mirrors ``runtime.feedback`` semantics exactly: ``task_success`` must be
    in ``[0, 1]`` (``ValueError`` otherwise, validated BEFORE any lookup),
    an unknown ``packet_id`` raises ``KeyError``, and the decisions consumed
    by ``PatternStore.record_feedback`` come from the ``MessageAudit`` row
    the real encode created.  Returns a per-packet + merged per-pattern
    before/after summary (status, ``task_utility``, ``utility_score``) --
    additive JSON only, never a change to any existing field.

    ``packets`` is a list of ``(turn, packet_id)`` pairs for one SAGE variant.

    NOTE (cumulative semantics): each packet's ``patterns_updated`` field is
    CUMULATIVE -- ``len(merged)`` across all packets processed so far for
    this variant (``merged`` accumulates outside the packet loop), NOT a
    per-packet count.  The variant-level ``patterns_updated`` list in the
    returned summary is the authoritative merged per-pattern before/after
    view.
    """
    if not 0.0 <= task_success <= 1.0:
        raise ValueError("task_success must be in [0, 1]")
    from sqlalchemy import select

    from sage_plugin.db_models import MessageAudit
    from sage_plugin.patterns import PatternStore

    store = PatternStore(db, settings)
    packets_summary: list[dict[str, Any]] = []
    merged: dict[str, dict[str, Any]] = {}
    for turn, packet_id in packets:
        audit = db.scalar(select(MessageAudit).where(MessageAudit.packet_id == packet_id))
        if audit is None:
            raise KeyError(packet_id)
        touched_ids = sorted(
            {decision.get("pattern_id") for decision in audit.decisions if isinstance(decision.get("pattern_id"), str)}
        )
        before: dict[str, dict[str, Any]] = {}
        for pattern_id in touched_ids:
            pattern = store.get(pattern_id)
            if pattern is not None:
                before[pattern_id] = {
                    "status": pattern.status,
                    "task_utility": pattern.task_utility,
                    "utility_score": store.utility_score(pattern),
                }
        updated = store.record_feedback(audit.decisions, task_success)
        after: dict[str, dict[str, Any]] = {}
        for pattern in updated:
            after[pattern.pattern_id] = {
                "status": pattern.status,
                "task_utility": pattern.task_utility,
                "utility_score": store.utility_score(pattern),
            }
        for pattern_id in sorted(set(before) | set(after)):
            merged[pattern_id] = {
                "pattern_id": pattern_id,
                "status_before": before.get(pattern_id, {}).get("status"),
                "status_after": after.get(pattern_id, {}).get("status"),
                "task_utility_before": before.get(pattern_id, {}).get("task_utility"),
                "task_utility_after": after.get(pattern_id, {}).get("task_utility"),
                "utility_score_before": before.get(pattern_id, {}).get("utility_score"),
                "utility_score_after": after.get(pattern_id, {}).get("utility_score"),
            }
        packets_summary.append(
            {
                "packet_id": packet_id,
                "turn": turn,
                "decisions": len(audit.decisions),
                "patterns_updated": len(merged),
            }
        )
    return {
        "task_success": task_success,
        "packets": packets_summary,
        "patterns_updated": [merged[pattern_id] for pattern_id in sorted(merged)],
    }


def _record_benchmark_feedback(cb: Any, selected: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Record each selected SAGE variant's measured task success into the
    codec's pattern store (issue #16, stage 4).

    For every selected SAGE variant (v09-v12) the variant's six exchanges
    are re-encoded into the scratch database through the REAL codec with the
    benchmark's pinned packet ids (deterministic, exactly like the
    benchmark's own ``_run_sage_variant``), so the ``MessageAudit`` rows the
    real encodes created exist; each packet's decisions are then recorded
    with the variant's measured task success -- the mean of the
    adapter-reported ``task_success`` values for that variant's rows -- via
    ``_record_feedback_for_packets`` (``runtime.feedback`` semantics).

    This is post-hoc DB bookkeeping: the wire bytes reported in the artifact
    come from the benchmark's recorded turn data, never from this re-encode,
    so the SAGE variants' wire bytes are byte-identical with or without the
    flag.  The returned summary is additive JSON (a top-level ``feedback``
    key) and never alters existing row fields or the RFC table.
    """
    from sage_plugin import db as db_module
    from sage_plugin.config import Settings
    from sage_plugin.db import SessionLocal

    db_module.init_db()
    sage_specs = {spec["id"]: spec for spec in cb._sage_specs()}
    rows_by_variant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        rows_by_variant[row["variant"]].append(row)
    variants: list[dict[str, Any]] = []
    for variant_id in sorted(set(selected) & set(sage_specs)):
        variant_rows = rows_by_variant.get(variant_id)
        if not variant_rows:
            continue
        task_success = statistics.mean(row["task_success"] for row in variant_rows)
        spec = sage_specs[variant_id]
        settings = Settings(
            auth_required=False,
            database_url=os.environ.get("SAGE_DATABASE_URL", "sqlite://"),
            context_accounting_enabled=True,
            learning_mode="managed",
            **spec.get("settings", {}),
        )
        # Real encodes -> MessageAudit rows for this variant (schema reset per
        # variant, exactly like the benchmark's own run loop).
        cb._run_sage_variant(spec)
        packets = [
            (turn, "P" + hashlib.sha256(f"{variant_id}:{turn}".encode()).hexdigest()[:32])
            for turn in range(6)
        ]
        with SessionLocal() as db:
            summary = _record_feedback_for_packets(db, settings, packets, task_success)
            db.commit()
        summary["variant"] = variant_id
        summary["variant_name"] = spec["name"]
        variants.append(summary)
    return {
        "recorded": True,
        "note": (
            "measured downstream task success recorded into the codec's pattern store via "
            "PatternStore.record_feedback (runtime.feedback semantics); post-hoc DB bookkeeping "
            "-- zero wire-byte change"
        ),
        "variants": variants,
    }


def run_harness(
    adapters: dict[str, Any],
    *,
    decoder_mode: str = "direct-symbolic",
    symbolic_examples: bool = False,
    variants: list[str] | None = None,
    timeout: float = 120.0,
    record_feedback: bool = False,
) -> dict[str, Any]:
    """Run the model evaluation harness end-to-end and return the full results.

    Requires ``SAGE_DATABASE_URL`` to be set to a writable scratch database
    path (the harness refuses to run against the ambient default ``~/sage.db``;
    the CLI ``main()`` sets it up automatically).  If ``sage_plugin.db`` is
    already imported with an engine bound to a different database than
    ``SAGE_DATABASE_URL``, refuses with ``RuntimeError`` (the module-level
    engine cannot be rebound in this process).

    Raises ``ValueError`` for invalid configuration (including configs with
    fewer than 2 distinct model families) and ``RuntimeError`` for adapter
    failures or a missing ``SAGE_DATABASE_URL`` -- results are never
    fabricated.
    """
    if not os.environ.get("SAGE_DATABASE_URL", "").strip():
        raise RuntimeError(
            "SAGE_DATABASE_URL is not set; set it to a writable scratch database "
            "path (e.g. sqlite:///<scratch>/sage_bench.db) before running the "
            "harness -- refusing to touch the ambient default database (~/sage.db)"
        )
    conflict = _prebound_sage_plugin_conflict()
    if conflict is not None:
        raise RuntimeError(conflict)
    validate_adapters(adapters)
    if decoder_mode not in DECODER_MODES:
        raise ValueError(f"decoder_mode must be one of {DECODER_MODES}")
    cb = _load_compression_benchmark()
    benchmark = cb.run_benchmark(out_dir=None)
    selected = variants if variants is not None else list(_ALL_VARIANT_IDS)
    known = {row["variant_id"] for row in benchmark["variants"]}
    for variant_id in selected:
        if variant_id not in known:
            raise ValueError(f"unknown variant id {variant_id!r}; expected one of {sorted(known)}")
    exchanges = _build_exchanges(cb, benchmark, selected)

    rows: list[dict[str, Any]] = []
    for identity, spec in sorted(adapters.items()):
        for receiver_state in ("cold", "warm"):
            for exchange in exchanges:
                payload = _build_payload(cb, exchange, receiver_state, decoder_mode, symbolic_examples)
                result = _invoke(spec["command"], payload, timeout, identity)
                rows.append(
                    _row_from_result(
                        cb,
                        identity,
                        spec,
                        exchange,
                        result,
                        receiver_state=receiver_state,
                        decoder_mode=decoder_mode,
                        symbolic_examples=symbolic_examples,
                        payload=payload,
                    )
                )
    table_rows = _aggregate_rows(rows)
    deltas = _warm_vs_cold_deltas(table_rows)
    markdown = _format_markdown_table(table_rows)
    markdown_full = markdown + ("\n\n" + _format_delta_table(deltas) if deltas else "")
    feedback = _record_benchmark_feedback(cb, selected, rows) if record_feedback else None
    results = {
        "schema": "sage.model_eval_harness.v1",
        "generated_at": cb.FIXED_TIMESTAMP,
        "scenario": benchmark["scenario"],
        "provider": {"configured": True, "env": PROVIDER_ENV},
        "decoder_mode": decoder_mode,
        "decoder_configuration": DECODER_LABELS[decoder_mode],
        "symbolic_examples": bool(symbolic_examples),
        "adapters": {
            identity: {
                key: spec[key] for key in ("family", "version", "codebook_version") if key in spec
            }
            for identity, spec in sorted(adapters.items())
        },
        "rows": rows,
        "table_rows": table_rows,
        "deltas": deltas,
        "markdown_table": markdown,
        "markdown": markdown_full,
    }
    if feedback is not None:
        results["feedback"] = feedback
    return results


def _write_artifacts(out_dir: str | Path, results: dict[str, Any]) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Advisory only (no locking -- this is an opt-in benchmark tool): a
    # pre-existing artifact means a previous run -- possibly a CONCURRENT run
    # pointed at the same --output dir -- is about to be silently overwritten.
    if (out / "model_eval_harness.json").exists():
        print(
            "model evaluation harness: warning: overwriting existing artifacts "
            f"in {out} (concurrent runs with the same --output dir silently lose "
            "one run's results)",
            file=sys.stderr,
        )
    try:
        payload = (
            json.dumps(results, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        )
    except ValueError as exc:
        raise RuntimeError(
            "adapter results contain non-finite numbers; refusing to write invalid RFC 8259 JSON"
        ) from exc
    (out / "model_eval_harness.json").write_text(payload)
    (out / "model_eval_harness.md").write_text(results["markdown"] + "\n")


def _positive_timeout(value: str) -> float:
    """argparse type: ``--timeout`` must be a positive, finite number of
    seconds (``nan``/``inf`` are rejected -- ``nan <= 0`` is False, so a bare
    ``<= 0`` check would let them through)."""
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError(f"--timeout must be a positive finite number, got {value!r}")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Opt-in model evaluation harness (issue #16, stage 3): run the compression "
            "benchmark's receivers on >=2 model families via external-runtime adapters, "
            "cold vs warm, RFC public result table."
        )
    )
    parser.add_argument(
        "--adapters",
        type=Path,
        default=None,
        help="path to an adapters JSON config (model_identity -> family/version/command)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="directory for model_eval_harness.json/.md raw artifacts (outside the repo)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_timeout,
        default=120.0,
        help="per-adapter-call timeout in seconds (must be > 0)",
    )
    parser.add_argument(
        "--decoder-mode",
        choices=DECODER_MODES,
        default="direct-symbolic",
        help="how the packet reaches the receiving model (RFC model-facing evaluation modes)",
    )
    parser.add_argument(
        "--with-examples",
        action="store_true",
        help="give the receivers a symbolic-format example packet + meaning (symbolic_examples=true)",
    )
    parser.add_argument(
        "--variants",
        default=None,
        help="comma-separated variant ids to evaluate (default: all twelve; an empty value is an error)",
    )
    parser.add_argument(
        "--record-feedback",
        action="store_true",
        help=(
            "record each SAGE variant's measured task success into the codec's pattern store "
            "via PatternStore.record_feedback (runtime.feedback semantics; additive 'feedback' "
            "JSON summary key, zero wire-byte change).  Default OFF: artifacts are byte-identical "
            "to a run without the flag."
        ),
    )
    args = parser.parse_args(argv)

    if args.adapters is None or not provider_available():
        print(f"model evaluation harness: {NO_PROVIDER_NOTE}")
        return 0

    # Reject an --output path that exists as a FILE before anything runs (no
    # traceback, no wasted adapter calls).  The directory itself is only
    # created AFTER run_harness has succeeded, immediately before the
    # artifacts are written (see below), so NO validation or error path --
    # missing adapters, empty --variants, unknown variant id, adapter
    # failure -- leaves an empty output dir behind.
    output_dir: Path | None = None
    if args.output is not None:
        out: Path = args.output
        if out.exists() and not out.is_dir():
            print(
                "model evaluation harness: error: --output path exists and is not a directory",
                file=sys.stderr,
            )
            return 2
        output_dir = out

    try:
        adapters = load_adapters(args.adapters)
    except FileNotFoundError:
        print(
            f"model evaluation harness: error: no such adapters file: {args.adapters}",
            file=sys.stderr,
        )
        return 2
    except (ValueError, OSError) as exc:
        print(f"model evaluation harness: error: {exc}", file=sys.stderr)
        return 2

    variants: list[str] | None = None
    if args.variants is not None:
        segments = [item.strip() for item in args.variants.split(",")]
        if not any(segments):
            print(
                "model evaluation harness: error: --variants must name at least one variant id",
                file=sys.stderr,
            )
            return 2
        variants = [item for item in segments if item]

    # Bind a STABLE per-process scratch database BEFORE any sage_plugin import
    # (db.py creates the engine at import time).  The file lives in
    # ~/.sage-bench -- never in the --output dir -- and is never deleted
    # mid-process (the module-level engine may hold pooled connections to it);
    # it is removed at process exit via _cleanup_scratch_db.
    scratch_db = _scratch_db_path()
    scratch_db.parent.mkdir(parents=True, exist_ok=True)
    prior_db_url = os.environ.get("SAGE_DATABASE_URL")
    os.environ["SAGE_DATABASE_URL"] = f"sqlite:///{scratch_db}"
    try:
        results = run_harness(
            adapters,
            decoder_mode=args.decoder_mode,
            symbolic_examples=args.with_examples,
            variants=variants,
            timeout=args.timeout,
            record_feedback=args.record_feedback,
        )
    except ValueError as exc:
        print(f"model evaluation harness: error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"model evaluation harness: error: {exc}", file=sys.stderr)
        return 1
    finally:
        if prior_db_url is None:
            os.environ.pop("SAGE_DATABASE_URL", None)
        else:
            os.environ["SAGE_DATABASE_URL"] = prior_db_url

    print(
        f"Model evaluation harness (issue #16, stage 3) -- decoder mode: {args.decoder_mode}, "
        f"symbolic examples: {args.with_examples}"
    )
    print(results["markdown_table"])
    if results["deltas"]:
        print()
        print(_format_delta_table(results["deltas"]))
    if output_dir is not None:
        # Create the output dir only now: run_harness has fully succeeded
        # (adapters loaded, --variants validated, every variant id known,
        # adapters ran without error), and this dir is only ever used by
        # _write_artifacts -- so every validation/error path above exits
        # without leaving an empty directory behind.
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            _write_artifacts(output_dir, results)
        except RuntimeError as exc:
            print(f"model evaluation harness: error: {exc}", file=sys.stderr)
            return 1
        print(f"\nArtifacts written to {output_dir}")
    if args.record_feedback:
        feedback = results.get("feedback")
        if feedback is not None:
            variants_note = ", ".join(
                f"{item['variant']} (patterns updated: {len(item['patterns_updated'])})"
                for item in feedback["variants"]
            )
            print(f"Feedback recorded (--record-feedback): {variants_note or 'no SAGE variants selected'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
