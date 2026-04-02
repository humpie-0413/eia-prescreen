# EIA Pre-Screen 프로젝트 전수조사 보고서 V4

> 조사일: 2026-04-03 | Gemini LLM 전환 + 34건 풀테스트 완료 기준 | 조사 도구: Claude Code (Opus 4.6) × 5 병렬 에이전트

---

## 1. 프로젝트 개요

### 목적
사업 위치와 유형을 입력하면 공식·캐시 데이터와 사례 라이브러리를 바탕으로 환경영향평가 초기 단계의 입지 리스크와 우선 검토 항목을 근거와 함께 제시하는 **사전검토 지원 도구**.

### 대상 사용자
환경영향평가 대행업체 실무자, 사업 기획 담당자, 환경부 협의 담당자

### 핵심 기능 (12개)
1. 입지 리스크 카드 (Critical/Major/Review/Info) + 근거 표시
2. 법적 규제·인허가 자동 매칭 (174개)
3. 평가항목 우선순위 추천
4. 유사사례 라이브러리 (89건 큐레이션)
5. 다중 부지 비교 (최대 3개 Side-by-side)
6. 현장조사 체크리스트 자동 생성
7. 데이터 가용성 대시보드
8. LLM 리스크 종합 해석문 (Gemini 2.5 Flash)
9. RAG 기반 평가서 원문 검색 (103건, 6,103 청크)
10. Draft Copilot: 7장 22섹션 초안 자동 생성 (사업유형별 중점 배지)
11. 검토의견 예측 + 품질 체크 (9,996건 과거 데이터)
12. PDF 보고서 생성 (1p 브리프 / 5~10p 요약 / 체크리스트 / 비교)

### 기술 스택
| 계층 | 기술 |
|------|------|
| 프론트엔드 | Next.js 16.2.1 (App Router) + React 19 + TypeScript 5 + Tailwind v4 + shadcn/ui |
| 지도 | MapLibre GL JS 5.21 (CARTO Positron) |
| 백엔드 | FastAPI 0.115 + SQLAlchemy 2.0 + Alembic |
| DB | PostgreSQL 16 + PostGIS 3.4 |
| RAG | ChromaDB + sentence-transformers (jhgan/ko-sroberta-multitask) |
| LLM | Google Gemini 2.5 Flash (기본, 무료) / OpenRouter DeepSeek V3 (대안) |
| PDF | ReportLab (Korean CID fonts) |
| 인증 | JWT (HS256) + bcrypt + RBAC (admin/analyst/viewer) |
| 모니터링 | Prometheus metrics (9개) + JSON 구조화 로깅 |
| 인프라 | Docker Compose (5 서비스) + Nginx + Certbot |
| CI/CD | GitHub Actions (ci.yml 5 jobs + deploy.yml) |

---

## 2. 아키텍처 현황

### 백엔드 서비스 (15개)

| # | 파일 | 주요 클래스/함수 |
|---|------|----------------|
| 1 | risk_engine.py | RiskEngine |
| 2 | regulation_matcher.py | RegulationMatcher |
| 3 | data_fetcher.py | DataFetcher (22개 커넥터 오케스트레이션) |
| 4 | screening_store.py | create(), get(), list_all(), update_evaluation() |
| 5 | case_search.py | CaseSearchService |
| 6 | llm_interpreter.py | LLMInterpreter |
| 7 | report_generator.py | ReportGenerator (PDF 4종) |
| 8 | checklist_generator.py | ChecklistGenerator |
| 9 | draft_copilot.py | DraftCopilot (7장 22섹션) |
| 10 | review_predictor.py | ReviewPredictor |
| 11 | quality_checker.py | QualityChecker |
| 12 | pattern_advisor.py | PatternAdvisor (9,996건) |
| 13 | report_rag.py | ReportRAG (6,103 청크) |
| 14 | cache_manager.py | CacheManager |
| 15 | legislation_monitor.py | LegislationMonitor (6개 법률) |

### 코어 모듈 (V4 신규: llm_client.py)

| 파일 | 역할 |
|------|------|
| config.py | Settings (31개 환경변수) |
| security.py | JWT + bcrypt + RBAC |
| llm_client.py | LLM 프로바이더 팩토리 (Gemini/OpenRouter) |
| logging_middleware.py | 순수 ASGI 요청 로깅 |
| metrics.py | Prometheus 메트릭 수집 |

### API 엔드포인트 (41개)

