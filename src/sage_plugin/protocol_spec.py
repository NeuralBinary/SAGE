from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Literal

import msgpack
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SAGE_PROTOCOL = "sage/0.1"
SAGE_WIRE_VERSION = 1
SAGE_SUPPORTED_PROTOCOLS = (SAGE_PROTOCOL,)
SAGE_SUPPORTED_WIRES = (SAGE_WIRE_VERSION,)
SAGE_MEDIA_TYPE_JSON = "application/vnd.sage.packet+json"
SAGE_MEDIA_TYPE_MSGPACK = "application/vnd.sage.packet+msgpack"


class WireProvenanceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    source_ids: list[str] | None = Field(default=None, alias="s")
    observed_at: int | str | None = Field(default=None, alias="t")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, alias="q")
    derivation: str | None = Field(default=None, alias="d")
    producer: str | None = Field(default=None, alias="p")


class WireAtomV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    code: str | None = Field(default=None, alias="c")
    code_version: int | None = Field(default=None, ge=1, alias="v")
    literal: Any | None = Field(default=None, alias="l")
    has_literal: int | None = Field(default=None, ge=1, le=1, alias="h")
    path: str | None = Field(default=None, alias="p")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, alias="q")
    epistemic_type: str | None = Field(default=None, alias="e")


class WireSignatureV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    alg: Literal["Ed25519"] = "Ed25519"
    kid: str
    sig: str


class WirePacketV1(BaseModel):
    """Normative SAGE wire-v1 object.

    Short field names are part of the frozen v1 wire contract. SAGE 0.1 is the
    initial baseline: writers and readers MUST use wire version 1.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: int = Field(default=SAGE_WIRE_VERSION, alias="v")
    codebook: str = Field(alias="c")
    act: str = Field(default="report", alias="a")
    packet_id: str | None = Field(default=None, alias="i")
    sender: str | None = Field(default=None, alias="s")
    receiver: str | None = Field(default=None, alias="r")
    atoms: list[WireAtomV1] | None = Field(default=None, alias="x")
    refs: list[str] | None = Field(default=None, alias="R")
    base: str | None = Field(default=None, alias="b")
    delta: Any | None = Field(default=None, alias="d")
    provenance: WireProvenanceV1 = Field(default_factory=WireProvenanceV1, alias="p")
    meta: dict[str, Any] | None = Field(default=None, alias="m")
    signature: WireSignatureV1 | None = Field(default=None, alias="g")


def _normalized(value: Any) -> Any:
    """Convert JSON-like data to SAGE's canonical serialization domain.

    * object keys must be strings and are sorted lexicographically by Unicode code point
    * tuples become arrays
    * non-finite floats are rejected
    * bytes are preserved for MessagePack but are not valid canonical JSON inputs
    """
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise TypeError("SAGE canonical objects require string keys")
        return {key: _normalized(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("SAGE canonical encoding forbids NaN and infinity")
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return value
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    normalized = _normalized(value)
    if _contains_bytes(normalized):
        raise TypeError("canonical JSON cannot contain raw bytes")
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_msgpack_bytes(value: Any) -> bytes:
    normalized = _normalized(value)
    return msgpack.packb(normalized, use_bin_type=True, strict_types=True)


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_msgpack_bytes(value)).hexdigest()


def _contains_bytes(value: Any) -> bool:
    if isinstance(value, bytes):
        return True
    if isinstance(value, dict):
        return any(_contains_bytes(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_bytes(v) for v in value)
    return False


def validate_wire_v1(value: dict[str, Any]) -> WirePacketV1:
    packet = WirePacketV1.model_validate(value)
    if packet.version != SAGE_WIRE_VERSION:
        raise ValueError(f"expected wire version {SAGE_WIRE_VERSION}, got {packet.version}")
    return packet


def wire_schema() -> dict[str, Any]:
    return WirePacketV1.model_json_schema(by_alias=True)


def conformance_error(value: dict[str, Any]) -> str | None:
    try:
        validate_wire_v1(value)
        canonical_msgpack_bytes(value)
    except (ValidationError, TypeError, ValueError) as exc:
        return str(exc)
    return None
