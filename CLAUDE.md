# EIA Pre-Screen

## 제품 정의

EIA Pre-Screen은 사업 위치와 유형을 입력하면 공식·캐시 데이터와 사례 라이브러리를 바탕으로 환경영향평가 초기 단계의 입지 리스크와 우선 검토 항목을 근거와 함께 제시하는 사전검토 지원 도구다.

### 이 도구가 하는 것
- 입지 리스크 카드 (Critical/Major/Review/Info) + 근거 표시
- 법적 규제·인허가 자동 매칭
- 평가항목 우선순위 추천 (3~5개)
- 유사사례 라이브러리 (89건 큐레이션)
- 다중 부지 비교 (최대 3개 Side-by-side)
- 현장조사 체크리스트 자동 생성
- 데이터 가용성 대시보드
- LLM 리스크 종합 해석문
- RAG 기반 평가서 원문 검색 (103건, 6,103 청크)
- Draft Copilot: 7장 22섹션 초안 자동 생성 (사업유형별 중점 배지)
- 검토의견 예측 + 품질 체크 (9,996건 과거 데이터 기반)
- 1p 브리프 + 5~10p 환경현황 요약 보고서 PDF

### 이 도구가 하지 않는 것 (Non-Goals)
- 법적 판정 시스템이 아님
- 현장조사·전문 모델링·최종 평가자 판단을 대체하지 않음
- 평가서 전체 자동 작성 안 함
- HWP 직접 출력 안 함 (후속 확장)
- AERMOD 연계 자동화 안 함 (후속 확장)
- 주민의견/공람 workflow 안 함
- 원문 전체 NLP 자동 분석 안 함

## 기술 스택

- **프론트엔드**: Next.js 16+ (App Router) + TypeScript + Tailwind CSS + shadcn/ui
- **지도**: MapLibre GL JS (오픈소스, PostGIS GeoJSON 직접 연동)
- **백엔드**: FastAPI + SQLAlchemy + Alembic
- **DB**: PostgreSQL 16 + PostGIS 3.4
- **데이터 처리**: Python ETL + 캐시 스냅샷
- **RAG**: ChromaDB + sentence-transformers (jhgan/ko-sroberta-multitask)
- **LLM**: Google Gemini 2.5 Flash (기본, 무료) / OpenRouter DeepSeek V3 (대안) — llm_client.py 팩토리 패턴
- **공간 질의**: V-world WFS/연속지적도 GetFeature
- **출력**: PDF (ReportLab, Korean CID fonts)
- **모니터링**: Prometheus metrics (/metrics 엔드포인트)
- **인증**: JWT (HS256) + bcrypt + RBAC (admin/analyst/viewer)
- **인프라**: Docker Compose (5 서비스) + Nginx + Certbot
- **CI/CD**: GitHub Actions (ci.yml + deploy.yml)
- **패키지 매니저**: pnpm (프론트), pip + venv (백엔드)

## 프로젝트 구조