| 라우터 | 엔드포인트 수 | 인증 |
|--------|-------------|------|
| auth.py | 4 (register, login, refresh, me) | Public |
| screening.py | 3 (create, get, list) | ⚠️ 임시 해제 |
| evaluation.py | 3 (evaluate, regulations, checklist) | ⚠️ 임시 해제 |
| cases.py | 5 (search, get, similar, interpret, report) | ⚠️ 임시 해제 |
| draft.py | 3 (full, section, template) | Mixed |
| review.py | 2 (predict, quality-check) | ⚠️ 임시 해제 |
| compare.py | 2 (compare, report) | ⚠️ 임시 해제 |
| data_status.py | 3 (connectors, screening, status) | Public |
| patterns.py | 4 (summary, type, predict, suggested) | Public |
| rag.py | 4 (query, draft-assist, stats, index) | ⚠️ 임시 해제 |
| admin.py | 6 (law-status, check, acknowledge, rules CRUD) | ⚠️ 임시 해제 |
| main.py | 2 (health, metrics) | Public |
| **합계** | **41** | ⚠️ JWT 임시 해제 상태 (테스트용) |

### 커넥터 (26개 파일, 22개 DataFetcher 등록)

**DataFetcher 등록 22개:**
LandUse, Ecology, AirQuality, WaterQuality, Soil, Noise, Population, ProjectArea, EiaInfo, Marine, Geology, Greenhouse, Weather, Traffic, Odor, Radio, Industry, Facilities, Species, Hydrology, Ocean, WasteData

**미등록 4개:** VworldConnector (LandUse 내부 사용), CulturalConnector, LandscapeConnector, LegislationConnector (법령모니터링 전용)

### 프론트엔드

| 항목 | 수 |
|------|---|
| 페이지 (page.tsx) | 10 |
| 빌드 라우트 | 11 (_not-found 포함) |
| 레이아웃 (layout.tsx) | 2 (root, screening/[id]) |
| 컴포넌트 (.tsx) | 27 (ui:11, risk:4, charts:4, feedback:3, layout:2, map:1, admin:1, root:1) |
| API 호출 함수 | 34 (네트워크 호출 33 + logout 클라이언트 전용 1) |
| 커스텀 훅 | 1 (use-count-up) |
| 타입 파일 | 4 (49개 타입/인터페이스) |
| dependencies | 18 |
| devDependencies | 8 |

---

## 3. 데이터 자산

### 규칙 YAML (77개, 19개 도메인)

| 도메인 | 규칙 수 | | 도메인 | 규칙 수 |
|--------|--------|-|--------|--------|
| ecology | 9 | | land_regulation | 8 |
| water | 7 | | marine | 6 |
| air_quality | 5 | | social | 5 |
| noise | 4 | | soil | 4 |
| traffic | 4 | | cultural | 3 |
| geology | 3 | | greenhouse | 3 |
| hazard | 3 | | landscape | 3 |
| odor | 3 | | population | 3 |
| waste | 2 | | radio | 1 |
| sunshine | 1 | | | |

### 규제 매핑 (174개, 3개 파일)

| 파일 | 항목 수 |
|------|---------|
| zone_code_mapping.json | 80 |
| conservation_type_mapping.json | 64 |
| eia_thresholds.json | 30 |

### 유사사례 (89건, 18개 유형)
cases.json — 89건 큐레이션 완료

### RAG 원문 (103건, 6,103 청크)

| 항목 | 수치 |
|------|------|
| 보고서 디렉토리 | 103 |
| PDF 파일 | 526 |
| ChromaDB 청크 | 6,103 |
| 사업유형 | 16 |

### 벌크 협의 데이터
- 분석 데이터: 9,996건 (analysis/conslt_patterns.json summary)
- 분석 파일: 6개 (common_issues, patterns, by_type, remediation, risk_matrix, suggested_rules)

### 초안 템플릿 (7장 22섹션)

| 장 | 제목 | 섹션 수 |
|----|------|---------|
| ch1 | 사업의 개요 | 3 |
| ch2 | 지역 개황 | 3 |
| ch3 | 평가 항목별 현황 및 영향 예측 | 9 |
| ch4 | 환경영향 저감 방안 | 2 |
| ch5 | 종합 평가 및 결론 | 2 |
| ch6 | 사후환경영향조사 계획 | 2 |
| ch7 | 대안 검토 | 1 |

### 정적 데이터

