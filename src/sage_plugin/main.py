from __future__ import annotations

import hmac
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
from .db import init_db
from .security import bearer_token

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
if settings.allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.include_router(router)
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
