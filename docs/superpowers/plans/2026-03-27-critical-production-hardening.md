# Critical Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 4 critical production blockers: JWT authentication, Dockerfiles, rate limiting, and global error handling.

**Architecture:** JWT auth with bcrypt password hashing, 3 roles (admin/analyst/viewer), applied via FastAPI `Depends()`. slowapi for rate limiting. Centralized error handler registered in `main.py`. Multi-stage Docker builds for both services.

**Tech Stack:** PyJWT, bcrypt, slowapi, FastAPI exception handlers, Docker multi-stage builds

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `backend/app/models/user.py` | User SQLAlchemy model (email, hashed_password, role, is_active) |
| `backend/app/schemas/auth.py` | Pydantic models for register/login/token responses |
| `backend/app/core/auth.py` | JWT encode/decode, password hashing, `get_current_user` dependency |
| `backend/app/api/auth.py` | POST /register, /login, /refresh endpoints |
| `backend/app/core/error_handler.py` | Global exception handlers (500, 422, HTTPException) |
| `backend/app/core/rate_limiter.py` | slowapi limiter instance and key functions |
| `backend/Dockerfile` | Python 3.12-slim backend image |
| `frontend/Dockerfile` | Node 20-slim multi-stage frontend image |

### Modified Files
| File | Changes |
|------|---------|
| `backend/requirements.txt` | Add PyJWT, bcrypt, slowapi |
| `backend/app/core/config.py` | Add SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS |
| `backend/app/db/migrations/env.py:12` | Add `import backend.app.models.user` |
| `backend/app/main.py` | Register auth router, error handlers, rate limiter |
| `backend/app/api/screening.py` | Add `Depends(get_current_user)` to all endpoints |
| `backend/app/api/evaluation.py` | Add `Depends(get_current_user)` to all endpoints |
| `backend/app/api/cases.py` | Add `Depends(get_current_user)` to all endpoints on both routers |
| `backend/app/api/compare.py` | Add `Depends(get_current_user)` to all endpoints |
| `backend/app/api/data_status.py` | Add `Depends(get_current_user)` to all endpoints |
| `docker-compose.yml` | Add SECRET_KEY env var, verify Dockerfile paths |

---

## Task 1: Global Error Handler (C-4)

**Rationale:** Implement this first because all subsequent tasks benefit from consistent error responses.

**Files:**
- Create: `backend/app/core/error_handler.py`
- Modify: `backend/app/main.py:42-47`

- [ ] **Step 1: Create error handler module**

```python
# backend/app/core/error_handler.py
"""Global exception handlers — unified error response format."""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("eia-prescreen")


def register_error_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "입력 데이터가 유효하지 않습니다.",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "detail": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "서버 내부 오류가 발생했습니다.",
                "detail": None,
            },
        )
```

- [ ] **Step 2: Register error handlers in main.py**

Add after app creation (after line 47 of `backend/app/main.py`):

```python
from backend.app.core.error_handler import register_error_handlers

# After app = FastAPI(...)
register_error_handlers(app)
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `cd C:/0_project/eia-prescreen && PYTHONPATH=. python -m pytest tests/test_smoke_e2e.py -v`

Expected: Some tests may need adjustment because error responses now have a different JSON structure. The health endpoint returns 200 OK unchanged. HTTP error tests (404, 422) should still get correct status codes — the body format changes but the tests primarily check status codes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/error_handler.py backend/app/main.py
git commit -m "feat(C-4): add global error handler with unified error response format"
```

---

## Task 2: User Model + Migration (C-1 part 1)

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/db/migrations/env.py:12`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Append to `backend/requirements.txt`:

```
PyJWT==2.9.*
bcrypt==4.2.*
slowapi==0.1.*
```

- [ ] **Step 2: Install dependencies**

Run: `pip install PyJWT bcrypt slowapi`

- [ ] **Step 3: Create User model**

```python
# backend/app/models/user.py
"""User model for authentication."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    """사용자 계정."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.ANALYST
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

- [ ] **Step 4: Register User model in migrations env.py**

Add after line 12 of `backend/app/db/migrations/env.py`:

```python
import backend.app.models.user  # noqa: F401
```

- [ ] **Step 5: Generate Alembic migration**

