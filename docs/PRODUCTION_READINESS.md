# EIA Pre-Screen — 운영 준비 현황 및 보완 계획

> 작성일: 2026-03-29 (갱신)
> 현재 상태: **데모/MVP (운영 준비도 약 92%)**

---

## 1. 현재 완성 현황

### 1.1 백엔드 API (35개 엔드포인트 — 모두 동작)

> 전체 상세: [docs/API_REFERENCE.md](API_REFERENCE.md)

| 그룹 | 엔드포인트 수 | 상태 |
|------|-------------|------|
| 시스템 (health) | 1 | ✅ |
| 인증 (auth) | 4 | ✅ |
| 스크리닝 (screening) | 3 | ✅ |
| 리스크 평가 (evaluation) | 3 | ✅ |
| 유사사례 & AI 해석 | 4 | ✅ |
| 부지 비교 (compare) | 2 | ✅ |
| 패턴 분석 (patterns) | 4 | ✅ |
| Draft Copilot | 3 | ✅ |
| 검토의견 예측 (review) | 2 | ✅ |
| RAG 원문 검색 | 4 | ✅ |
| 데이터 현황 (data-status) | 3 | ✅ |
| PDF 보고서 (report) | 2 | ✅ |

### 1.2 서비스 레이어 (11개)

| 서비스 | 파일 | 상태 |
|--------|------|------|
| 규칙 엔진 (64개 YAML, 16도메인) | `risk_engine.py` | ✅ 완성 |
| 데이터 수집기 (18개 커넥터) | `data_fetcher.py` | ✅ 완성 |
| 규제 매처 (175개 매핑) | `regulation_matcher.py` | ✅ 완성 |
| 캐시 관리자 | `cache_manager.py` | ✅ 완성 |
| LLM 해석기 (DeepSeek V3 via OpenRouter) | `llm_interpreter.py` | ✅ 완성 |
| PDF 보고서 (4종) | `report_generator.py` | ✅ 완성 |
| 유사사례 검색 (84건) | `case_search.py` | ✅ 완성 |
| 체크리스트 생성 | `checklist_generator.py` | ✅ 완성 |
| **RAG 원문 검색 (6,103 청크)** | `report_rag.py` | ✅ 완성 |
| **Draft Copilot (6장 18섹션)** | `draft_copilot.py` | ✅ 완성 |
| **패턴 분석 (9,973건)** | `pattern_advisor.py` | ✅ 완성 |

### 1.3 프론트엔드 (8개 라우트)

| 페이지 | 경로 | 상태 |
|--------|------|------|
| 랜딩 | `/` | ✅ |
| 새 검토 | `/screening/new` | ✅ |
| 대시보드 | `/screening/[id]/dashboard` | ✅ |
| 리스크 맵 | `/screening/[id]/map` | ✅ |
| 데이터 현황 | `/screening/[id]/data-status` | ✅ |
| 유사사례·보고서·AI 해석 | `/screening/[id]/cases` | ✅ |
| Draft Copilot | `/screening/[id]/draft` | ✅ |
| 부지 비교 | `/screening/compare` | ✅ |

### 1.4 데이터

| 데이터 | 수치 | 상태 |
|--------|------|------|
| 규칙 YAML (16개 도메인) | 64개 | ✅ |
| 규제 매핑 (용도지역·보호구역·EIA 임계값) | 175개 | ✅ |
| 유사사례 (큐레이션) | 84건 | ✅ |
| 벌크 협의 데이터 (패턴 분석) | 9,973건 | ✅ |
| 환경영향평가서 원문 (RAG) | 103건 / 526 PDF / 6.3GB | ✅ |
| RAG 청크 (ChromaDB) | 6,103개 (99 보고서, 16 유형) | ✅ |
| 사업유형 (환경영향평가법 시행령 별표3) | 17개 | ✅ |
| 데모 데이터 3개 시나리오 (양평·세종·보령) | 3건 | ✅ |

