import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import check_db_connection, ensure_postgis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.core.error_handler import register_error_handlers
from backend.app.core.logger import setup_logging
from backend.app.core.logging_middleware import APILoggingMiddleware
from backend.app.core.metrics import MetricsMiddleware, metrics_endpoint
from backend.app.core.rate_limiter import limiter
from backend.app.api.auth import router as auth_router
from backend.app.api.screening import router as screening_router
from backend.app.api.data_status import router as data_status_router
from backend.app.api.evaluation import router as evaluation_router
from backend.app.api.cases import router as cases_router
from backend.app.api.cases import screening_router as cases_screening_router
from backend.app.api.compare import router as compare_router
from backend.app.api.patterns import router as patterns_router
from backend.app.api.draft import router as draft_router
from backend.app.api.draft import template_router as draft_template_router
from backend.app.api.review import router as review_router
from backend.app.api.rag import router as rag_router
from backend.app.api.admin import router as admin_router
from backend.app.core.auth import get_auth_user

setup_logging()
logger = logging.getLogger("eia-prescreen")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    logger.info("EIA Pre-Screen backend starting up...")

    db_ok = await check_db_connection()
    if db_ok:
        logger.info("Database connection OK")
        await ensure_postgis()
        logger.info("PostGIS extension ensured")
    else:
        logger.warning(
            "Database connection failed — running in limited mode. "
            "Check DATABASE_URL or start PostgreSQL."
        )

    yield

    # Shutdown
    logger.info("EIA Pre-Screen backend shutting down...")


app = FastAPI(
    title="EIA Pre-Screen API",
    description="환경영향평가 사전검토 지원 도구 API",
    version="0.1.0",
    lifespan=lifespan,
)

# Error handlers
register_error_handlers(app)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API Logging (순수 ASGI 미들웨어 — BaseHTTPMiddleware는 dependency injection 간섭)
app.add_middleware(APILoggingMiddleware)

# Prometheus metrics
app.add_middleware(MetricsMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.mount_path = "/api"
_auth_deps = [Depends(get_auth_user)]

# Public routers (no auth required)
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(data_status_router, prefix="/api/data-status", tags=["data-status"])
app.include_router(patterns_router, prefix="/api/patterns", tags=["patterns"])
app.include_router(draft_template_router, prefix="/api", tags=["draft"])

# Protected routers (JWT required)
app.include_router(screening_router, prefix="/api/screening", tags=["screening"], dependencies=_auth_deps)
app.include_router(evaluation_router, prefix="/api/screening", tags=["evaluation"], dependencies=_auth_deps)
app.include_router(cases_router, prefix="/api/cases", tags=["cases"], dependencies=_auth_deps)
app.include_router(cases_screening_router, prefix="/api/screening", tags=["cases"], dependencies=_auth_deps)
app.include_router(compare_router, prefix="/api/screening", tags=["compare"], dependencies=_auth_deps)
app.include_router(draft_router, prefix="/api/screening", tags=["draft"], dependencies=_auth_deps)
app.include_router(review_router, prefix="/api/screening", tags=["review"], dependencies=_auth_deps)
app.include_router(rag_router, prefix="/api/rag", tags=["rag"], dependencies=_auth_deps)
app.include_router(admin_router, prefix="/api/admin", tags=["admin"], dependencies=_auth_deps)


@app.get("/health")
async def health_check() -> dict:
    db_ok = await check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "demo_mode": settings.DEMO_MODE,
    }


app.add_route("/metrics", metrics_endpoint, methods=["GET"])