Run: `cd C:/0_project/eia-prescreen && PYTHONPATH=. alembic revision --autogenerate -m "add_users_table"`

Expected: New migration file in `backend/app/db/migrations/versions/` creating `users` table.

- [ ] **Step 6: Apply migration**

Run: `cd C:/0_project/eia-prescreen && PYTHONPATH=. alembic upgrade head`

Expected: `INFO [alembic.runtime.migration] Running upgrade ... -> ..., add_users_table`

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/models/user.py backend/app/db/migrations/env.py backend/app/db/migrations/versions/
git commit -m "feat(C-1): add User model with roles and Alembic migration"
```

---

## Task 3: Auth Core — JWT + Password Hashing (C-1 part 2)

**Files:**
- Create: `backend/app/core/auth.py`
- Modify: `backend/app/core/config.py:40` (add token config)

- [ ] **Step 1: Add token settings to config.py**

Add after line 40 of `backend/app/core/config.py` (after `SECRET_KEY`):

```python
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

- [ ] **Step 2: Create auth core module**

```python
# backend/app/core/auth.py
"""JWT token management and password hashing."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_session
from backend.app.models.user import User

_security = HTTPBearer(auto_error=False)

_ALGORITHM = "HS256"


# ── Password ──


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ──


def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰이 만료되었습니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")


# ── Dependencies ──


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI dependency — extracts and validates the current user from Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access 토큰이 아닙니다.")

    user_id = payload.get("sub")
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")

    return user


def require_role(*roles: str):
    """Dependency factory — checks that the current user has one of the required roles."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"이 작업에는 {', '.join(roles)} 권한이 필요합니다.",
            )
        return user
    return _check
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/auth.py backend/app/core/config.py
git commit -m "feat(C-1): add JWT auth core with password hashing and role-based dependencies"
```

---

## Task 4: Auth API Endpoints (C-1 part 3)

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/main.py` (register auth router)

- [ ] **Step 1: Create auth schemas**

```python
# backend/app/schemas/auth.py
"""Authentication request/response schemas."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field("", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create auth API endpoints**

```python
# backend/app/api/auth.py
"""Authentication endpoints — register, login, refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.app.core.database import get_session
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    # Check duplicate email
    stmt = select(User).where(User.email == body.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse, summary="로그인")
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    stmt = select(User).where(User.email == body.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.post("/refresh", response_model=TokenResponse, summary="토큰 갱신")
async def refresh_token(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh 토큰이 아닙니다.",
        )

    user_id = payload.get("sub")
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.get("/me", response_model=UserResponse, summary="현재 사용자 정보")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
    )