| 파일 | 항목 수 | 용도 |
|------|---------|------|
| kwater_dam_codes.json | 20개 댐 | 수문 커넥터 최근접 댐 매칭 |
| khoa_stations.json | 30개 관측소 | 해양 커넥터 최근접 조위관측소 매칭 |
| endangered_species.csv | 267종 (I급60, II급207) | 멸종위기종 커넥터 CSV 데이터 |

---

## 4. 외부 API 실연동 현황

### 실연동 API (16종)

| # | 커넥터 | API 엔드포인트 | 제공기관 | 계층 |
|---|--------|--------------|---------|------|
| 1 | LandUse | apis.data.go.kr + api.vworld.kr (11 layers) | 국토교통부/국토지리정보원 | A |
| 2 | Ecology | apis.data.go.kr + api.mcee.go.kr WMS | 국립생태원 | B |
| 3 | AirQuality | apis.data.go.kr (에어코리아 3종) | 한국환경공단 | B |
| 4 | WaterQuality | apis.data.go.kr 수질측정 | 국립환경과학원 | B |
| 5 | Weather | apis.data.go.kr ASOS | 기상청 | B |
| 6 | Traffic | data.ex.co.kr 실시간 교통량 | 한국도로공사 | B |
| 7 | EiaInfo | apis.data.go.kr EIA 6종+상세+협의 | 국립환경과학원 | B |
| 8 | Marine | apis.data.go.kr 해양환경 2종 | 해양수산부 | B |
| 9 | Odor | apis.data.go.kr 악취 | 한국환경공단 | B |
| 10 | Hydrology | apis.data.go.kr K-water 수문 | 한국수자원공사 | B |
| 11 | Ocean | khoa.go.kr 조위관측 | 국립해양조사원 | B |
| 12 | WasteData | recycling-info.or.kr 폐기물 통계 | 한국자원순환정보시스템 | B |
| 13 | Radio | apis.data.go.kr 전파환경 | 과학기술정보통신부 | B* |
| 14 | Industry | apis.data.go.kr 산업단지 | 산업통상자원부 | B* |
| 15 | Facilities | api.vworld.kr POI | 국토지리정보원 | B* |
| 16 | Legislation | law.go.kr 법령정보 | 법제처 | B |

*Radio, Industry, Facilities: API 호출하지만 파싱이 기본값 반환

### CSV/정적 데이터 커넥터 (7종)

| # | 커넥터 | 데이터 파일 | 레코드 수 |
|---|--------|-----------|----------|
| 1 | Soil | 토양오염실태조사 CSV | 2,949 |
| 2 | Noise | 소음진동측정망 CSV | 144,927 |
| 3 | Population | 인구주거 조사/예측 CSV | 19,553 |
| 4 | Geology | 지형지질 개요/경사/표고 CSV | 2,060+ |
| 5 | Greenhouse | 온실가스 인벤토리 CSV | 162 |
| 6 | ProjectArea | BSNS_AREA.dbf | 2,766 |
| 7 | Species | endangered_species.csv | 267 |

### LLM 프로바이더 (V4 변경)

| 항목 | V3 | V4 |
|------|----|----|
| 기본 프로바이더 | OpenRouter (DeepSeek V3) | **Gemini 2.5 Flash** |
| API 방식 | OpenAI 호환 | OpenAI 호환 (동일) |
| 비용 | 무료 (크레딧 소진) | **무료 (Google AI Studio)** |
| max_tokens | 기본값 | **4,096** |
| 팩토리 모듈 | 없음 (직접 생성) | **llm_client.py** (get_llm_client/get_llm_model) |
| 대안 프로바이더 | 없음 | OpenRouter (환경변수 전환) |

---

## 5. 인프라

### Docker (5개 서비스)

| 서비스 | 이미지 | 포트 | non-root | healthcheck |
|--------|--------|------|----------|-------------|
| db | postgis/postgis:16-3.4 | 5432 | — | pg_isready |
| backend | python:3.12-slim | 8000 | ✅ appuser | ✅ curl /health |
| frontend | node:20-slim | 3000 | ✅ appuser | ✅ curl / |
| nginx | nginx:1.27-alpine | 80, 443 | — | — |
| certbot | certbot/certbot | — | — | profile-gated |

### CI/CD (2 워크플로)

**ci.yml** (5 jobs): backend-lint, backend-test, frontend-lint, frontend-build, docker-build
**deploy.yml** (1 job): 플레이스홀더 (manual dispatch)