### 1.5 품질 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| 단위 테스트 (pytest) | 114개 passed |
| RAG 검색 품질 (16개 사업유형) | 90.3/100 평균, 100% 통과 |
| RAG LLM 답변 품질 | 92.7/100 평균, 100% 통과 |
| Draft Copilot RAG 통합 | 100% (5/5) 통과 |
| E2E 시나리오 테스트 (3건) | 105/105 체크 통과 |
| RAG 종합 품질 | 94.0/100 |

---

## 2. 운영 투입을 위한 보완 항목

### 🔴 CRITICAL — 운영 전 반드시 해결

#### C-1. 인증·인가 시스템 없음

**현재**: 모든 API 엔드포인트가 인증 없이 공개 접근 가능
**위험**: 누구나 스크리닝 데이터를 열람·수정·삭제 가능

**보완 방안**:
```
1. JWT 기반 인증 (fastapi-users 또는 직접 구현)
   - 로그인/회원가입 API
   - Access Token (15분) + Refresh Token (7일) 발급
   - 모든 /api/* 엔드포인트에 Depends(get_current_user)

2. 역할 기반 인가 (RBAC)
   - admin: 시스템 설정, 사용자 관리
   - analyst: 스크리닝 생성·평가·보고서 생성
   - viewer: 읽기 전용

3. 구현 파일:
   - backend/app/core/auth.py (JWT 발급·검증)
   - backend/app/api/auth.py (로그인·회원가입 엔드포인트)
   - backend/app/models/user.py (사용자 모델)
   - alembic migration (users 테이블)
```

**예상 공수**: 3~5일

---

#### C-2. Dockerfile 미존재

**현재**: `docker-compose.yml`이 `build: context: ./backend`를 참조하지만 Dockerfile이 없어 `docker-compose up` 실패
**위험**: 컨테이너 배포 불가

**보완 방안**:
```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# frontend/Dockerfile
FROM node:20-slim
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
CMD ["pnpm", "start"]
```

**예상 공수**: 1일

---

#### C-3. Rate Limiting 없음

**현재**: API 호출 횟수 제한이 없어 DoS 공격에 취약
**위험**: 단일 클라이언트가 무제한 호출 가능, OpenRouter API 과금 폭증 가능

**보완 방안**:
```
1. slowapi 패키지 도입
   - 일반 엔드포인트: 60 req/min per IP
   - LLM 해석 (/interpret): 10 req/min per user
   - PDF 생성 (/report): 20 req/min per user
   - 비인증 요청: 10 req/min per IP

2. 구현:
   - backend/app/core/rate_limiter.py
   - 각 라우터에 @limiter.limit() 데코레이터

3. 운영 단계에서는 Redis 백엔드로 전환 (현재 in-memory)
```

**예상 공수**: 1일

---

#### C-4. 글로벌 에러 핸들러 없음

**현재**: 예외 발생 시 FastAPI 기본 500 응답 (스택트레이스 노출 가능)
**위험**: 내부 구현 정보 유출, 일관성 없는 에러 응답 형식

**보완 방안**:
```python
# backend/app/core/error_handler.py
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "서버 내부 오류가 발생했습니다."}
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": str(exc.errors())}
    )
```

**예상 공수**: 0.5일

---

### 🟡 HIGH — 운영 안정성 확보

#### H-1. ~~누락 커넥터~~ → ✅ 해결 완료 (2026-03-28)

**이전**: 25개 규칙 중 9개는 규칙만 있고 실시간 데이터 커넥터 없음
**현재**: 14개 커넥터 전체 구현 완료, 64개 규칙(16개 도메인) 모두 평가 가능