```

- [ ] **Step 3: Register auth router in main.py**

Add to imports in `backend/app/main.py`:

```python
from backend.app.api.auth import router as auth_router
```

Add to router registrations (after line 65):

```python
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/auth.py backend/app/main.py
git commit -m "feat(C-1): add auth API endpoints — register, login, refresh, me"
```

---

## Task 5: Apply Auth to All Existing Endpoints (C-1 part 4)

**Files:**
- Modify: `backend/app/api/screening.py:1-4,29-31,68-70,97-98`
- Modify: `backend/app/api/evaluation.py:1-4,84-87,239-241,271-273`
- Modify: `backend/app/api/cases.py:1-4,49-55,98,132-135,198-200,277-279`
- Modify: `backend/app/api/compare.py:1-4,35-37,199-201`
- Modify: `backend/app/api/data_status.py:1-4,115,142-147,162-168`

The pattern is the same for every endpoint — add `get_current_user` import and add `current_user: User = Depends(get_current_user)` as a parameter. The parameter is unused in the function body (it just triggers the auth check).

- [ ] **Step 1: Add auth dependency to screening.py**

Add import:
```python
from backend.app.core.auth import get_current_user
from backend.app.models.user import User
```

Add to each endpoint function signature:
```python
async def create_screening(
    body: ScreeningInput,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),          # ← ADD
) -> ScreeningResponse:
```

Same for `get_screening` and `list_screenings`.

- [ ] **Step 2: Add auth dependency to evaluation.py**

Same pattern — add import and `_: User = Depends(get_current_user)` to:
- `evaluate_screening` (line 84)
- `get_regulations` (line 239)
- `get_checklist` (line 271)

- [ ] **Step 3: Add auth dependency to cases.py**

Same pattern for both `router` and `screening_router` endpoints:
- `search_cases` (line 49)
- `get_case` (line 98) — note: no session param, add after case_id
- `find_similar_cases` (line 132)
- `interpret_screening` (line 198)
- `generate_report` (line 277)

- [ ] **Step 4: Add auth dependency to compare.py**

- `compare_screenings` (line 35)
- `compare_report` (line 199)

- [ ] **Step 5: Add auth dependency to data_status.py**

- `list_connectors` (line 115) — currently no params, add:
  ```python
  async def list_connectors(_: User = Depends(get_current_user)) -> ConnectorListResponse:
  ```
- `get_screening_data_status` (line 142)
- `get_data_status` (line 162)

Also add imports at top of `data_status.py`:
```python
from fastapi import APIRouter, Depends, Query
from backend.app.core.auth import get_current_user
from backend.app.models.user import User
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/screening.py backend/app/api/evaluation.py backend/app/api/cases.py backend/app/api/compare.py backend/app/api/data_status.py
git commit -m "feat(C-1): apply JWT auth dependency to all API endpoints"
```

---

## Task 6: Rate Limiting (C-3)

**Files:**
- Create: `backend/app/core/rate_limiter.py`
- Modify: `backend/app/main.py` (add slowapi middleware + state)
- Modify: `backend/app/api/cases.py` (LLM interpret limit)
- Modify: `backend/app/api/evaluation.py` (report limit annotation example)

- [ ] **Step 1: Create rate limiter module**

```python
# backend/app/core/rate_limiter.py
"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from backend.app.core.auth import _security


def _get_key(request: Request) -> str:
    """Rate limit key: user ID if authenticated, else IP address."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        # Use a hash of the token as the key (avoids decoding overhead)
        return f"user:{hash(auth)}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_key)

# Pre-built decorators for common limits
LIMIT_DEFAULT = "60/minute"          # Authenticated general endpoints
LIMIT_UNAUTHENTICATED = "10/minute"  # No auth fallback
LIMIT_LLM = "10/minute"             # LLM interpret (expensive)
LIMIT_PDF = "20/minute"             # PDF generation (CPU-intensive)
```

- [ ] **Step 2: Register slowapi in main.py**

Add imports:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.app.core.rate_limiter import limiter
```

Add after `register_error_handlers(app)`:
```python
# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: Apply rate limits to expensive endpoints**

In `backend/app/api/cases.py`, add to LLM interpret endpoint:

```python
from backend.app.core.rate_limiter import limiter, LIMIT_LLM, LIMIT_PDF

@screening_router.post("/{screening_id}/interpret", ...)
@limiter.limit(LIMIT_LLM)
async def interpret_screening(
    request: Request,           # ← ADD as first param
    screening_id: UUID,
    ...
```

In `backend/app/api/cases.py`, report endpoint:

```python
@screening_router.post("/{screening_id}/report", ...)
@limiter.limit(LIMIT_PDF)
async def generate_report(
    request: Request,           # ← ADD as first param
    screening_id: UUID,
    ...
```

Add `from starlette.requests import Request` to imports.

In `backend/app/api/compare.py`, compare report:

```python
from backend.app.core.rate_limiter import limiter, LIMIT_PDF
from starlette.requests import Request

@router.post("/compare/report", ...)
@limiter.limit(LIMIT_PDF)
async def compare_report(
    request: Request,           # ← ADD as first param
    body: CompareRequest,
    ...
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/rate_limiter.py backend/app/main.py backend/app/api/cases.py backend/app/api/compare.py
git commit -m "feat(C-3): add rate limiting with slowapi — tiered limits for LLM/PDF/general"
```

---

## Task 7: Dockerfiles (C-2)

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Create backend Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

# System dependencies for psycopg2/geoalchemy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create frontend Dockerfile (multi-stage)**

```dockerfile
# frontend/Dockerfile

# ── Stage 1: Install dependencies ──
FROM node:20-slim AS deps
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ── Stage 2: Build ──
FROM node:20-slim AS builder
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

# ── Stage 3: Production ──
FROM node:20-slim AS runner
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy build output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
```

- [ ] **Step 3: Update docker-compose.yml**

Replace the full file:

```yaml
services:
  # ── PostgreSQL + PostGIS ──
  db:
    image: postgis/postgis:16-3.4
    container_name: eia-prescreen-db
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-eia_prescreen}
      POSTGRES_USER: ${POSTGRES_USER:-eia_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-change_me_in_production}
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-eia_user} -d ${POSTGRES_DB:-eia_prescreen}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── FastAPI Backend ──
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: eia-prescreen-backend
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-eia_user}:${POSTGRES_PASSWORD:-change_me_in_production}@db:5432/${POSTGRES_DB:-eia_prescreen}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      DEMO_MODE: ${DEMO_MODE:-true}
      CACHE_DIR: /app/data/snapshots
      SECRET_KEY: ${SECRET_KEY:-change_me_in_production}
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 15s
      timeout: 5s
      retries: 3

  # ── Next.js Frontend ──
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: eia-prescreen-frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:${BACKEND_PORT:-8000}
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 4: Add next.config.ts output: "standalone" for Docker**

In `frontend/next.config.ts`, change to:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 5: Create .dockerignore files**

`backend/.dockerignore`:
```
__pycache__
*.pyc
.env
venv
.git
```

`frontend/.dockerignore`:
```
node_modules
.next
.env.local
.git
```

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile frontend/Dockerfile docker-compose.yml frontend/next.config.ts backend/.dockerignore frontend/.dockerignore
git commit -m "feat(C-2): add Dockerfiles with multi-stage frontend build, update docker-compose"
```

---

## Task 8: Fix Tests for Auth + Error Handler Changes

**Files:**
- Modify: `tests/test_smoke_e2e.py`

- [ ] **Step 1: Update test_smoke_e2e.py**

Tests that hit authenticated endpoints will now get 401 instead of their previous responses. The `TestClient` fixture needs a helper to create auth tokens, OR the tests should verify 401 for unauthenticated requests.

Key changes:
1. Auth-protected endpoints now return 401 without a token
2. Error responses have new `{error, message, detail}` format
3. `/health` and `/api/auth/*` remain unauthenticated

Update HTTP endpoint tests:
- `test_health_endpoint` — unchanged (no auth required)
- `test_cases_search_no_filter` — now returns 401 without token
- `test_screening_create_missing_body` — now returns 401 without token
- Add auth helper fixture to get valid tokens for tests that need them

```python
# Add fixture for authenticated requests
@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict:
    """Register a test user and return auth headers."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "name": "Test User",
    })
    # Login
    resp = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

