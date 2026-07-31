from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .api import router
from .config import get_settings
from .db import SessionLocal, init_db
from .security import bearer_token
from .db_models import IdempotencyRecord
from .resilience import BackpressureError, QuotaExceededError, request_hash

REQUESTS = Counter("sage_http_requests_total", "SAGE HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("sage_http_request_seconds", "SAGE HTTP latency", ["method", "path"])
settings = get_settings()

try:
    from .mcp_server import build_server

    mcp_server = build_server()
    mcp_server.settings.streamable_http_path = "/"
except RuntimeError:
    mcp_server = None


class _BodyTooLarge(Exception):
    pass




def _idempotent_write_path(path: str) -> bool:
    exact = {
        "/v1/bus/handoff", "/v1/bus/ack-batch", "/v1/refs", "/v1/states", "/v1/states/transition",
        "/v1/concepts", "/v1/patterns/observe", "/v1/calibration/record", "/v1/patterns/gc",
        "/v1/facts", "/v1/subscriptions", "/v1/publish", "/v1/routing/agents", "/v1/routing/send",
        "/v1/federation/peers", "/v1/federation/import", "/v1/receivers/model-identity",
        "/v1/codebooks/releases", "/v1/maintenance/cleanup",
    }
    if path in exact:
        return True
    return any(
        path.startswith(prefix)
        for prefix in (
            "/v1/bus/", "/v1/feedback/", "/v1/refs/", "/v1/concepts/", "/v1/patterns/",
            "/v1/facts/", "/v1/contradictions/", "/v1/states/",
        )
    ) and not path.endswith("/resolve")


class IdempotencyMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[[], Awaitable[dict[str, Any]]], send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path") or "")
        if not _idempotent_write_path(path):
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        raw_key = headers.get(b"x-idempotency-key")
        if not raw_key:
            await self.app(scope, receive, send)
            return
        try:
            key = raw_key.decode("ascii").strip()
        except UnicodeDecodeError:
            await Response('{"detail":"invalid idempotency key"}', status_code=400, media_type="application/json")(scope, receive, send)
            return
        if not key or len(key) > 128:
            await Response('{"detail":"invalid idempotency key"}', status_code=400, media_type="application/json")(scope, receive, send)
            return
        chunks: list[bytes] = []
        more = True
        while more:
            message = await receive()
            if message.get("type") != "http.request":
                continue
            chunks.append(message.get("body", b""))
            more = bool(message.get("more_body"))
        body = b"".join(chunks)
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw_sha256": hashlib.sha256(body).hexdigest()}
        workspace = payload.get("workspace", "default") if isinstance(payload, dict) else "default"
        auth = headers.get(b"authorization", b"")
        auth_scope = hashlib.sha256(auth).hexdigest()[:16]
        record_scope = f"{workspace}:{auth_scope}"[:128]
        operation = f"{scope.get('method')}:{path}"[:128]
        digest = request_hash(payload)
        from datetime import datetime, timedelta, timezone
        expires = datetime.now(timezone.utc) + timedelta(seconds=settings.idempotency_ttl_seconds)
        reserved = False
        with SessionLocal() as db:
            existing = db.query(IdempotencyRecord).filter_by(workspace=record_scope, operation=operation, key=key).one_or_none()
            if existing is not None:
                if existing.request_hash != digest:
                    await Response('{"detail":"idempotency key reused with different request"}', status_code=409, media_type="application/json")(scope, receive, send)
                    return
                cached = dict(existing.response or {})
                if cached.get("pending"):
                    await Response('{"detail":"idempotent request is in progress"}', status_code=409, media_type="application/json", headers={"Retry-After": "1"})(scope, receive, send)
                    return
                if "body" in cached:
                    await Response(
                        content=cached["body"].encode("utf-8"),
                        status_code=int(cached.get("status", 200)),
                        media_type=cached.get("media_type", "application/json"),
                        headers={"X-SAGE-Idempotent-Replay": "true"},
                    )(scope, receive, send)
                    return
            else:
                db.add(IdempotencyRecord(
                    workspace=record_scope, operation=operation, key=key, request_hash=digest, response={"pending": True}, expires_at=expires
                ))
                try:
                    db.commit()
                    reserved = True
                except Exception:
                    db.rollback()
                    await Response('{"detail":"idempotent request collision"}', status_code=409, media_type="application/json", headers={"Retry-After": "1"})(scope, receive, send)
                    return

        sent_start: dict[str, Any] | None = None
        response_chunks: list[bytes] = []

        async def replay_receive() -> dict[str, Any]:
            nonlocal body
            data, body = body, b""
            return {"type": "http.request", "body": data, "more_body": False}

        async def capture_send(message: dict[str, Any]) -> None:
            nonlocal sent_start
            if message["type"] == "http.response.start":
                sent_start = message
            elif message["type"] == "http.response.body":
                response_chunks.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                if sent_start is not None:
                    await send(sent_start)
                await send(message)

        try:
            await self.app(scope, replay_receive, capture_send)
        finally:
            if reserved:
                status = int((sent_start or {}).get("status", 500))
                response_body = b"".join(response_chunks)
                with SessionLocal() as db:
                    record = db.query(IdempotencyRecord).filter_by(workspace=record_scope, operation=operation, key=key).one_or_none()
                    if record is not None:
                        if 200 <= status < 300 and len(response_body) <= settings.http_max_body_bytes:
                            content_type = "application/json"
                            for name, value in (sent_start or {}).get("headers", []):
                                if name.lower() == b"content-type":
                                    content_type = value.decode("latin1").split(";", 1)[0]
                                    break
                            record.response = {
                                "status": status,
                                "media_type": content_type,
                                "body": response_body.decode("utf-8", errors="strict"),
                            }
                            db.commit()
                        else:
                            db.delete(record)
                            db.commit()


class BodyLimitMiddleware:
    def __init__(self, app: Any, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: Callable[[], Awaitable[dict[str, Any]]], send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        await Response('{"detail":"request body too large"}', status_code=413, media_type="application/json")(scope, receive, send)
                        return
                except ValueError:
                    await Response('{"detail":"invalid content-length"}', status_code=400, media_type="application/json")(scope, receive, send)
                    return
        received = 0

        async def limited_receive() -> dict[str, Any]:
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await Response('{"detail":"request body too large"}', status_code=413, media_type="application/json")(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_schema:
        init_db()
    if mcp_server is None:
        yield
        return
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(
    title="SAGE",
    version=__version__,
    description="Secure vendor-neutral semantic communication runtime for AI agents.",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.http_max_body_bytes)
app.add_middleware(IdempotencyMiddleware)
if settings.allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.include_router(router)


@app.exception_handler(QuotaExceededError)
async def quota_error(_: Request, exc: QuotaExceededError) -> Response:
    return Response(json.dumps({"detail": str(exc)}), status_code=429, media_type="application/json", headers={"Retry-After": "1"})


@app.exception_handler(BackpressureError)
async def backpressure_error(_: Request, exc: BackpressureError) -> Response:
    status = 503 if exc.state == "unavailable" else 429
    return Response(json.dumps({"detail": str(exc), "state": exc.state}), status_code=status, media_type="application/json", headers={"Retry-After": "1"})
if mcp_server is not None:
    app.mount("/mcp", mcp_server.streamable_http_app(), name="sage-mcp")


def _valid_service_bearer(request: Request) -> bool:
    if not settings.auth_required:
        return True
    supplied = bearer_token(request.headers.get("authorization"))
    if supplied is None:
        return False
    return any(hmac.compare_digest(supplied, expected) for expected in settings.api_keys)


@app.middleware("http")
async def security_metrics_and_mcp_auth(request: Request, call_next: Callable) -> Response:
    start = time.perf_counter()
    protected_mcp = request.url.path.startswith("/mcp") and not _valid_service_bearer(request)
    protected_metrics = request.url.path == "/metrics" and not settings.metrics_public and not _valid_service_bearer(request)
    if protected_mcp or protected_metrics:
        response = Response(
            status_code=401,
            content='{"detail":"invalid bearer token"}',
            media_type="application/json",
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.env == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if request.url.path.startswith("/v1/") or request.url.path.startswith("/mcp"):
        response.headers.setdefault("Cache-Control", "no-store")
    route = request.scope.get("route")
    path = getattr(route, "path", "__unmatched__")
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
    return response


@app.get("/health/live", include_in_schema=False)
def live() -> dict[str, object]:
    return {"alive": True, "version": __version__, "mcp": mcp_server is not None}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def run() -> None:
    import uvicorn

    uvicorn.run("sage_plugin.main:app", host="0.0.0.0", port=8080)