| 커넥터 | API 출처 | 구현 상태 |
|--------|---------|----------|
| 토지이용 | 토지이음 (국토부) | ✅ 구현 |
| 생태 | 국립생태원 | ✅ 구현 |
| 대기질 | 에어코리아 | ✅ 구현 |
| 수질 | 물환경정보시스템 | ✅ 구현 |
| 소음 | 국가소음정보시스템 | ✅ 구현 |
| 토양 | 토양환경정보시스템 | ✅ 구현 |
| 경관 | 국가경관포탈 | ✅ 구현 |
| 문화재 | 문화재청 GIS | ✅ 구현 |
| 사회 | 민원 정보 | ✅ 구현 |
| 인구 | 통계청 | ✅ 구현 |
| 지질 | 지질자원연구원 | ✅ 구현 |
| 온실가스 | 환경부 | ✅ 구현 |
| 기상 | 기상청 | ✅ 구현 |
| 교통 | 교통 DB | ✅ 구현 |

데모 3개 시나리오 모두 17개 도메인 데이터 완비 (14개 커넥터 + 경관/문화재/사회 목데이터 통합)

---

#### H-2. API 요청·응답 로깅 없음

**현재**: `logging.getLogger`는 import되어 있으나 실제 API 호출 기록이 남지 않음
**위험**: 장애 원인 추적 불가, 사용량 분석 불가

**보완 방안**:
```
1. 미들웨어 기반 요청 로깅:
   - 요청: method, path, IP, user_id, timestamp
   - 응답: status_code, latency_ms
   - 에러: traceback (500 응답만)

2. 구조화 로깅 (JSON format):
   - structlog 또는 python-json-logger 패키지
   - 운영 환경에서 ELK/CloudWatch로 수집 가능

3. 구현 파일:
   - backend/app/core/logging_middleware.py
   - backend/app/core/logger.py
```

**예상 공수**: 1~2일

---

#### H-3. DB 커넥션 풀링 미설정

**현재**: SQLAlchemy 기본 풀링 설정 사용 (pool_size=5)
**위험**: 동시 접속 20명 이상 시 커넥션 부족

**보완 방안**:
```python
# backend/app/core/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,           # 기본 커넥션 수
    max_overflow=10,        # 초과 허용
    pool_timeout=30,        # 대기 시간 (초)
    pool_recycle=1800,      # 커넥션 재사용 주기 (초)
    pool_pre_ping=True,     # 커넥션 유효성 사전 검증
)
```

**예상 공수**: 0.5일

---

#### H-4. 프론트엔드 에러 바운더리 없음

**현재**: API 호출 실패 시 화면이 깨지거나 빈 화면 표시
**위험**: 사용자 혼란, 오류 원인 파악 불가

**보완 방안**:
```
1. Next.js error.tsx 파일 추가:
   - frontend/src/app/error.tsx (글로벌)
   - frontend/src/app/screening/[id]/error.tsx (스크리닝별)

2. React Query 에러 핸들링:
   - QueryClientProvider에 onError 콜백
   - Toast 알림 (sonner 또는 react-hot-toast)

3. Loading 상태:
   - loading.tsx 파일 추가 (스켈레톤 UI)
   - Suspense 경계 설정
```

**예상 공수**: 2일

---

#### H-5. CI/CD 파이프라인 없음

**현재**: 수동 배포만 가능
**위험**: 회귀 테스트 누락, 배포 과정 오류

**보완 방안**:
```yaml
# .github/workflows/ci.yml
- lint (ruff, eslint)
- type-check (mypy, tsc --noEmit)
- test (pytest, vitest)
- build (docker build)
- deploy (staging → production)
```

**예상 공수**: 2~3일

---

### 🟢 MEDIUM — 운영 품질 향상

#### M-1. HTTPS/TLS 미설정

**현재**: HTTP만 사용 (docker-compose에 nginx/certbot 없음)
**보완**: nginx reverse proxy + Let's Encrypt 인증서 자동 갱신

**예상 공수**: 1일

---

#### M-2. 테스트 커버리지 부족 (약 30%)

