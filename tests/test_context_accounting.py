"""Context-accounting instrumentation tests (issue #16, stage 1).

Covers:
* token-estimation fallback heuristic and tiktoken path (import guard);
* accounting math on known payloads;
* the shared no-op collector (zero behavioral change when disabled);
* cross-exchange report merging;
* codec instrumentation: encode/decode record real metrics;
* wire-byte identity: the instrumented codec must emit byte-identical wire
  output for a representative payload set (golden bytes captured from the
  pre-instrumentation codec at commit cf46d42, wire version 2).
"""

from __future__ import annotations

import json
import math

import pytest

import sage_plugin.context_accounting as ca
from sage_plugin.codec import SageCodec
from sage_plugin.config import Settings
from sage_plugin.db import SessionLocal
from sage_plugin.schemas import EncodeRequest, Provenance
from sage_plugin.state import StateStore

PROV = Provenance(observed_at="2026-08-01T00:00:00+00:00", producer="alice")


def _fixed_packet_id(codec: SageCodec, name: str) -> None:
    import hashlib

    codec._packet_id = lambda n=name: "P" + hashlib.sha256(n.encode()).hexdigest()[:32]  # type: ignore[method-assign]


def _base_request(**kw) -> EncodeRequest:
    req = dict(
        sender="alice",
        receiver="bob",
        provenance=PROV,
        use_cache=False,
        use_receiver_knowledge=False,
        record_learning=False,
        auto_learn=False,
    )
    req.update(kw)
    return EncodeRequest(**req)


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def test_estimate_tokens_fallback_heuristic_without_tiktoken(monkeypatch):
    monkeypatch.setattr(ca, "_encoder", None)
    monkeypatch.setattr(ca, "_tiktoken_attempted", True)
    assert ca.estimate_tokens("hello world") == math.ceil(11 / 4.0)
    assert ca.estimate_tokens("x" * 100) == 25
    assert ca.estimate_tokens("") == 1
    # custom chars-per-token width is honored
    assert ca.estimate_tokens("x" * 10, chars_per_token=2.0) == 5


def test_estimate_tokens_uses_tiktoken_when_available(monkeypatch):
    class _FakeEncoder:
        def encode(self, text: str):
            return list(range(len(text)))

    monkeypatch.setattr(ca, "_encoder", _FakeEncoder())
    monkeypatch.setattr(ca, "_tiktoken_attempted", True)
    assert ca.estimate_tokens("abcd") == 4
    assert ca.estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Accounting math on known payloads
# ---------------------------------------------------------------------------


def test_accounting_math_on_known_payloads():
    acc = ca.ContextAccounting(estimate=lambda s: len(s))
    acc.record_exchange("P1", "semantic")
    acc.record_wire_bytes(100, 80)
    acc.record_stored_bytes(50)
    acc.record_model_tokens(25)
    acc.record_codebook_fingerprint("abc123")  # 6 bytes / 6 tokens
    acc.record_codebook_definition("C1", "hello world")  # "C1 hello world" -> 14 bytes / 14 tokens
    acc.record_pattern_definition("a_b_c")  # 5 bytes / 5 tokens
    acc.record_decoding_text("hello world", {"x": 1})  # "hello world {'x': 1}" -> 20 bytes / 20 tokens
    acc.record_reference_fetch(512)
    acc.record_reference_fetch(None)  # counts, adds no bytes
    acc.record_fallback("unknown thing")  # 13 bytes / 13 tokens

    rep = acc.snapshot()
    assert rep.exchanges == 1
    assert rep.packet_id == "P1"
    assert rep.strategy == "semantic"
    assert rep.wire_bytes_json == 100
    assert rep.wire_bytes_msgpack == 80
    assert rep.stored_bytes == 50
    assert rep.model_tokens == 25
    assert rep.codebook_setup_bytes == 20  # 6 fingerprint + 14 definition
    assert rep.codebook_setup_tokens == 20
    assert rep.codebook_definitions == 1
    assert rep.pattern_setup_bytes == 5
    assert rep.pattern_setup_tokens == 5
    assert rep.pattern_definitions == 1
    assert rep.decoding_bytes == 20
    assert rep.decoding_tokens == 20
    assert rep.reference_fetch_bytes == 512
    assert rep.reference_fetch_count == 2
    assert rep.fallback_bytes == 13
    assert rep.fallback_tokens == 13
    assert rep.fallback_count == 1


def test_snapshot_is_detached_and_reset_clears():
    acc = ca.ContextAccounting(estimate=lambda s: len(s))
    acc.record_wire_bytes(10, 5)
    snap = acc.snapshot()
    acc.record_wire_bytes(10, 5)
    assert snap.wire_bytes_json == 10  # snapshot unaffected by later recording
    acc.reset()
    assert acc.snapshot().wire_bytes_msgpack == 0