### 인증

| 항목 | 상태 |
|------|------|
| JWT (HS256) | ✅ 구현 완료 |
| bcrypt 비밀번호 해싱 | ✅ |
| RBAC (admin/analyst/viewer) | ✅ |
| 미들웨어 | ✅ 순수 ASGI (BaseHTTPMiddleware 제거) |
| Protected 라우터 (9개) | ⚠️ **임시 해제** (테스트용, _auth_deps 코드 유지) |
| Public 라우터 (4개) | ✅ auth, data_status, patterns, draft_template |
| 프론트엔드 401 리다이렉트 | ⚠️ **임시 비활성화** (주석 처리) |

### 기타

| 항목 | 수치 |
|------|------|
| Prometheus 메트릭 | 9개 (Counter 5, Histogram 3, Gauge 1) |
| 에러 핸들러 | 3종 (한국어 메시지) |
| Rate Limit 단계 | 4단계 (10~60/min) |
| 법령 모니터링 | 6개 법률 |
| 환경변수 (.env.example) | 31개 |
| Nginx HTTPS | 준비됨 (주석 상태) |

---

## 6. 테스트

### pytest

| 항목 | 수치 |
|------|------|
| 수집 | 205 |
| 통과 | 190 |
| 스킵 | 15 (DB 미연결) |
| 실패 | 0 |
| 에러 | 0 |
| 소요시간 | 121초 |

### Playwright E2E

| 항목 | 수치 |
|------|------|
| 스펙 파일 | 14 |
| 테스트 수 | 67 |

### 34건 풀테스트 (V4 신규)

| 항목 | 수치 |
|------|------|
| 사업유형 | 17 |
| 사례 수 | 34 (유형당 2건) |
| API 호출 | 340 (사례당 10건) |
| 성공률 | 100% (340/340) |
| 리스크 카드 범위 | 3~12건 |
| 규제 매칭 범위 | 1~19건 |
| 유사사례 반환 | 30/34 (mining 2, forest 2 = 0건) |
| 품질 점수 범위 | 93~100점 |
| 초안 생성 | 34/34건 22섹션/7장 |
| 커넥터 가용 | 20~22/22 (90.9~100%) |
| RAG 출처 | 34/34건 5출처 |

### 코드 품질

| 항목 | 수치 |
|------|------|
| ESLint 에러 | 0 |
| TypeScript 에러 | 0 (pnpm build 성공) |
| TODO/FIXME | 0 (프로젝트 코드 내) |

---

## 7. 최종 수치 요약표

| 항목 | V3 수치 | V4 수치 (실측) | 변동 |
|------|---------|---------------|------|
| 백엔드 서비스 | 15 | **15** | — |
| 코어 모듈 | 4 | **5** | +1 (llm_client.py) |
| API 엔드포인트 | 41 | **41** | — |
| API 라우터 | 11 | **11** | — |
| 프론트엔드 페이지 | 10 | **10** | — |
| 프론트엔드 라우트 (빌드) | 11 | **11** | — |
| 프론트엔드 컴포넌트 | 27 | **27** | — |
| API 호출 함수 | 33 | **34** | +1 (logout 포함 집계) |
| 커넥터 파일 | 26 | **26** | — |
| DataFetcher 등록 | 22 | **22** | — |
| 실연동 API | 16 | **16** | — |
| CSV/정적 커넥터 | 7 | **7** | — |
| 정적 데이터 파일 | 3 | **3** | — |
| 규칙 YAML 도메인 | 19 | **19** | — |
| 규칙 수 | 77 | **77** | — |
| 규제 매핑 | 174 | **174** | — |
| 유사사례 | 89 | **89** | — |
| RAG 보고서 | 103 | **103** | — |
| RAG 청크 | 6,103 | **6,103** | — |
| 벌크 데이터 | 9,973 | **9,996** | +23 (분석 파일 기준) |
| 초안 템플릿 장 | 7 | **7** | — |
| 초안 템플릿 섹션 | 22 | **22** | — |
| 단위 테스트 (수집) | 205 | **205** | — |
| 단위 테스트 (통과) | 190 | **190** | — |
| E2E 테스트 | 67 | **67** | — |
| 풀테스트 사례 | — | **34** | V4 신규 |
| 풀테스트 API 호출 | — | **340** | V4 신규 |
| TypeScript 에러 | 0 | **0** | — |
| ESLint 에러 | 0 | **0** | — |
| TODO/FIXME | 1 | **0** | -1 (deploy.yml은 프로젝트 코드 외) |
| 환경변수 | 28 | **31** | +3 (LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL) |
| Docker 서비스 | 5 | **5** | — |
| CI jobs | 6 | **5** | -1 (e2e-test 미확인) |
| Prometheus 메트릭 | 9 | **9** | — |
| RBAC 역할 | 3 | **3** | — |
| 법령 모니터링 | 6개 법률 | **6개 법률** | — |
| LLM 프로바이더 | DeepSeek V3 (OpenRouter) | **Gemini 2.5 Flash** | 전환 |
| JWT 인증 | ✅ 정상 동작 | **⚠️ 임시 해제** | 테스트용 |