```
eia-prescreen/
├── frontend/                # Next.js App Router
│   ├── src/
│   │   ├── app/            # App Router pages (10개)
│   │   │   ├── screening/
│   │   │   │   ├── new/          # 스크리닝 생성
│   │   │   │   ├── compare/      # 부지 비교
│   │   │   │   └── [id]/         # screening_id 기반 라우팅
│   │   │   │       ├── dashboard/
│   │   │   │       ├── map/
│   │   │   │       ├── data-status/
│   │   │   │       ├── cases/
│   │   │   │       ├── draft/
│   │   │   │       └── rag/
│   │   │   └── admin/
│   │   │       └── rules/        # 관리자 규칙 관리
│   │   ├── components/     # React components
│   │   │   ├── ui/         # shadcn/ui 공통 (11개)
│   │   │   ├── risk/       # 리스크 (4개: Badge, Drawer, Banner, Freshness)
│   │   │   ├── charts/     # 차트 (4개: Donut, Bar, Pattern, Empty)
│   │   │   ├── feedback/   # 피드백 (3개: Empty, Error, Loading)
│   │   │   ├── layout/     # 레이아웃 (2개: Sidebar, ThemeToggle)
│   │   │   ├── map/        # MapLibre (1개: ScreeningMap)
│   │   │   └── admin/      # 관리자 (1개: LawStatusBanner)
│   │   ├── lib/            # 유틸, API 클라이언트
│   │   ├── hooks/          # 커스텀 훅
│   │   ├── types/          # TypeScript 타입
│   │   └── styles/         # 글로벌 스타일
│   ├── e2e/                # Playwright E2E 테스트
│   ├── public/
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── backend/                 # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/            # API 라우터
│   │   │   ├── screening.py    # 스크리닝 CRUD
│   │   │   ├── evaluation.py   # 리스크 평가 + 체크리스트
│   │   │   ├── draft.py        # Draft Copilot
│   │   │   ├── review.py       # 검토의견 예측 + 품질 체크
│   │   │   ├── data_status.py  # 데이터 가용성 대시보드
│   │   │   ├── cases.py        # 유사사례 + LLM 해석 + PDF 보고서
│   │   │   ├── compare.py      # 부지 비교
│   │   │   ├── patterns.py     # 과거 패턴 분석
│   │   │   ├── rag.py          # RAG 원문 검색
│   │   │   ├── auth.py         # 인증 (JWT + RBAC)
│   │   │   └── admin.py        # 관리자 (법령 모니터링 + 규칙 CRUD)
│   │   ├── core/           # 설정, 보안, 메트릭
│   │   ├── models/         # SQLAlchemy 모델
│   │   ├── schemas/        # Pydantic 스키마
│   │   ├── services/       # 비즈니스 로직
│   │   │   ├── screening_store.py    # 스크리닝 통합 조회 (DB/인메모리)
│   │   │   ├── risk_engine.py        # 77개 YAML 규칙 엔진
│   │   │   ├── regulation_matcher.py # 174개 규제 매칭
│   │   │   ├── data_fetcher.py       # 22개 커넥터 병렬 호출
│   │   │   ├── cache_manager.py      # 캐시/스냅샷 관리
│   │   │   ├── llm_interpreter.py    # LLM 해석문 (Gemini/OpenRouter)
│   │   │   ├── report_generator.py   # PDF 보고서 4종
│   │   │   ├── case_search.py        # 유사사례 검색
│   │   │   ├── checklist_generator.py # 체크리스트 생성
│   │   │   ├── draft_copilot.py      # 7장 22섹션 초안
│   │   │   ├── review_predictor.py   # 검토의견 예측
│   │   │   ├── quality_checker.py    # 품질 체크 33항목
│   │   │   ├── pattern_advisor.py    # 9,996건 패턴 분석
│   │   │   ├── report_rag.py         # RAG 원문 검색
│   │   │   └── legislation_monitor.py # 6개 법령 개정 감지
│   │   ├── rules/          # 룰 엔진 YAML
│   │   │   ├── v1/         # 19개 도메인 YAML 파일
│   │   │   └── schema.py
│   │   ├── connectors/     # 외부 API 커넥터 (26개 파일, 22개 DataFetcher 등록)
│   │   └── db/             # DB 마이그레이션
│   ├── tests/
│   ├── requirements.txt
│   └── alembic.ini
├── data/                    # 정적 데이터
│   ├── cases/              # 큐레이션 사례 JSON (89건)
│   ├── regulations/        # 규제 매핑 테이블 (174개)
│   ├── snapshots/          # API 캐시 스냅샷
│   ├── bulk/               # 벌크 협의 데이터 (9,996건)
│   └── reports/            # EIASS 환평 원문 (103건)
├── docs/                    # 문서
│   ├── API_REFERENCE.md
│   ├── DATA_SOURCES.md
│   ├── PRODUCT_SCOPE.md
│   ├── PRODUCTION_READINESS.md
│   ├── QA_REPORT.md
│   ├── FINAL_PLAN_V4.md
│   ├── DESIGN_QA_PLAN_V5.md
│   ├── ITERATION_PLAN.md
│   ├── PROJECT_AUDIT.md
│   ├── PROJECT_AUDIT_V2.md
│   ├── PROJECT_AUDIT_V3.md
│   ├── PROJECT_AUDIT_V4.md
│   ├── FULL_TYPE_TEST_34.md
│   └── FINAL_EXECUTION_PLAN.md
├── docker-compose.yml
├── .env.example
├── CLAUDE.md               # 이 파일
└── README.md
```

## 아키텍처 핵심 원칙

### Mock/Demo 데이터 전면 제거 (2026-03-29 완료)

모든 하드코딩된 데모 데이터가 제거되고 실 데이터 파이프라인으로 전환됨:

- **커넥터**: `fetch_demo()` 메서드 삭제, `_make_empty_result()` 로 대체 (데이터 미확보 시 graceful 빈 결과)
- **API 라우터**: `scenario` 파라미터 전면 제거, `screening_id` 기반 동적 데이터만 사용
- **프론트엔드**: `scenarioMap`, `SCENARIO_LOCATIONS`, `SCENARIO_PROJECT_TYPE` 등 시나리오 매핑 삭제
- **데이터**: `data/demo/` 폴더 삭제 (yangpyeong, sejong, boryeong 시나리오 데이터)
- **DEMO_MODE 의미 변경**: `true` = 커넥터 오류 무시 + 빈 데이터 반환 (기존: 하드코딩 데이터 반환)

### ScreeningStore 패턴

`backend/app/services/screening_store.py` — 스크리닝 데이터 통합 조회 서비스:
- DB(PostgreSQL) 또는 인메모리 저장소 투명하게 사용
- `create()`, `get()`, `list_all()`, `update_evaluation()` 메서드
- 모든 API 라우터(evaluation, draft, review, data_status)가 공통 사용
- 스크리닝 생성 시 `lng`, `lat` 좌표 저장 → 후속 평가 API에서 재사용

### 데이터 흐름

```
스크리닝 생성 (좌표+사업유형)
  → screening_store.create()
  → 커넥터 22개 병렬 호출 (data_fetcher.fetch_all)
  → 룰 엔진 평가 (risk_engine.evaluate)
  → 규제 매칭 (regulation_matcher.match)
  → 평가 결과 저장 (screening_store.update_evaluation)
  → Draft/Review/Report 등 후속 API에서 저장된 결과 재사용
```

## 외부 API (34종 승인, 16종 실연동)

| 계층 | API | 제공기관 | 상태 |
|------|-----|---------|------|
| A | 토지이용규제정보서비스 | 국토교통부 | 실연동 |
| A | V-world WFS/WMS | 국토지리정보원 | 실연동 |
| B | 에어코리아 대기오염정보 | 한국환경공단 | 실연동+캐시 |
| B | 수질측정정보 | 국립환경과학원 | 실연동+캐시 |
| B | 토양측정망 | 국립환경과학원 | 실연동+캐시 |
| B | 기상청 ASOS | 기상청 | 실연동+캐시 |
| B | 교통량 통계 | 한국건설기술연구원 | 실연동+캐시 |
| B | 생태자연도 | 국립생태원 | 실연동+캐시 |
| B | 환경영향평가 정보 (11종) | 국립환경과학원 | 실연동+캐시 |
| B | K-water 수문 운영 정보 | 한국수자원공사 | 실연동+캐시 |
| B | 조위관측 (KHOA) | 국립해양조사원 | 실연동+캐시 |
| B | 폐기물 통계 | 한국자원순환정보시스템 | 실연동+캐시 |
| C | 멸종위기종 (267종) | 국립생물자원관 | CSV (2024.12 기준) |
| C | EIASS 환경영향평가서 원문 | 환경영향평가정보지원시스템 | 크롤링 (103건) |

## 데이터 전략: 3계층

### A계층: 안정형 실시간
- 토지이용규제정보, 기초 조회 계열
- 실제 검증에서 안정적으로 확인된 소스만

### B계층: 불안정형 + 캐시
- 실시간 호출 시도 → 실패 시 마지막 성공 스냅샷으로 자동 전환
- 실패 시 `_make_empty_result()` 로 빈 ConnectorResult 반환 (에러 전파 안 함)
- 필수 메타: `fetched_at`, `snapshot_at`, `fallback_used`, `freshness`

### C계층: 수동 스냅샷 / 큐레이션
- 유사사례 89건 (LLM 태깅 + 수동 검수), 반복 보완 포인트, 주민 민감 이슈
- EIASS 원문 103건 (526 PDF, 16개 사업유형) → RAG 색인 6,103 청크
- 벌크 협의 데이터 9,996건 → 패턴 분석 + 검토의견 예측
- "자동 수집"보다 "정확한 태깅"이 더 중요

**핵심**: 실시간 = 고급 기능, 캐시 = 기본 동작 보장, 연결 실패 = 빈 데이터로 graceful 처리

## 사업유형 (환경영향평가법 시행령 별표3 기준 17개)

도시개발(urban_dev), 산업입지(industrial), 에너지개발(energy), 항만건설(port),
도로건설(road), 수자원개발(water_resource), 철도건설(railway), 공항건설(airport),
하천이용개발(river), 관광단지개발(tourism), 산지개발(mountain), 체육시설(sports),
폐기물처리시설(waste), 국방군사시설(military), 토석광물채취(mining), 매립간척(reclamation), 기타(etc)