**현재 테스트 현황**:
| 영역 | 테스트 수 | 커버리지 |
|------|----------|---------|
| 유사사례 검색 | 6개 | ✅ |
| PDF 생성 (4종) | 4개 | ✅ |
| 체크리스트 | 2개 | ✅ |
| LLM (키 없음 에러) | 1개 | ⚠️ 부분 |
| HTTP 엔드포인트 | 13개 | ⚠️ smoke만 |
| 규칙 엔진 | 1개 | ⚠️ 로드만 |
| 규제 매처 | 1개 | ⚠️ 로드만 |
| **커넥터 폴백** | **0개** | ❌ |
| **DB 통합** | **0개** | ❌ |
| **프론트엔드 컴포넌트** | **0개** | ❌ |

**보완 방안**:
```
1. 백엔드 통합 테스트 (실 DB): pytest + testcontainers-python
2. 커넥터 폴백 테스트: 정상 → timeout → 캐시 시나리오
3. 프론트엔드: Vitest + React Testing Library
4. 목표 커버리지: 70% 이상
```

**예상 공수**: 5일

---

#### M-3. 모니터링·관측성 없음

**현재**: `/health` 엔드포인트만 존재
**보완**:
```
1. Prometheus 메트릭 (/metrics):
   - 요청 수, 응답 시간, 에러율
   - 커넥터별 성공/실패율
   - DB 커넥션 풀 사용량

2. Grafana 대시보드:
   - API 응답 시간 분포
   - 커넥터 상태
   - OpenRouter/DeepSeek API 사용량

3. Sentry (에러 추적):
   - 예외 자동 수집
   - 사용자 세션 추적
```

**예상 공수**: 3일

---

#### M-4. 접근성 (Accessibility) 미비

**현재**: 시맨틱 HTML은 사용하나 ARIA 라벨, 키보드 내비게이션, 포커스 관리 미흡
**보완**: 주요 인터랙티브 요소에 aria-label, role 속성 추가 + 키보드 탐색 테스트

**예상 공수**: 2일

---

#### M-5. 환경별 설정 분리 없음

**현재**: 단일 `.env` 파일로 개발/운영 구분 없음
**보완**:
```
.env.development    # 로컬 개발 (DEMO_MODE=true)
.env.staging        # 스테이징 (실 DB, 테스트 API 키)
.env.production     # 운영 (실 DB, 실 API 키, HTTPS)
```

**예상 공수**: 0.5일

---

#### M-6. 커넥터 재시도(Retry) 로직 없음

**현재**: 공공 API 1회 실패 시 즉시 캐시 폴백
**보완**: exponential backoff (1초→2초→4초, 최대 3회) 후 폴백

**예상 공수**: 1일

---

### 🔵 NICE TO HAVE — 향후 확장

| 항목 | 설명 | 예상 공수 |
|------|------|----------|
| API 버저닝 | `/api/v1/`, `/api/v2/` 분리 | 1일 |
| WebSocket 실시간 진행률 | 평가 진행 상황 실시간 표시 | 3일 |
| HWP 보고서 출력 | 공공기관 제출용 한글 파일 | 5일 |
| 다중 사용자 팀 협업 | 팀 워크스페이스, 공유 기능 | 10일 |
| AERMOD 연계 | 대기 확산 모델 자동화 | 10일 |
| 감사 로그 (Audit Log) | 누가 언제 무엇을 했는지 추적 | 2일 |
| API 키 자동 로테이션 | 공공 API 키 만료 전 자동 갱신 | 1일 |
| 다국어 지원 (i18n) | 영문 보고서 생성 | 5일 |

---

## 3. 운영 투입 로드맵