def test_report_merge_accumulates():
    a = ca.ContextReport(exchanges=1, wire_bytes_json=100, wire_bytes_msgpack=80, fallback_count=1)
    b = ca.ContextReport(exchanges=1, wire_bytes_json=50, wire_bytes_msgpack=40, fallback_count=2)
    merged = ca.ContextReport().merge(a).merge(b)
    assert merged.exchanges == 2
    assert merged.wire_bytes_json == 150
    assert merged.wire_bytes_msgpack == 120
    assert merged.fallback_count == 3


# ---------------------------------------------------------------------------
# No-op collector
# ---------------------------------------------------------------------------


def test_noop_collector_is_behaviorally_inert():
    noop = ca.collector(False)
    assert noop.enabled is False
    assert ca.collector(False) is noop  # shared singleton
    # every recorder is a safe no-op
    noop.record_exchange("P1", "semantic")
    noop.record_wire_bytes(1, 2)
    noop.record_stored_bytes(3)
    noop.record_model_tokens(4)
    noop.record_codebook_fingerprint("fp")
    noop.record_codebook_definition("C1", "canonical")
    noop.record_pattern_definition("pat")
    noop.record_decoding_text("canonical", "literal")
    noop.record_reference_fetch(100)
    noop.record_fallback("fallback")
    rep = noop.snapshot()
    assert rep == ca.ContextReport()
    # enabled collectors are fresh instances, not the singleton
    assert ca.collector(True) is not noop
    assert ca.collector(True).enabled is True


# ---------------------------------------------------------------------------
# Codec instrumentation
# ---------------------------------------------------------------------------


def test_codec_disabled_accounting_is_default_and_inert():
    with SessionLocal() as db:
        codec = SageCodec(db, Settings(auth_required=False, database_url="sqlite://"))
        assert codec.accounting.enabled is False
        result = codec.encode(_base_request(content="hello world"))
        assert codec.context_report() is None
        decoded = codec.decode(result.packet)
        assert decoded.concepts == []


def test_encode_records_accounting_metrics():
    with SessionLocal() as db:
        settings = Settings(
            auth_required=False, database_url="sqlite://", context_accounting_enabled=True
        )
        codec = SageCodec(db, settings)
        result = codec.encode(_base_request(content="hello world"))
        rep = codec.context_report()
        assert rep is not None
        assert rep.exchanges == 1
        assert rep.packet_id == result.packet.id
        assert rep.strategy == "semantic"
        assert rep.wire_bytes_json == result.output_bytes_json
        assert rep.wire_bytes_msgpack == result.output_bytes_msgpack
        assert rep.model_tokens > 0
        assert rep.codebook_setup_bytes > 0  # fingerprint recorded
        assert rep.fallback_count >= 1  # unknown unit fell back to literal


def test_encode_records_codebook_definitions_for_unknown_codes():
    with SessionLocal() as db:
        settings = Settings(
            auth_required=False, database_url="sqlite://", context_accounting_enabled=True
        )
        codec = SageCodec(db, settings)
        codec.codebook.register("global", "refund_requested")
        db.commit()
        codec.encode(_base_request(content="refund requested"))
        rep = codec.context_report()
        assert rep is not None
        assert rep.codebook_definitions == 1  # receiver does not know C00000001
        assert rep.codebook_setup_tokens > 0


def test_encode_records_stored_bytes_for_state_and_reference():
    with SessionLocal() as db:
        settings = Settings(
            auth_required=False, database_url="sqlite://", context_accounting_enabled=True
        )
        codec = SageCodec(db, settings)
        codec.encode(_base_request(content={"status": "blocked", "count": 3}))
        rep = codec.context_report()
        assert rep is not None
        assert rep.stored_bytes == len(b'{"count":3,"status":"blocked"}')
        codec.encode(_base_request(content={"blob": "x" * 3000}))
        rep2 = codec.context_report()
        assert rep2 is not None
        assert rep2.strategy == "reference"
        assert rep2.stored_bytes > 0
        assert rep2.reference_fetch_count == 0  # fetch happens on decode, not encode


def test_decode_records_decoding_and_reference_fetch_metrics():
    with SessionLocal() as db:
        settings = Settings(
            auth_required=False, database_url="sqlite://", context_accounting_enabled=True
        )
        codec = SageCodec(db, settings)
        encoded = codec.encode(_base_request(content={"blob": "x" * 3000}))
        codec.decode(encoded.packet, resolve_refs=True, receiver="bob")
        rep = codec.context_report()
        assert rep is not None
        assert rep.strategy == "reference"
        assert rep.reference_fetch_count >= 1
        assert rep.reference_fetch_bytes > 0
        # reference packets carry no atoms: expansion cost is the fetch volume
        assert rep.decoding_bytes == 0
        assert rep.decoding_tokens == 0