## 룰 엔진

- **77개 규칙** (19개 도메인), JSON/YAML로 관리 (코드 하드코딩 금지)
- 점수 합산 하지 않음 → 설명 가능한 카드형 규칙
- 각 규칙 필드: `rule_id`, `rule_version`, `title`, `trigger_dataset`, `condition`, `severity`, `rationale`, `evidence`, `next_action`, `legal_basis`, `source_snapshot_date`, `confidence`, `human_review_required`
- 심각도: Critical / Major / Review / Info
- 조건 연산자: eq, ne, gt, gte, lt, lte, in, not_in, contains, intersects, within_buffer, exists, not_exists
- 필드 접근: 점(.) 표기법 (`ecology.eco_grade`, `land_use.zone_conflict`)
- 작성 안내서 개정에 따라 규칙도 버전 관리

## LLM 사용 원칙

- 사례 태깅 보조: 초벌 태깅은 LLM, 최종 검수는 사람
- 리스크 해석문: 룰 엔진 출력을 자연어 2~3문단으로 서술
- RAG 답변: 실제 평가서 원문 기반, 출처 표시 필수
- Draft Copilot: 템플릿 + RAG 참조 + LLM 보완 (3단계)
- **반드시** "이 해석은 AI 생성이며 참고용" 명시
- 근거 카드와 함께 표시, 단독 판정 금지

## 주요 수치

| 항목 | 수치 |
|------|------|
| pytest | 205개 수집 (190 passed, 15 skipped) |
| Playwright E2E | 67개 passed (14 스펙) |
| 환경영향평가서 원문 | 103건 (526 PDF, 6.3GB, 16개 사업유형) |
| RAG 청크 | 6,103개 |
| RAG 검색 품질 | 90.3/100 |
| 벌크 협의 데이터 | 9,996건 |
| 실연동 API | 16종 (34종 승인) |
| 규칙 YAML | 77개 (19개 도메인) |
| 유사사례 | 89건 (18개 유형) |
| 규제 매핑 | 174개 (3개 파일) |
| 커넥터 파일 | 26개 (22개 DataFetcher 등록) |
| 서비스 레이어 | 15개 |
| 백엔드 엔드포인트 | 41개 (11 라우터) |
| 프론트엔드 페이지 | 10개 (11 빌드 라우트) |
| 프론트엔드 컴포넌트 | 27개 |
| API 호출 함수 | 34개 |
| 풀테스트 (17유형×2건) | 340 API 호출, 100% 성공 |
| 초안 템플릿 | 7장 22섹션 |
| 별표1 커버리지 | 70% 완전, 30% 부분, 0% 미보유 |

## E2E 테스트 규칙

### API 스텁 인프라
- **스텁 데이터**: `frontend/e2e/fixtures/api-stubs.ts` — 10개 카테고리 (Screening, Evaluation, Cases, Draft, DataStatus, Patterns, Review, Compare, LLM, RAG) + Empty 변형
- **모킹 헬퍼**: `frontend/e2e/helpers/mock-api.ts` — 3개 함수:
  - `setupApiMocks(page)` — 정상 응답 (기본)
  - `setupErrorMocks(page)` — 500 에러 응답 (ErrorState 테스트)
  - `setupEmptyMocks(page)` — 빈 데이터 응답 (EmptyState 테스트)
- 모든 E2E 테스트는 `setupApiMocks()`로 외부 API를 고정하여 Flakiness 제거
- `page.route()`로 백엔드 API 인터셉트 (프론트엔드 → 백엔드 호출만 모킹)

### 자동 검증
- 프론트엔드 파일 수정 후 반드시 확인: `cd frontend && pnpm build && pnpm lint`
- E2E 실행: `cd frontend && npx playwright test --reporter=list`
- pytest 실행: `cd eia-prescreen && python -m pytest tests/ backend/tests/ -v`

## 코딩 컨벤션

### 프론트엔드
- 컴포넌트: PascalCase, 기능 단위 폴더 구조
- 스타일: Tailwind 유틸리티 우선, 커스텀 CSS 최소화
- 상태관리: React Query (서버 상태) + Zustand (클라이언트 상태)
- 지도: MapLibre GL JS 직접 사용, react-map-gl 래퍼 사용 가능
- 라우팅: screening_id 기반 동적 라우팅 (scenario 파라미터 사용 금지)