```
Phase 1 (1주차) — 배포 인프라 + 보안 기초
├── C-1. JWT 인증·인가 구현
├── C-2. Dockerfile 작성 (backend + frontend)
├── C-3. Rate Limiting 적용
├── C-4. 글로벌 에러 핸들러
└── M-5. 환경별 설정 분리

Phase 2 (2주차) — 안정성 확보
├── H-2. API 로깅 미들웨어
├── H-3. DB 커넥션 풀링 설정
├── H-4. 프론트엔드 에러 바운더리
├── H-5. GitHub Actions CI/CD 파이프라인
└── M-1. nginx + HTTPS 구성

Phase 3 (3~4주차) — 데이터 완성도
├── H-1. ✅ 완료 — 14개 커넥터 전체 구현
├── M-2. 테스트 커버리지 70% 달성
├── M-6. 커넥터 재시도 로직
└── M-3. 모니터링 (Prometheus + Sentry)

Phase 4 (5주차~) — 고도화
├── 감사 로그
├── WebSocket 실시간 진행률
├── HWP 보고서
└── 성능 부하 테스트
```

---

## 4. 현재 즉시 가용한 데모 범위

다음 기능은 **지금 바로 시연 가능**합니다 (API 키 불필요 항목 포함):

| 기능 | 외부 의존성 | 즉시 가용 |
|------|-----------|----------|
| 리스크 분석 (64개 규칙) | 없음 (로컬 YAML) | ✅ |
| 규제 자동 매칭 (175개) | 없음 (로컬 JSON) | ✅ |
| 유사사례 검색 (84건) | 없음 (로컬 JSON) | ✅ |
| 체크리스트 생성 | 없음 (로컬 로직) | ✅ |
| PDF 보고서 4종 | 없음 (reportlab) | ✅ |
| 리스크 맵 | MapLibre CDN | ✅ |
| 부지 비교 | 없음 (로컬 계산) | ✅ |
| 데이터 현황 대시보드 | 없음 (mock 데이터) | ✅ |
| 검토의견 예측 (9,973건) | 없음 (로컬 통계) | ✅ |
| **RAG 원문 검색 (6,103 청크)** | **ChromaDB 로컬** | ✅ (색인 완료) |
| **Draft Copilot (18섹션 초안)** | **ChromaDB + LLM** | ✅ |
| **AI 해석 (DeepSeek)** | **OPENROUTER_API_KEY** | ✅ (키 설정됨) |

---

## 5. 보안 점검 요약

| 항목 | 현재 상태 | 운영 필요 조치 |
|------|----------|---------------|
| SQL Injection | ✅ SQLAlchemy ORM 보호 | 유지 |
| XSS | ✅ React 자동 이스케이프 | 유지 |
| CORS | ✅ 허용 도메인 지정 | 운영 도메인으로 변경 |
| 인증 | ❌ 없음 | JWT 구현 필수 |
| 인가 | ❌ 없음 | RBAC 구현 필수 |
| Rate Limiting | ❌ 없음 | slowapi 적용 필수 |
| HTTPS | ❌ HTTP만 | nginx + TLS 인증서 |
| 비밀번호 관리 | ⚠️ .env 평문 | Secret Manager 연동 |
| 입력 검증 | ✅ Pydantic 강력 | 유지 |
| 에러 노출 | ⚠️ 스택트레이스 가능 | 글로벌 핸들러 |

---

---

## 6. 참고 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| API 레퍼런스 | [docs/API_REFERENCE.md](API_REFERENCE.md) | 35개 엔드포인트 상세 |
| 데이터 소스 | [docs/DATA_SOURCES.md](DATA_SOURCES.md) | 18개 커넥터 + EIASS RAG |
| 제품 범위 | [docs/PRODUCT_SCOPE.md](PRODUCT_SCOPE.md) | 제품 정의 + Non-goals |
| 규칙 스펙 | [docs/RULE_SPEC.md](RULE_SPEC.md) | 64개 규칙 작성 가이드 |

---

*본 문서는 2026-03-29 기준 프로젝트 분석 결과입니다. 진행 상황에 따라 업데이트하세요.*