def test_decode_records_fallback_for_unknown_code():
    with SessionLocal() as db:
        settings = Settings(
            auth_required=False, database_url="sqlite://", context_accounting_enabled=True
        )
        codec = SageCodec(db, settings)
        encoded = codec.encode(_base_request(content="hello world"))
        codec.decode(encoded.packet, receiver="bob")
        rep = codec.context_report()
        assert rep is not None
        # unknown (no-code) atoms are decoded as literals: expansion recorded,
        # no codebook definition cost on the receive side
        assert rep.decoding_bytes > 0
        assert rep.fallback_count == 0


# ---------------------------------------------------------------------------
# Wire-byte identity (golden bytes captured from pre-instrumentation codec)
# ---------------------------------------------------------------------------

GOLDEN_CASES = {
    "delta": {
        "strategy": "delta",
        "wire_json": "{\"a\":\"report\",\"b\":\"S2976efd240d42031d5b8b5ef196fc25232f37d29\",\"c\":\"global\",\"d\":[{\"op\":\"replace\",\"path\":\"/failed\",\"value\":1}],\"i\":\"P4f4a9410ffcdf895c4adb880659e9b5c\",\"m\":{\"revision\":2,\"state\":\"S495c3c766e5c28338dbf242ed7b7ad624142457f\"},\"p\":{\"p\":\"alice\",\"t\":1785542400},\"r\":\"bob\",\"s\":\"alice\",\"v\":2}",
        "wire_msgpack_b64": "iqFhpnJlcG9ydKFi2SlTMjk3NmVmZDI0MGQ0MjAzMWQ1YjhiNWVmMTk2ZmMyNTIzMmYzN2QyOaFjpmdsb2JhbKFkkYOib3CncmVwbGFjZaRwYXRopy9mYWlsZWSldmFsdWUBoWnZIVA0ZjRhOTQxMGZmY2RmODk1YzRhZGI4ODA2NTllOWI1Y6FtgqhyZXZpc2lvbgKlc3RhdGXZKVM0OTVjM2M3NjZlNWMyODMzOGRiZjI0MmVkN2I3YWQ2MjQxNDI0NTdmoXCCoXClYWxpY2WhdM5qbTcAoXKjYm9ioXOlYWxpY2WhdgI=",
        "output_bytes_json": 297,
        "output_bytes_msgpack": 233,
        "packet_id": "P4f4a9410ffcdf895c4adb880659e9b5c",
    },
    "literal_string": {
        "strategy": "semantic",
        "wire_json": "{\"a\":\"report\",\"c\":\"global\",\"i\":\"P1a17e4773202e98bb505febb620a1b52\",\"p\":{\"p\":\"alice\",\"t\":1785542400},\"r\":\"bob\",\"s\":\"alice\",\"v\":2,\"x\":[{\"h\":1,\"l\":\"hello world\",\"p\":\"$\"}]}",
        "wire_msgpack_b64": "iKFhpnJlcG9ydKFjpmdsb2JhbKFp2SFQMWExN2U0NzczMjAyZTk4YmI1MDVmZWJiNjIwYTFiNTKhcIKhcKVhbGljZaF0zmptNwChcqNib2Khc6VhbGljZaF2AqF4kYOhaAGhbKtoZWxsbyB3b3JsZKFwoSQ=",
        "output_bytes_json": 168,
        "output_bytes_msgpack": 116,
        "packet_id": "P1a17e4773202e98bb505febb620a1b52",
    },
    "reference": {
        "strategy": "reference",
        "wire_json": "{\"R\":[\"sage:sha256:b6b7f9a9be427689b75d86a5fd3b63d874bd5a453d51c324ada7772552764c4a\"],\"a\":\"report\",\"c\":\"global\",\"i\":\"P52367a6622b19f08825e915fad80c542\",\"m\":{\"memory_tier\":\"hot\",\"revision\":1,\"state\":\"Sf95883a1680cc9f429b2b69cc86afcaa7aed7dd2\"},\"p\":{\"p\":\"alice\",\"t\":1785542400},\"r\":\"bob\",\"s\":\"alice\",\"v\":2}",
        "wire_msgpack_b64": "iaFSkdlMc2FnZTpzaGEyNTY6YjZiN2Y5YTliZTQyNzY4OWI3NWQ4NmE1ZmQzYjYzZDg3NGJkNWE0NTNkNTFjMzI0YWRhNzc3MjU1Mjc2NGM0YaFhpnJlcG9ydKFjpmdsb2JhbKFp2SFQNTIzNjdhNjYyMmIxOWYwODgyNWU5MTVmYWQ4MGM1NDKhbYOrbWVtb3J5X3RpZXKjaG90qHJldmlzaW9uAaVzdGF0ZdkpU2Y5NTg4M2ExNjgwY2M5ZjQyOWIyYjY5Y2M4NmFmY2FhN2FlZDdkZDKhcIKhcKVhbGljZaF0zmptNwChcqNib2Khc6VhbGljZaF2Ag==",
        "output_bytes_json": 304,
        "output_bytes_msgpack": 250,
        "packet_id": "P52367a6622b19f08825e915fad80c542",
    },
    "semantic_code": {
        "strategy": "semantic",
        "wire_json": "{\"a\":\"report\",\"c\":\"global\",\"i\":\"Pe6f55b5aeb4ac5efde6f1c724c342f81\",\"p\":{\"p\":\"alice\",\"t\":1785542400},\"r\":\"bob\",\"s\":\"alice\",\"v\":2,\"x\":[{\"c\":\"C00000001\",\"p\":\"$\",\"v\":1}]}",
        "wire_msgpack_b64": "iKFhpnJlcG9ydKFjpmdsb2JhbKFp2SFQZTZmNTViNWFlYjRhYzVlZmRlNmYxYzcyNGMzNDJmODGhcIKhcKVhbGljZaF0zmptNwChcqNib2Khc6VhbGljZaF2AqF4kYOhY6lDMDAwMDAwMDGhcKEkoXYB",
        "output_bytes_json": 166,
        "output_bytes_msgpack": 114,
        "packet_id": "Pe6f55b5aeb4ac5efde6f1c724c342f81",
    },
    "state_checkpoint": {
        "strategy": "semantic",
        "wire_json": "{\"a\":\"report\",\"c\":\"global\",\"i\":\"P81ae62c0ca668c37dc9dc68d09042f96\",\"m\":{\"revision\":1,\"state\":\"Sd3819d6c535a664d593768d6ea6ee40e53984528\"},\"p\":{\"p\":\"alice\",\"t\":1785542400},\"r\":\"bob\",\"s\":\"alice\",\"v\":2,\"x\":[{\"h\":1,\"l\":3,\"p\":\"$.count\"},{\"h\":1,\"l\":\"blocked\",\"p\":\"$.status\"}]}",
        "wire_msgpack_b64": "iaFhpnJlcG9ydKFjpmdsb2JhbKFp2SFQODFhZTYyYzBjYTY2OGMzN2RjOWRjNjhkMDkwNDJmOTahbYKocmV2aXNpb24BpXN0YXRl2SlTZDM4MTlkNmM1MzVhNjY0ZDU5Mzc2OGQ2ZWE2ZWU0MGU1Mzk4NDUyOKFwgqFwpWFsaWNloXTOam03AKFyo2JvYqFzpWFsaWNloXYCoXiSg6FoAaFsA6FwpyQuY291bnSDoWgBoWynYmxvY2tlZKFwqCQuc3RhdHVz",
        "output_bytes_json": 270,
        "output_bytes_msgpack": 198,
        "packet_id": "P81ae62c0ca668c37dc9dc68d09042f96",
    }
}