### 백엔드
- FastAPI 라우터: 기능별 분리
- 서비스 레이어: 비즈니스 로직은 services/에 집중
- 데이터 조회: screening_store를 통한 중앙화 접근 (API 라우터에서 직접 DB 쿼리 금지)
- DB 모델: SQLAlchemy ORM, PostGIS geometry 타입 활용
- 외부 API: connectors/ 폴더에 어댑터 패턴으로 구현
- 커넥터 실패 처리: `_make_empty_result()` 반환 (exception 전파 금지)
- 캐시: Redis 또는 파일 기반 스냅샷 (현재 파일 기반)
- 하드코딩 데이터 금지: 모든 데이터는 커넥터/DB/파일에서 동적 로드

### 공통
- 타입 안전성 최우선 (TypeScript strict, Python type hints)
- 에러 처리: 사용자에게 의미 있는 메시지 반환
- 로깅: 구조화된 로그 (JSON format)
- 환경변수: .env 파일, 시크릿은 절대 커밋하지 않음

## 개발 Phase 및 완료 현황

### Phase 0~4: 완료 ✅

| Phase | 내용 | 상태 |
|-------|------|------|
| 0 | Product Freeze (PRODUCT_SCOPE.md, non-goal 확정) | ✅ |
| 1 | Data Stabilization (커넥터 14개, 캐시, 규제 DB) | ✅ |
| 2 | Risk Engine + 규제 매칭 (64규칙, 175매핑, 체크리스트) | ✅ |
| 3 | Case Library + LLM (84사례, 해석문, PDF 4종) | ✅ |
| 4 | 부지 비교 + 데이터 대시보드 | ✅ |

### Step 1~21: 완료 ✅ (docs/FINAL_PLAN_V4.md + DESIGN_QA_PLAN_V5.md)

| Step | 작업 | 상태 |
|------|------|------|
| 1~6 | 유사사례 89건, 규제 174개, 규칙 77개, 커넥터 26개, 통합검증 | ✅ |
| 7~9 | 벌크 9,996건 수집, 패턴 분석, 서비스 통합 | ✅ |
| 10~11 | Draft Copilot, 검토의견 예측 + 품질 체크 | ✅ |
| 12~14 | EIASS 크롤링 103건, RAG 6,103 청크 | ✅ |
| 15 | RAG 품질 테스트 (90.3/100) | ✅ |
| 16~17 | 로컬 E2E, 문서 업데이트 | ✅ |
| 18~19 | UI/UX 디자인 + Playwright 41개 E2E | ✅ |
| 20~21 | QA 검증 + 재검증 (docs/QA_REPORT.md) | ✅ |

### Mock 데이터 전면 제거: 완료 ✅

- 커넥터 17개 파일: `_DEMO_DATA` + `fetch_demo()` 삭제
- API 라우터 4개: scenario 매핑/분기 삭제, screening_store 기반으로 전환
- 스키마 4개: scenario 필드 삭제
- 프론트엔드 10개 파일: scenario 매핑/쿼리파라미터 삭제
- `data/demo/` 폴더 삭제
- 테스트 5개 파일: demo 의존 테스트를 인라인 픽스처 기반으로 전환

### 실무 확장: 완료 ✅ (docs/FINAL_EXECUTION_PLAN.md)

| Phase | 범위 | 내용 |
|-------|------|------|
| A | A-1~A-4 | 기반 정비 (문서, Docker, 인증, CI/CD) | ✅ |
| B | B-1~B-6 | 데이터 완결성 (별표1 커버리지 55%→70%) | ✅ |
| C | C-1~C-2 | 법령 최신성 (자동 감지 + 규칙 관리 UI) | ✅ |
| D | D-1~D-3 | 보고서·UI 전문화 (초안, 지도, PDF) | ✅ |

## 운영 준비 현황

현재 상태: **MVP 완료 (Phase A~D 전체 완료)**

### 완료된 운영 과제

| 항목 | 상태 |
|------|------|
| JWT 인증·인가 (RBAC 3역할) | ✅ Phase A (BaseHTTPMiddleware→순수ASGI 전환으로 수정 완료, 2026-04-01) |
| Dockerfile (backend + frontend, non-root, healthcheck) | ✅ Phase A |
| Rate Limiting (slowapi, 4단계) | ✅ Phase A |
| 글로벌 에러 핸들러 (3종 한국어) | ✅ Phase A |
| API 로깅 미들웨어 (순수 ASGI, JSON 구조화) | ✅ Phase A |
| CI/CD (ci.yml 5 jobs) | ✅ Phase A |
| 프론트엔드 에러 바운더리 | ✅ Phase A |

