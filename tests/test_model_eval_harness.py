"""Regression tests for the opt-in model evaluation harness (issue #16, stage 3).

Covers (issue #16, stage 3):

* clean no-provider skip -- no ``--adapters`` flag or unset
  ``SAGE_BENCH_LLM_PROVIDER`` -> "not run, no provider", exit code 0,
  nothing fabricated;
* the >=2 model families gate -- configs covering fewer than 2 distinct
  ``family`` values are rejected with a clear error;
* a fake adapter (a tiny ``python -c`` command that echoes a JSON result from
  stdin) proves the end-to-end run produces rows with the RFC's per-model
  fields (receiver model, model version, codebook version, decoder
  configuration, symbolic-example flag), cold AND warm rows, and a markdown
  table matching the RFC's six-column public format;
* decoder-assisted mode counts expansion tokens in ``input_tokens``
  (RFC "Prevent hidden decompression costs");
* adapter failures (non-zero exit / missing ``task_success``) raise a clear
  error -- never silent fabrication.

All tests are deterministic (fixed inputs, no network, no real model) and
write their output directories under ``/opt/data/sage/scratch/`` -- never
``/tmp``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_SCRIPT = ROOT / "scripts" / "model_eval_harness.py"
SCRATCH_ROOT = Path(os.environ.get("SAGE_SCRATCH_ROOT", "/opt/data/sage/scratch")) / "stage3-tests"

#: A deterministic fake adapter: reads the JSON payload from stdin, echoes a
#: fixed result.  Warm receivers succeed at 1.0, cold receivers at 0.5, so the
#: cold/warm split is observable in the rows.
FAKE_ADAPTER_OK = (
    "import json,sys; p=json.load(sys.stdin); "
    "print(json.dumps({'task_success': 1.0 if p.get('receiver_state') == 'warm' else 0.5, "
    "'input_tokens': 7, 'output_tokens': 5, 'provider_cost_usd': 0.0012, 'critical_fact_recall': 0.8}))"
)
FAKE_ADAPTER_EXIT_3 = "import sys; sys.exit(3)"
FAKE_ADAPTER_NO_SUCCESS = (
    "import json,sys; p=json.load(sys.stdin); "
    "print(json.dumps({'input_tokens': 1, 'output_tokens': 1, 'provider_cost_usd': 0.0}))"
)


def _load_harness() -> Any:
    spec = importlib.util.spec_from_file_location("model_eval_harness", HARNESS_SCRIPT)
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def h() -> Any:
    return _load_harness()


@pytest.fixture()
def scratch_dir() -> Iterator[Path]:
    """A scratch output directory under /opt/data/sage/scratch (never /tmp)."""
    path = SCRATCH_ROOT / uuid.uuid4().hex[:12]
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _adapters_config() -> dict[str, Any]:
    return {
        "acme-gpt-4o": {
            "family": "acme",
            "version": "gpt-4o-2026-05",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
        "nebula-sonnet": {
            "family": "nebula",
            "version": "sonnet-2026-07",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
    }


def _one_family_config() -> dict[str, Any]:
    """Two adapters of the SAME family -- must be rejected by the gate."""
    return {
        "acme-gpt-4o": {
            "family": "acme",
            "version": "gpt-4o-2026-05",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
        "acme-gpt-4o-mini": {
            "family": "acme",
            "version": "gpt-4o-mini",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
    }


# ---------------------------------------------------------------------------
# No-provider skip
# ---------------------------------------------------------------------------


def test_no_provider_skip_is_clean(h, monkeypatch, capsys, scratch_dir):
    monkeypatch.delenv("SAGE_BENCH_LLM_PROVIDER", raising=False)
    assert h.provider_available() is False
    assert h.main([]) == 0
    assert "not run, no provider" in capsys.readouterr().out
    # an adapters config alone is not enough: the provider env gate still skips
    cfg = scratch_dir / "adapters.json"
    cfg.write_text(json.dumps(_adapters_config()))
    out_dir = scratch_dir / "out"
    assert h.main(["--adapters", str(cfg), "--output", str(out_dir)]) == 0
    assert "not run, no provider" in capsys.readouterr().out
    assert not out_dir.exists()  # nothing was fabricated or written


# ---------------------------------------------------------------------------
# >=2 model families gate
# ---------------------------------------------------------------------------


def test_less_than_two_families_rejected(h):
    with pytest.raises(ValueError, match="at least 2 distinct model families"):
        h.validate_adapters(_one_family_config())
    # two adapters of DIFFERENT families pass the gate
    h.validate_adapters(_adapters_config())
    # structural validation is still enforced
    with pytest.raises(ValueError, match="command"):
        h.validate_adapters({"x": {"family": "acme", "version": "1", "command": "not-a-list"}})


def test_less_than_two_families_cli_error(h, monkeypatch, scratch_dir, capsys):
    monkeypatch.setenv("SAGE_BENCH_LLM_PROVIDER", "fake")
    cfg = scratch_dir / "adapters.json"
    cfg.write_text(json.dumps(_one_family_config()))
    assert h.main(["--adapters", str(cfg)]) == 2
    assert "at least 2 distinct model families" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Fake-adapter end-to-end
# ---------------------------------------------------------------------------


def test_fake_adapter_end_to_end(h, monkeypatch, scratch_dir):
    monkeypatch.setenv("SAGE_BENCH_LLM_PROVIDER", "fake")
    cfg = scratch_dir / "adapters.json"
    cfg.write_text(json.dumps(_adapters_config()))
    out_dir = scratch_dir / "out"
    assert (
        h.main(
            [
                "--adapters",
                str(cfg),
                "--output",
                str(out_dir),
                "--variants",
                "v01,v12",
                "--with-examples",
            ]
        )
        == 0
    )
    artifact = json.loads((out_dir / "model_eval_harness.json").read_text())
    markdown = (out_dir / "model_eval_harness.md").read_text()
    rows = artifact["rows"]
    assert rows

    # RFC "Receiver compatibility" per-model fields on every row
    required_fields = {
        "receiver_model",
        "model_version",
        "codebook_version",
        "decoder_configuration",
        "symbolic_examples",
        "receiver_state",
    }
    for row in rows:
        assert required_fields <= row.keys()

    # cold AND warm rows for every (variant, receiver) combination
    pairs = {(row["variant"], row["receiver_model"]) for row in rows}
    assert pairs == {("v01", "acme-gpt-4o"), ("v01", "nebula-sonnet"), ("v12", "acme-gpt-4o"), ("v12", "nebula-sonnet")}
    for variant, receiver in pairs:
        states = {
            row["receiver_state"] for row in rows if row["variant"] == variant and row["receiver_model"] == receiver
        }
        assert states == {"cold", "warm"}

    # the fake adapter's cold/warm split flows through: warm succeeds, cold 0.5
    assert {row["task_success"] for row in rows if row["receiver_state"] == "warm"} == {1.0}
    assert {row["task_success"] for row in rows if row["receiver_state"] == "cold"} == {0.5}

    # per-model fields carry the config values
    config = _adapters_config()
    row = rows[0]
    assert row["receiver_model"] in config
    assert row["model_family"] == config[row["receiver_model"]]["family"]
    assert row["model_version"] == config[row["receiver_model"]]["version"]
    assert row["codebook_version"] == "global:1"  # default when unpinned
    assert row["symbolic_examples"] is True
    assert row["decoder_configuration"] == "direct symbolic"

    # RFC public format: exact header + separator, then one 6-column row each
    lines = artifact["markdown_table"].splitlines()
    assert lines[0] == h.RFC_TABLE_HEADER
    assert lines[1] == h.RFC_TABLE_SEPARATOR
    assert lines[0] == "| Variant | Wire bytes | Input tokens | Total cost | Task accuracy | Critical-fact recall |"
    for line in lines[2:]:
        assert line.startswith("| ")
        assert line.count("|") == 7  # six columns
        assert line.endswith(" |")

    # deterministic sort: variant, then receiver, then cold before warm
    cells = [line.split("|")[1].strip() for line in lines[2:]]
    assert cells == sorted(cells)
    assert any(cell.endswith("] cold") for cell in cells)
    assert any(cell.endswith("] warm") for cell in cells)

    # aggregate rows carry accuracy/recall percentages derived from the adapter
    for table_row in artifact["table_rows"]:
        assert table_row["task_accuracy"] in (0.5, 1.0)
        assert table_row["critical_fact_recall"] == 0.8
    assert "%" in markdown

    # warm-vs-cold deltas exist for every (variant, receiver) pair
    assert len(artifact["deltas"]) == 4
    for delta in artifact["deltas"]:
        assert delta["task_accuracy_delta"] == 0.5  # warm 1.0 - cold 0.5

    # no database files may be left behind in the artifact directory
    assert not list(out_dir.glob("*.db"))
    assert not list(out_dir.glob("*.sqlite*"))


# ---------------------------------------------------------------------------
# Decoder-assisted token accounting
# ---------------------------------------------------------------------------


def test_decoder_assisted_counts_expansion_tokens(h, monkeypatch, scratch_dir):
    monkeypatch.setenv("SAGE_BENCH_LLM_PROVIDER", "fake")
    cfg = scratch_dir / "adapters.json"
    cfg.write_text(json.dumps(_adapters_config()))
    out_dir = scratch_dir / "decoder-assisted"
    assert (
        h.main(
            [
                "--adapters",
                str(cfg),
                "--output",
                str(out_dir),
                "--variants",
                "v01",
                "--decoder-mode",
                "decoder-assisted",
            ]
        )
        == 0
    )
    rows = json.loads((out_dir / "model_eval_harness.json").read_text())["rows"]
    assert rows
    for row in rows:
        assert row["decoder_configuration"] == "decoder-assisted"
        assert row["adapter_input_tokens"] == 7
        assert row["expansion_tokens"] > 0
        assert row["input_tokens"] == row["adapter_input_tokens"] + row["expansion_tokens"]

    # the expansion equals the deterministic estimator on the model-facing text
    cb = h._load_compression_benchmark()
    for row in rows:
        if row["variant"] == "v01" and row["turn"] == 0:
            assert row["expansion_tokens"] == cb._estimate_tokens(cb.SHARED_CONTEXT)

    # direct-symbolic (default) adds no expansion tokens
    out_dir_plain = scratch_dir / "direct-symbolic"
    assert (
        h.main(["--adapters", str(cfg), "--output", str(out_dir_plain), "--variants", "v01"]) == 0
    )
    rows_plain = json.loads((out_dir_plain / "model_eval_harness.json").read_text())["rows"]
    for row in rows_plain:
        assert row["decoder_configuration"] == "direct symbolic"
        assert row["expansion_tokens"] == 0
        assert row["input_tokens"] == row["adapter_input_tokens"] == 7


# ---------------------------------------------------------------------------
# Adapter failures raise, never fabricate
# ---------------------------------------------------------------------------


def test_adapter_failure_raises_clear_error(h, monkeypatch):
    monkeypatch.setenv("SAGE_BENCH_LLM_PROVIDER", "fake")
    exit_config = {
        "acme-bad": {
            "family": "acme",
            "version": "1",
            "command": [sys.executable, "-c", FAKE_ADAPTER_EXIT_3],
        },
        "nebula-ok": {
            "family": "nebula",
            "version": "1",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
    }
    with pytest.raises(RuntimeError, match="acme-bad"):
        h.run_harness(exit_config, variants=["v01"])

    missing_config = {
        "acme-ok": {
            "family": "acme",
            "version": "1",
            "command": [sys.executable, "-c", FAKE_ADAPTER_OK],
        },
        "nebula-missing": {
            "family": "nebula",
            "version": "1",
            "command": [sys.executable, "-c", FAKE_ADAPTER_NO_SUCCESS],
        },
    }
    with pytest.raises(RuntimeError, match="task_success"):
        h.run_harness(missing_config, variants=["v01"])


def test_unknown_variant_rejected(h, monkeypatch):
    monkeypatch.setenv("SAGE_BENCH_LLM_PROVIDER", "fake")
    with pytest.raises(ValueError, match="unknown variant id"):
        h.run_harness(_adapters_config(), variants=["v99"])
