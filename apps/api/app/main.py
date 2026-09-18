import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import text
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.database import create_engine
from app.core.logging import configure_logging
from app.modules.identity.routes import router as identity_router
from app.modules.identity.security import AuthError

log = structlog.get_logger()


class Probe(BaseModel):
    status: Literal["ok", "ready", "unavailable"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    app.state.identity_engine = create_sync_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    app.state.engine = create_engine(settings)
    app.state.redis = Redis.from_url(
        settings.redis_url.get_secret_value(), socket_timeout=2, socket_connect_timeout=2
    )
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await app.state.engine.dispose()
        app.state.identity_engine.dispose()


async def dependencies_ready(request: Request) -> bool:
    try:
        async with asyncio.timeout(4):
            async with request.app.state.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await request.app.state.redis.ping()
        return True
    except Exception as exc:
        # Exception text can contain connection credentials. Record classification only.
        log.warning("readiness_failed", error_type=type(exc).__name__)
        return False


def create_app() -> FastAPI:
    settings = get_settings()
    docs_enabled = settings.app_env in {"local", "test"}
    app = FastAPI(
        title="EDP Platform API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.include_router(identity_router)

    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": {
                    "code": exc.code,
                    "message": "Request could not be completed",
                    "request_id": request.state.request_id,
                }
            },
            headers={"Retry-After": "900"} if exc.status == 429 else None,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        except Exception as exc:
            log.error("request_failed", error_type=type(exc).__name__)
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_error",
                        "message": "Request failed",
                        "request_id": request_id,
                    }
                },
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        log.info("request_completed", method=request.method, status=response.status_code)
        structlog.contextvars.clear_contextvars()
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request",
                    "request_id": request.state.request_id,
                    "details": [{"field": list(e["loc"]), "code": e["type"]} for e in exc.errors()],
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": "Request could not be completed",
                    "request_id": request.state.request_id,
                }
            },
        )

    @app.get("/health", response_model=Probe, tags=["operations"])
    async def health() -> Probe:
        return Probe(status="ok")

    @app.get("/ready", response_model=Probe, responses={503: {"model": Probe}}, tags=["operations"])
    async def ready(request: Request, response: Response) -> Probe:
        if not await dependencies_ready(request):
            response.status_code = 503
            return Probe(status="unavailable")
        return Probe(status="ready")

    return app


app = create_app()