Then update tests to use `auth_headers` where needed, and add new tests:

```python
def test_unauthenticated_returns_401(client: TestClient):
    """Protected endpoints require authentication."""
    r = client.get("/api/cases")
    assert r.status_code == 401

def test_auth_register_and_login(client: TestClient):
    r = client.post("/api/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "name": "New User",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "new@example.com"

    r = client.post("/api/auth/login", json={
        "email": "new@example.com",
        "password": "password123",
    })
    assert r.status_code == 200
    assert "access_token" in r.json()
```

- [ ] **Step 2: Run all tests**

Run: `cd C:/0_project/eia-prescreen && PYTHONPATH=. python -m pytest tests/ -v`

Fix any failures.

- [ ] **Step 3: Run frontend build**

Run: `cd C:/0_project/eia-prescreen/frontend && pnpm build`

Expected: Build succeeds (no backend changes affect frontend types).

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: update smoke tests for JWT auth and unified error responses"
```

---

## Verification Checklist

After all tasks, verify:

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `pnpm build` (in frontend/) — no TypeScript errors
- [ ] `POST /api/auth/register` creates user
- [ ] `POST /api/auth/login` returns access + refresh tokens
- [ ] `GET /api/cases` without token → 401
- [ ] `GET /api/cases` with valid token → 200
- [ ] `GET /health` without token → 200 (no auth required)
- [ ] Rate limit: 11th request within 1 minute to `/api/screening/{id}/interpret` → 429
- [ ] Invalid JSON body → `{"error": "validation_error", ...}` with 422
- [ ] Internal error → `{"error": "internal_error", ...}` with 500 (no stack trace)
- [ ] `docker-compose build` succeeds for both services