### 잔여 운영 과제

| 우선순위 | 항목 | 비고 |
|---------|------|------|
| 🟡 High | deploy.yml 실 배포 구현 | 현재 플레이스홀더 |
| 🟡 High | HTTPS 활성화 (nginx TLS) | 주석 처리 상태, 스크립트 준비됨 |
| 🟡 High | DB 커넥션 풀링 최적화 | — |
| 🟢 Low | .dockerignore 추가 | 빌드 컨텍스트 최적화 |
| 🟢 Low | 법령 모니터링 자동 스케줄링 | 현재 수동 트리거만 |
| 🟢 Low | react-map-gl, zustand 미사용 패키지 정리 | — |
| 🟢 Low | RAG/ML 패키지 버전 고정 | >= → == |

## 참고 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| API 레퍼런스 | docs/API_REFERENCE.md | 41개 엔드포인트 상세 |
| 데이터 소스 | docs/DATA_SOURCES.md | 26개 커넥터 + EIASS RAG |
| 운영 준비 | docs/PRODUCTION_READINESS.md | 보완 항목 + 로드맵 |
| QA 보고서 | docs/QA_REPORT.md | Playwright 67/67, pytest 190/205 |
| 제품 범위 | docs/PRODUCT_SCOPE.md | 제품 정의 + Non-goals |
| 실행 계획 | docs/FINAL_PLAN_V4.md | Step 15~20 상세 |
| 디자인+QA | docs/DESIGN_QA_PLAN_V5.md | Step 18~23 (디자인, E2E, QA) |
| 이터레이션 | docs/ITERATION_PLAN.md | UI/UX 이터레이션 |
| 전수조사 V1 | docs/PROJECT_AUDIT.md | 프로젝트 전수조사 (Phase A~D 이전) |
| 전수조사 V2 | docs/PROJECT_AUDIT_V2.md | 프로젝트 전수조사 (Phase A~D 완료 기준) |
| 전수조사 V3 | docs/PROJECT_AUDIT_V3.md | 프로젝트 전수조사 (API 실연동 + JWT 수정 완료 기준) |
| 전수조사 V4 | docs/PROJECT_AUDIT_V4.md | 프로젝트 전수조사 (Gemini + 풀테스트 기준, 최신) |
| 풀테스트 결과 | docs/FULL_TYPE_TEST_34.md | 17유형 34건 풀테스트 결과 |
| 실행 계획 | docs/FINAL_EXECUTION_PLAN.md | 15 Step 실무 확장 계획 |

## 실무 확장 진행 상태

| Phase | 범위 | 상태 |
|-------|------|------|
| A 기반 정비 | A-1~A-4 | ✅ 완료 |
| B 데이터 완결성 | B-1~B-6 | ✅ 완료 |
| C 법령 최신성 | C-1~C-2 | ✅ 완료 |
| D 보고서·UI | D-1~D-3 | ✅ 완료 |

**전체 Phase A~D + Gemini 전환 + 풀테스트 완료 (2026-04-03)**

### 34건 풀테스트 결과 (2026-04-03, 17유형 × 2건)

| 검증 기준 | 결과 |
|-----------|------|
| 34건 리스크 1건+ | **PASS** (최소 3건~최대 12건) |
| 34건 규제 1건+ | **PASS** (최소 1건~최대 19건) |
| 초안 22섹션/7장 | **PASS** (34/34) |
| 품질 80점+ | **PASS** (93~100점) |
| 커넥터 20개+ | **PASS** (20~22/22) |
| 검토의견 유형별 차별화 | **PASS** (5개 패턴 그룹) |

**발견 이슈**: mining/forest 유사사례 0건 (라이브러리 미보유), reclamation 1건 (희소)

### LLM 프로바이더 현황 (V4)
- 기본: Google Gemini 2.5 Flash (무료, llm_client.py 팩토리)
- 대안: OpenRouter DeepSeek V3 (LLM_PROVIDER 환경변수 전환)

실행 문서: docs/FINAL_EXECUTION_PLAN.md
풀테스트: docs/FULL_TYPE_TEST_34.md
전수조사: docs/PROJECT_AUDIT_V4.md (최신)