---

## 8. V3 → V4 변경점

### 주요 변경

| # | 항목 | V3 상태 | V4 상태 |
|---|------|---------|---------|
| 1 | LLM 프로바이더 | DeepSeek V3 via OpenRouter (크레딧 소진) | ✅ Gemini 2.5 Flash (무료, 안정) |
| 2 | LLM 팩토리 모듈 | 없음 (서비스별 직접 생성) | ✅ llm_client.py (공통 팩토리) |
| 3 | JWT 인증 | ✅ 정상 동작 (3건 테스트) | ⚠️ 임시 해제 (풀테스트용) |
| 4 | 프론트엔드 401 리다이렉트 | ✅ 활성 | ⚠️ 주석 처리 (풀테스트용) |
| 5 | 17유형 풀테스트 | 미실행 | ✅ 34건 완료 (340 API, 100% 성공) |
| 6 | 환경변수 | 28개 | 31개 (+LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL) |
| 7 | 벌크 데이터 집계 | 9,973건 (raw) | 9,996건 (분석 파일 기준) |

### 코드 변경 요약

| 파일 | 변경 내용 |
|------|----------|
| backend/app/core/llm_client.py | **신규** — LLM 프로바이더 팩토리 (Gemini/OpenRouter) |
| backend/app/core/config.py | LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL 추가 |
| backend/app/services/llm_interpreter.py | get_llm_client()/get_llm_model() 사용, max_tokens=4096 |
| backend/app/services/draft_copilot.py | get_llm_client()/get_llm_model() 사용, max_tokens=4096 |
| backend/app/services/report_rag.py | get_llm_client()/get_llm_model() 사용, max_tokens=4096 |
| backend/app/main.py | Protected 라우터에서 dependencies=_auth_deps 제거 (임시) |
| frontend/src/lib/api.ts | 401 → /login 리다이렉트 주석 처리 (임시) |
| tests/test_smoke_e2e.py | LLM mock 대상 변경 (settings → get_llm_client) |
| tests/test_medium_items.py | LLM mock 대상 변경 (settings → get_llm_client) |
| .env | LLM_PROVIDER=gemini, GEMINI_API_KEY, GEMINI_MODEL 추가 |
| .env.example | Gemini 설정 템플릿 추가 |
| docs/FULL_TYPE_TEST_34.md | **신규** — 34건 풀테스트 결과 문서 |

### 34건 풀테스트 주요 발견

| 발견 | 영향 | 권장 조치 |
|------|------|----------|
| mining, forest 유형 유사사례 0건 | 2개 유형 사례 미보유 | 각 3~5건 큐레이션 추가 |
| reclamation 유사사례 1건 | 매립 사례 희소 | 사례 추가 |
| other 유형 유사도 0.07 | 범용 유형 매칭 한계 | 유형 세분화 또는 임계값 조정 |
| 검토의견 유형별 5패턴 그룹 확인 | 차별화 작동 | 정상 |
| 군산 비응도 규제 1건 | 매립 특화 규제만 매칭 | 해양환경관리법 매핑 추가 |

### 남은 이슈

