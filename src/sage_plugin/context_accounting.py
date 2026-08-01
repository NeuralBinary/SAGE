"""Additive context-accounting instrumentation for the SAGE codec.

This module implements Stage 1 of the semantic-context-compression benchmark
cycle (issue #16): a pure, dependency-free recorder that measures, per
exchange, the cost components that determine whether SAGE actually reduces the
context an agent must process:

* transport bytes -- wire (canonical JSON + MessagePack) and stored
  (bytes materialized into reference / state stores on behalf of the exchange);
* model-facing token estimate -- a deterministic token estimate of the
  representation the receiving model must process (tiktoken when importable,
  otherwise a documented character heuristic);
* codebook setup cost -- the codebook fingerprint plus the canonical
  definitions of any codes the receiver does not already know;
* pattern setup cost -- canonical definitions of patterns promoted this
  exchange;
* decoding / expansion cost -- the model-facing text produced by decoding
  atoms on the receive side;
* reference-fetch volume -- bytes read from the reference store while
  resolving packet references;
* fallback cost -- literals emitted for unknown/ambiguous concepts and
  unknown codes encountered during decode.

Design constraints
------------------
* Zero-cost when disabled: ``collector(False)`` returns a shared no-op
  singleton whose recorders early-return; callers guard any extra work
  (e.g. DB lookups) behind ``accounting.enabled``.
* Deterministic: every recorded value is derived from observable events;
  token estimation is deterministic in both modes.
* Thread-safe for the codec's usage pattern: one recorder instance is used
  per encode/decode call and is never shared across calls, so there is no
  cross-call shared mutable state. The no-op singleton and the module-level
  token-estimator cache are the only module state and are safe to share.
* Additive: this module must never change wire output. It imports nothing
  from the rest of ``sage_plugin`` and raises nothing.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

#: tiktoken encoding used when the optional ``bench`` extra is installed.
_TIKTOKEN_ENCODING = "cl100k_base"
#: Default heuristic width (chars per token) matching the codec's own
#: ``chars_per_token_estimate`` default. Callers may pass their setting.
_DEFAULT_CHARS_PER_TOKEN = 4.0

_encoder: Any = None
_tiktoken_attempted = False
_encoder_lock = threading.Lock()


def estimate_tokens(text: str, chars_per_token: float = _DEFAULT_CHARS_PER_TOKEN) -> int:
    """Deterministic estimate of model-facing tokens for ``text``.

    Uses tiktoken when importable (it ships in the optional ``bench`` extra,
    ``tiktoken>=0.13,<1``); otherwise falls back to a documented character
    heuristic ``ceil(len(text) / chars_per_token)``. Never raises and never
    adds a hard dependency: the import is guarded and the failure path is the
    heuristic.
    """
    global _encoder, _tiktoken_attempted
    if _encoder is None and not _tiktoken_attempted:
        with _encoder_lock:
            if _encoder is None and not _tiktoken_attempted:
                _tiktoken_attempted = True
                try:
                    import tiktoken  # type: ignore[import-not-found]

                    _encoder = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
                except Exception:
                    _encoder = None
    if _encoder is not None:
        try:
            return len(_encoder.encode(text))
        except Exception:
            pass
    return max(1, math.ceil(len(text) / max(chars_per_token, 1.0)))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class ContextReport:
    """Aggregate accounting for one or more exchanges.

    Every field is a plain number (or count); ``bytes`` fields are raw
    observed facts, ``tokens`` fields are deterministic estimates derived
    from the corresponding text.
    """

    exchanges: int = 0
    #: identity/strategy of the most recent recorded exchange
    packet_id: str | None = None
    strategy: str | None = None

    # transport
    wire_bytes_json: int = 0
    wire_bytes_msgpack: int = 0
    stored_bytes: int = 0

    # model-facing context
    model_tokens: int = 0

    # codebook setup
    codebook_setup_bytes: int = 0
    codebook_setup_tokens: int = 0
    codebook_definitions: int = 0

    # pattern setup
    pattern_setup_bytes: int = 0
    pattern_setup_tokens: int = 0
    pattern_definitions: int = 0

    # decoding / expansion
    decoding_bytes: int = 0
    decoding_tokens: int = 0

    # reference fetch volume
    reference_fetch_bytes: int = 0
    reference_fetch_count: int = 0

    # fallback cost
    fallback_bytes: int = 0
    fallback_tokens: int = 0
    fallback_count: int = 0

    def merge(self, other: ContextReport) -> ContextReport:
        """Accumulate ``other`` into this report (in place) and return self."""
        for name in (
            "exchanges",
            "wire_bytes_json",
            "wire_bytes_msgpack",
            "stored_bytes",
            "model_tokens",
            "codebook_setup_bytes",
            "codebook_setup_tokens",
            "codebook_definitions",
            "pattern_setup_bytes",
            "pattern_setup_tokens",
            "pattern_definitions",
            "decoding_bytes",
            "decoding_tokens",
            "reference_fetch_bytes",
            "reference_fetch_count",
            "fallback_bytes",
            "fallback_tokens",
            "fallback_count",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        if other.packet_id is not None:
            self.packet_id = other.packet_id
        if other.strategy is not None:
            self.strategy = other.strategy
        return self


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------


class ContextAccounting:
    """Per-exchange recorder fed by the codec's encode/decode paths.

    One instance is used per encode/decode call; it is therefore not shared
    across threads. All record methods are additive and never raise.
    """

    def __init__(self, estimate: Callable[[str], int] = estimate_tokens, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._estimate = estimate
        self._report = ContextReport()

    # -- recorders ---------------------------------------------------------

    def record_exchange(self, packet_id: str | None, strategy: str | None) -> None:
        if not self.enabled:
            return
        self._report.exchanges += 1
        if packet_id is not None:
            self._report.packet_id = packet_id
        if strategy is not None:
            self._report.strategy = strategy

    def record_wire_bytes(self, json_bytes: int, msgpack_bytes: int) -> None:
        if not self.enabled:
            return
        self._report.wire_bytes_json += int(json_bytes)
        self._report.wire_bytes_msgpack += int(msgpack_bytes)

    def record_stored_bytes(self, byte_count: int) -> None:
        if not self.enabled:
            return
        self._report.stored_bytes += max(int(byte_count), 0)

    def record_model_tokens(self, token_count: int) -> None:
        if not self.enabled:
            return
        self._report.model_tokens += max(int(token_count), 0)

    def record_codebook_fingerprint(self, fingerprint: str) -> None:
        if not self.enabled:
            return
        self._report.codebook_setup_bytes += len(fingerprint.encode("utf-8"))
        self._report.codebook_setup_tokens += self._estimate(fingerprint)

    def record_codebook_definition(self, code: str, canonical: str) -> None:
        if not self.enabled:
            return
        text = f"{code} {canonical}".strip()
        self._report.codebook_setup_bytes += len(text.encode("utf-8"))
        self._report.codebook_setup_tokens += self._estimate(text)
        self._report.codebook_definitions += 1

    def record_pattern_definition(self, canonical: str) -> None:
        if not self.enabled:
            return
        self._report.pattern_setup_bytes += len(canonical.encode("utf-8"))
        self._report.pattern_setup_tokens += self._estimate(canonical)
        self._report.pattern_definitions += 1

    def record_decoding_text(self, canonical: str, literal: Any = None) -> None:
        if not self.enabled:
            return
        parts = [p for p in (canonical, str(literal) if literal is not None else "") if p]
        text = " ".join(parts)
        self._report.decoding_bytes += len(text.encode("utf-8"))
        self._report.decoding_tokens += self._estimate(text)

    def record_reference_fetch(self, byte_size: int | None) -> None:
        if not self.enabled:
            return
        self._report.reference_fetch_count += 1
        if byte_size is not None:
            self._report.reference_fetch_bytes += max(int(byte_size), 0)

    def record_fallback(self, text: str) -> None:
        if not self.enabled:
            return
        self._report.fallback_bytes += len(text.encode("utf-8"))
        self._report.fallback_tokens += self._estimate(text)
        self._report.fallback_count += 1

    # -- reporting ---------------------------------------------------------

    def snapshot(self) -> ContextReport:
        """Return a copy of the accumulated report (safe to hold onto)."""
        return replace(self._report)

    def reset(self) -> None:
        self._report = ContextReport()


#: Shared no-op recorder returned when accounting is disabled.
_NOOP = ContextAccounting(enabled=False)


def collector(enabled: bool) -> ContextAccounting:
    """Return a fresh recorder when ``enabled``, else the shared no-op."""
    return ContextAccounting() if enabled else _NOOP