@pytest.mark.parametrize(
    "name,golden",
    sorted(GOLDEN_CASES.items()),
    ids=sorted(GOLDEN_CASES),
)
def test_instrumented_codec_wire_bytes_match_pre_instrumentation_golden(name, golden):
    with SessionLocal() as db:
        settings = Settings(auth_required=False, database_url="sqlite://")
        codec = SageCodec(db, settings)
        _fixed_packet_id(codec, name)

        if name == "delta":
            state = StateStore(db).create({"failed": 3, "branch": "main"})
            db.commit()
            req = _base_request(content={"failed": 1, "branch": "main"}, base_state=state.id)
        elif name == "semantic_code":
            codec.codebook.register("global", "refund_requested")
            db.commit()
            req = _base_request(content="refund requested")
        elif name == "state_checkpoint":
            req = _base_request(content={"status": "blocked", "count": 3})
        elif name == "reference":
            req = _base_request(content={"blob": "x" * 3000})
        else:
            req = _base_request(content="hello world")

        result = codec.encode(req)
        assert result.strategy == golden["strategy"]
        assert result.wire_json == golden["wire_json"]
        assert result.wire_msgpack_b64 == golden["wire_msgpack_b64"]
        assert result.output_bytes_json == golden["output_bytes_json"]
        assert result.output_bytes_msgpack == golden["output_bytes_msgpack"]
        assert result.packet.id == golden["packet_id"]
        # wire version stays 2 (protocol frozen; instrumentation is additive)
        assert json.loads(result.wire_json)["v"] == 2