| # | 우선순위 | 이슈 | 비고 |
|---|---------|------|------|
| 1 | 🔴 Critical | **JWT 인증 재활성화** | 테스트 완료 후 _auth_deps 복원 필요 |
| 2 | 🔴 Critical | **프론트엔드 401 리다이렉트 복원** | api.ts 주석 해제 필요 |
| 3 | 🟡 High | deploy.yml 실 배포 구현 | 현재 플레이스홀더 |
| 4 | 🟡 High | HTTPS 활성화 (nginx TLS) | 주석 처리 상태 |
| 5 | 🟡 High | DB 커넥션 풀링 최적화 | — |
| 6 | 🟡 Medium | mining, forest, reclamation 유사사례 추가 | 풀테스트에서 발견 |
| 7 | 🟡 Medium | Radio/Industry/Facilities 커넥터 파싱 개선 | API 호출하지만 응답 미활용 |
| 8 | 🟢 Low | .dockerignore 추가 | 빌드 컨텍스트 최적화 |
| 9 | 🟢 Low | 법령 모니터링 자동 스케줄링 | 현재 수동 트리거 |
| 10 | 🟢 Low | react-map-gl, zustand 미사용 패키지 정리 | — |
| 11 | 🟢 Low | RAG/ML 패키지 버전 고정 | >= → == |
| 12 | 🟢 Low | 15개 DB 테스트 스킵 | CI에서 PostgreSQL 필요 |

---

## 9. 실무 확장 Phase 완료 현황

| Phase | 범위 | 상태 | 주요 성과 |
|-------|------|------|----------|
| A 기반 정비 | A-1~A-4 | ✅ | Dockerfile, JWT+RBAC, CI/CD, 에러핸들러, Rate Limit |
| B 데이터 완결성 | B-1~B-6 | ✅ | 커넥터 14→26, 규칙 64→77, 별표1 55%→70% |
| C 법령 최신성 | C-1~C-2 | ✅ | 법령 모니터링 6개, 관리자 규칙 UI |
| D 보고서·UI | D-1~D-3 | ✅ | 22섹션 템플릿, MapLibre 지도, PDF 전문화 |
| — API 실연동 | hydrology, ocean, waste_data, species | ✅ | 실연동 12→16종, 정적 데이터 3파일 |
| — JWT 수정 | BaseHTTPMiddleware→순수ASGI | ✅ | 인증 401 정상 동작 (V3 확인, V4 임시 해제) |
| — LLM 전환 | DeepSeek V3 → Gemini 2.5 Flash | ✅ | 무료, 안정적, 팩토리 패턴 적용 |
| — 풀테스트 | 17유형 × 2건 = 34건 | ✅ | 340 API 100% 성공, 5패턴 검토의견 차별화 |

**전체 Phase A~D + API 실연동 + JWT + LLM 전환 + 풀테스트 완료 (2026-04-03)**

### 34건 풀테스트 요약 (2026-04-03)

| 유형 | 사례1 리스크 | 사례2 리스크 | 검토의견 1순위 | 품질 | 커넥터 |
|------|-----------|-----------|-------------|------|--------|
| road | C3/M5/R3 | C5/M2/R2 | 소음진동 | 94 | 22/22 |
| railway | C3/M3/R3 | C1/M4/R2 | 소음진동 | 94 | 22/22 |
| airport | C5/M1/R4 | C4/M2/R3 | 소음진동 | 94 | 22/22 |
| port | C3/M2/R3 | C0/M3/R3 | 수질 | 96-97 | 21-22/22 |
| dam | C3/M3/R3 | C3/M2/R3 | 수질 | 94 | 20-21/22 |
| industrial | C3/M4/R3 | C4/M4/R3 | 대기질 | 97 | 21-22/22 |
| energy | C4/M3/R3 | C4/M5/R3 | 대기질 | 94 | 21/22 |
| waste | C3/M4/R1 | C2/M1/R3 | 대기질 | 97 | 21-22/22 |
| urban_dev | C3/M3/R5 | C1/M4/R4 | 대기질 | 94 | 21-22/22 |
| housing | C1/M4/R2 | C1/M2/R2 | 대기질/소음 | 93-94 | 21-22/22 |
| tourism | C5/M3/R3 | C3/M2/R3 | 생태계 85% | 94 | 21-22/22 |
| mining | C4/M5/R2 | C1/M1/R1 | 지형지질 93% | 93-94 | 20-21/22 |
| military | C1/M2/R2 | C4/M2/R1 | 소음진동 89% | 93-94 | 20-21/22 |
| waterway | C1/M1/R3 | C3/M5/R3 | 수질 89% | 96-97 | 21-22/22 |
| reclamation | C0/M2/R3 | C3/M2/R3 | 생태계 95% | 100 | 21-22/22 |
| forest | C3/M4/R1 | C4/M2/R1 | 지형지질 93% | 94 | 21/22 |
| other | C1/M3/R2 | C1/M2/R2 | 수질 89% | 93-94 | 21-22/22 |
