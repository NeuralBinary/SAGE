from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[int((len(ordered) - 1) * fraction)]


def measure(call, iterations: int) -> tuple[list[float], list[object]]:
    elapsed: list[float] = []
    values: list[object] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        values.append(call())
        elapsed.append((time.perf_counter_ns() - started) / 1_000_000)
    return elapsed, values


def stats(values: list[float]) -> dict[str, float]:
    return {
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(percentile(values, 0.95), 3),
        "max_ms": round(max(values), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SAGE deterministic latency verification")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--core-encode-p95-ms", type=float, default=40.0)
    parser.add_argument("--core-decode-p95-ms", type=float, default=10.0)
    parser.add_argument("--http-send-p95-ms", type=float, default=75.0)
    parser.add_argument("--http-receive-p95-ms", type=float, default=50.0)
    args = parser.parse_args()
    if args.iterations < 20:
        raise SystemExit("iterations must be at least 20")

    db_path = Path(tempfile.gettempdir()) / f"sage-performance-{os.getpid()}.db"
    db_path.unlink(missing_ok=True)
    os.environ["SAGE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["SAGE_AUTH_REQUIRED"] = "false"
    os.environ["SAGE_PATTERN_LEARNING_ENABLED"] = "false"
    os.environ["SAGE_SEMANTIC_CACHE_ENABLED"] = "false"

    from fastapi.testclient import TestClient

    from sage_plugin.codec import SageCodec
    from sage_plugin.config import get_settings
    from sage_plugin.db import Base, SessionLocal, engine
    from sage_plugin.main import app
    from sage_plugin.schemas import EncodeRequest

    Base.metadata.create_all(engine)
    settings = get_settings()
    content = {
        "project": "sage",
        "status": "active",
        "count": 17,
        "flags": ["secure", "stable", "fast"],
        "note": "semantic transport production verification",
    }

    with SessionLocal() as db:
        codec = SageCodec(db, settings)
        request = EncodeRequest(sender="latency-producer", receiver="latency-consumer", content=content)
        for _ in range(20):
            codec.encode(request)
        encode_times, encoded = measure(lambda: codec.encode(request), args.iterations)
        packets = [item.packet for item in encoded]
        packet_index = 0

        def decode_once():
            nonlocal packet_index
            packet = packets[packet_index % len(packets)]
            packet_index += 1
            return codec.decode(packet)

        decode_times, _ = measure(decode_once, args.iterations)

    with TestClient(app) as client:
        for _ in range(10):
            response = client.post("/v1/transport/send", json={"sender": "latency-producer", "receiver": "latency-consumer", "content": content})
            response.raise_for_status()

        def http_send():
            response = client.post("/v1/transport/send", json={"sender": "latency-producer", "receiver": "latency-consumer", "content": content})
            response.raise_for_status()
            return response.json()

        http_send_times, sent = measure(http_send, max(20, args.iterations // 2))
        wires = [item["wire"] for item in sent]
        wire_index = 0

        def http_receive():
            nonlocal wire_index
            wire = wires[wire_index % len(wires)]
            wire_index += 1
            response = client.post("/v1/transport/receive", json={"receiver": "latency-consumer", "wire": wire, "acknowledge": False})
            response.raise_for_status()
            return response.json()

        http_receive_times, _ = measure(http_receive, max(20, args.iterations // 2))

    report = {
        "iterations": args.iterations,
        "core_encode": stats(encode_times),
        "core_decode": stats(decode_times),
        "http_send": stats(http_send_times),
        "http_receive": stats(http_receive_times),
        "limits_ms": {
            "core_encode_p95": args.core_encode_p95_ms,
            "core_decode_p95": args.core_decode_p95_ms,
            "http_send_p95": args.http_send_p95_ms,
            "http_receive_p95": args.http_receive_p95_ms,
        },
    }
    failures = []
    if report["core_encode"]["p95_ms"] > args.core_encode_p95_ms:
        failures.append("core encode p95")
    if report["core_decode"]["p95_ms"] > args.core_decode_p95_ms:
        failures.append("core decode p95")
    if report["http_send"]["p95_ms"] > args.http_send_p95_ms:
        failures.append("HTTP send p95")
    if report["http_receive"]["p95_ms"] > args.http_receive_p95_ms:
        failures.append("HTTP receive p95")
    report["ok"] = not failures
    report["failures"] = failures
    print(json.dumps(report, separators=(",", ":")))

    Base.metadata.drop_all(engine)
    engine.dispose()
    db_path.unlink(missing_ok=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
