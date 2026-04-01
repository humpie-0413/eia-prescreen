# EIA Pre-Screen 프로젝트 전수조사 보고서 V3

> 조사일: 2026-04-01 | Phase A~D + API 실연동 4종 + JWT 수정 완료 기준 | 조사 도구: Claude Code (Opus 4.6) × 5 병렬 에이전트

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
8. LLM 리스크 종합 해석문 (DeepSeek V3)
9. RAG 기반 평가서 원문 검색 (103건, 6,103 청크)
10. Draft Copilot: 7장 22섹션 초안 자동 생성 (사업유형별 중점 배지)
11. 검토의견 예측 + 품질 체크 (9,973건 과거 데이터)
12. PDF 보고서 생성 (1p 브리프 / 5~10p 요약 / 체크리스트 / 비교)

### 기술 스택
| 계층 | 기술 |
|------|------|
| 프론트엔드 | Next.js 16.2.1 (App Router) + React 19 + TypeScript 5 + Tailwind v4 + shadcn/ui |
| 지도 | MapLibre GL JS 5.21 (CARTO Positron) |
| 백엔드 | FastAPI 0.115 + SQLAlchemy 2.0 + Alembic |
| DB | PostgreSQL 16 + PostGIS 3.4 |
| RAG | ChromaDB + sentence-transformers (jhgan/ko-sroberta-multitask) |
| LLM | DeepSeek V3 via OpenRouter (무료) |
| PDF | ReportLab (Korean CID fonts) |
| 인증 | JWT (HS256) + bcrypt + RBAC (admin/analyst/viewer) |
| 모니터링 | Prometheus metrics (9개) + JSON 구조화 로깅 |
| 인프라 | Docker Compose (5 서비스) + Nginx + Certbot |
| CI/CD | GitHub Actions (ci.yml 6 jobs + deploy.yml) |

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
| 12 | pattern_advisor.py | PatternAdvisor (9,973건) |
| 13 | report_rag.py | ReportRAG (6,103 청크) |
| 14 | cache_manager.py | CacheManager |
| 15 | legislation_monitor.py | LegislationMonitor (6개 법률) |

### API 엔드포인트 (41개)

| 라우터 | 엔드포인트 수 | 인증 |
|--------|-------------|------|
| auth.py | 4 (register, login, refresh, me) | Public |
| screening.py | 3 (create, get, list) | Protected |
| evaluation.py | 3 (evaluate, regulations, checklist) | Protected |
| cases.py | 5 (search, get, similar, interpret, report) | Protected |
| draft.py | 3 (full, section, template) | Mixed (template=Public) |
| review.py | 2 (predict, quality-check) | Protected |
| compare.py | 2 (compare, report) | Protected |
| data_status.py | 3 (connectors, screening, status) | Public |
| patterns.py | 4 (summary, type, predict, suggested) | Public |
| rag.py | 4 (query, draft-assist, stats, index) | Protected |
| admin.py | 6 (law-status, check, acknowledge, rules CRUD) | Protected |
| main.py | 2 (health, metrics) | Public |
| **합계** | **41** | Public: 4라우터, Protected: 9라우터 |

### 커넥터 (26개 파일, 22개 DataFetcher 등록)

**DataFetcher 등록 22개:**
LandUse, Ecology, AirQuality, WaterQuality, Soil, Noise, Population, ProjectArea, EiaInfo, Marine, Geology, Greenhouse, Weather, Traffic, Odor, Radio, Industry, Facilities, Species, Hydrology, Ocean, WasteData

**미등록 4개:** VworldConnector (LandUse 내부 사용), CulturalConnector, LandscapeConnector, LegislationConnector (법령모니터링 전용)

### 프론트엔드

| 항목 | 수 |
|------|---|
| 페이지 (page.tsx) | 10 |
| 빌드 라우트 | 11 (_not-found 포함) |
| 컴포넌트 (.tsx) | 27 (ui:11, risk:4, charts:4, feedback:3, layout:2, map:1, admin:1, root:1) |
| API 호출 함수 | 33 (logout 제외 — 네트워크 미호출) |
| 커스텀 훅 | 1 (use-count-up) |
| 타입 파일 | 4 (screening, draft, review, patterns) |
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
| 추출 텍스트 JSON | 99 |

### 벌크 협의 데이터
- 메인 데이터: 9,973건 (raw/conslt_list_all.json)
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

### 정적 데이터 (V3 신규)

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

*Radio, Industry, Facilities: API 호출은 하지만 파싱이 기본값 반환 (실데이터 활용 개선 필요)

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

**ci.yml** (6 jobs): backend-lint, backend-test, frontend-lint, frontend-build, e2e-test, docker-build
**deploy.yml** (1 job): 플레이스홀더 (manual dispatch)

### 인증

| 항목 | 상태 |
|------|------|
| JWT (HS256) | ✅ 구현 완료 |
| bcrypt 비밀번호 해싱 | ✅ |
| RBAC (admin/analyst/viewer) | ✅ |
| 미들웨어 | ✅ 순수 ASGI (BaseHTTPMiddleware 제거) |
| Protected 라우터 (9개) | ✅ dependencies=[Depends(get_auth_user)] |
| Public 라우터 (4개) | ✅ auth, data_status, patterns, draft_template |
| 통합 테스트 401 확인 | ✅ 3건 사례 모두 정상 차단 (2026-04-01) |

### 기타

| 항목 | 수치 |
|------|------|
| Prometheus 메트릭 | 9개 (Counter 5, Histogram 3, Gauge 1) |
| 에러 핸들러 | 3종 (한국어 메시지) |
| Rate Limit 단계 | 4단계 (10~60/min) |
| 법령 모니터링 | 6개 법률 |
| 환경변수 (.env.example) | 28개 |
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

### Playwright E2E

| 항목 | 수치 |
|------|------|
| 스펙 파일 | 14 |
| 테스트 수 | 67 |

### 코드 품질

| 항목 | 수치 |
|------|------|
| ESLint 에러 | 0 |
| TypeScript 에러 | 0 (pnpm build 성공) |
| TODO | 1 (deploy.yml 배포 구성) |
| FIXME/HACK/XXX | 0 |

---

## 7. 최종 수치 요약표

| 항목 | V2 수치 | V3 수치 (실측) | 변동 |
|------|---------|---------------|------|
| 백엔드 서비스 | 15 | **15** | — |
| API 엔드포인트 | 41 | **41** | — |
| API 라우터 | 11 | **11** | — |
| 프론트엔드 페이지 | 10 | **10** | — |
| 프론트엔드 라우트 (빌드) | 11 | **11** | — |
| 프론트엔드 컴포넌트 | 28 | **27** | -1 (providers.tsx 별도 계산) |
| API 호출 함수 | 34 | **33** | -1 (logout 네트워크 미호출) |
| 커넥터 파일 | 26 | **26** | — |
| DataFetcher 등록 | 22 | **22** | — |
| 실연동 API | 12 | **16** | +4 (hydrology, ocean, waste_data, legislation) |
| CSV/정적 커넥터 | — | **7** | V3 신규 집계 |
| 정적 데이터 파일 | — | **3** (댐20, 관측소30, 종267) | V3 신규 |
| 규칙 YAML 도메인 | 19 | **19** | — |
| 규칙 수 | 77 | **77** | — |
| 규제 매핑 | 174 | **174** | — |
| 유사사례 | 89 | **89** | — |
| RAG 보고서 | 103 | **103** | — |
| RAG 청크 | 6,104 | **6,103** | -1 (실측 ChromaDB) |
| RAG 검색 품질 | 90.3 | **90.3** | — |
| 벌크 데이터 | 9,973 | **9,973** | — |
| 초안 템플릿 장 | 7 | **7** | — |
| 초안 템플릿 섹션 | 22 | **22** | — |
| 단위 테스트 (수집) | 205 | **205** | — |
| 단위 테스트 (통과) | 190 | **190** | — |
| E2E 테스트 | 67 | **67** | — |
| TypeScript 에러 | 0 | **0** | — |
| ESLint 에러 | 0 | **0** | — |
| TODO/FIXME | 1 | **1** | — |
| 환경변수 | 25 | **28** | +3 (KHOA_API_KEY, WASTE_API_KEY, WASTE_API_USERID) |
| 스냅샷 캐시 파일 | 3,470 | **3,658** | +188 (통합 테스트 캐시 누적) |
| Docker 서비스 | 5 | **5** | — |
| Prometheus 메트릭 | 9 | **9** | — |
| RBAC 역할 | 3 | **3** | — |
| 법령 모니터링 | 6개 법률 | **6개 법률** | — |
| JWT 인증 | ⚠️ 런타임 미적용 | **✅ 정상 동작** | 수정 완료 |

---

## 8. V2 → V3 변경점

### 해결된 이슈

| # | 이슈 | V2 상태 | V3 상태 |
|---|------|---------|---------|
| 1 | JWT 인증 런타임 미적용 (🔴 Critical) | BaseHTTPMiddleware 간섭으로 미동작 | ✅ 순수 ASGI 전환으로 수정, 3건 통합 테스트 401 확인 |
| 2 | 초안 18섹션/6장 (백엔드 미재시작) | 재시작 필요 | ✅ 22섹션/7장 정상 생성 확인 |
| 3 | 커넥터 14개만 표시 (백엔드 미재시작) | 재시작 필요 | ✅ 22개 전체 활성화 확인 |
| 4 | hydrology 껍데기 커넥터 | WAMIS API (불안정) | ✅ K-water 수문 운영 API 실연동 |
| 5 | ocean 껍데기 커넥터 | data.go.kr 일반 조위 | ✅ KHOA 조위관측 API 실연동 |
| 6 | waste_data 껍데기 커넥터 | data.go.kr 폐기물 | ✅ 자원순환정보시스템 API 실연동 |
| 7 | species 껍데기 커넥터 | 국가생물종정보 API | ✅ CSV 267종 실데이터 (국립생물자원관) |

### 코드 변경 요약

| 파일 | 변경 내용 |
|------|----------|
| backend/app/core/logging_middleware.py | BaseHTTPMiddleware → 순수 ASGI |
| backend/app/core/metrics.py | BaseHTTPMiddleware → 순수 ASGI |
| backend/app/core/auth.py | 에러 메시지 통일 |
| backend/app/core/config.py | KHOA_API_KEY, WASTE_API_KEY, WASTE_API_USERID 추가 |
| backend/app/connectors/hydrology.py | K-water 수문 API + 하버사인 댐 매칭 |
| backend/app/connectors/ocean.py | KHOA 조위관측 API + 관측소 매칭 |
| backend/app/connectors/waste_data.py | 자원순환정보시스템 API + V-world 역지오코딩 |
| backend/app/connectors/species.py | CSV 기반 멸종위기종 (생태자연도 등급 연동) |
| data/static/kwater_dam_codes.json | 신규 (20개 댐 좌표) |
| data/static/khoa_stations.json | 신규 (30개 관측소 좌표) |
| data/static/endangered_species.csv | 신규 (267종 UTF-8) |
| .env.example | KHOA_API_KEY, WASTE_API_KEY, WASTE_API_USERID 추가 |

### 남은 이슈

| # | 우선순위 | 이슈 | 비고 |
|---|---------|------|------|
| 1 | 🟡 High | deploy.yml 실 배포 구현 | 현재 플레이스홀더 |
| 2 | 🟡 High | HTTPS 활성화 (nginx TLS) | 주석 처리 상태 |
| 3 | 🟡 High | DB 커넥션 풀링 최적화 | — |
| 4 | 🟡 Medium | Radio/Industry/Facilities 커넥터 파싱 개선 | API 호출하지만 응답 미활용 |
| 5 | 🟢 Low | .dockerignore 추가 | 빌드 컨텍스트 최적화 |
| 6 | 🟢 Low | 법령 모니터링 자동 스케줄링 | 현재 수동 트리거 |
| 7 | 🟢 Low | react-map-gl, zustand 미사용 패키지 정리 | — |
| 8 | 🟢 Low | RAG/ML 패키지 버전 고정 | >= → == |
| 9 | 🟢 Low | dashboard/page.tsx 1,127줄 | 컴포넌트 분리 권장 |
| 10 | 🟢 Low | 15개 DB 테스트 스킵 | CI에서 PostgreSQL 필요 |
| 11 | 🟢 Low | water_quality 2007-2011 고정 데이터 | API 연동 완료되었으나 과거 데이터 |

---

## 9. 실무 확장 Phase 완료 현황

| Phase | 범위 | 상태 | 주요 성과 |
|-------|------|------|----------|
| A 기반 정비 | A-1~A-4 | ✅ | Dockerfile, JWT+RBAC, CI/CD, 에러핸들러, Rate Limit |
| B 데이터 완결성 | B-1~B-6 | ✅ | 커넥터 14→26, 규칙 64→77, 별표1 55%→70% |
| C 법령 최신성 | C-1~C-2 | ✅ | 법령 모니터링 6개, 관리자 규칙 UI |
| D 보고서·UI | D-1~D-3 | ✅ | 22섹션 템플릿, MapLibre 지도, PDF 전문화 |
| — API 실연동 | hydrology, ocean, waste_data, species | ✅ | 실연동 12→16종, 정적 데이터 3파일 |
| — JWT 수정 | BaseHTTPMiddleware→순수ASGI | ✅ | 인증 401 정상 동작, 3건 통합 테스트 확인 |

**전체 Phase A~D + API 실연동 + JWT 수정 완료 (2026-04-01)**

### 통합 테스트 결과 (2026-04-01, 3건 실 사례, 재검증)

| 항목 | 부여 관광 | 울산 산업 | 영주 에너지 |
|------|----------|----------|-----------|
| 리스크 카드 | 9 (C:3 M:3 R:3) | 5 (M:2 R:3) | 10 (C:4 M:3 R:3) |
| 규제 매칭 | 7 | 2 | 13 |
| 유사사례 | 5건 (0.31~0.34) | 5건 (0.33~0.35) | 7건 (0.31~0.34) |
| 검토의견 1순위 | 생태계 85% | 대기질 82% | 대기질 92% |
| 품질 체크 | 35/37 (94점) | 30/31 (96점) | 35/37 (94점) |
| RAG 답변 | 684자, 5출처 | 862자, 5출처 | 1,129자, 5출처 |
| 커넥터 | 22/22 (100%) | 22/22 (100%) | 21/22 (95.5%) |
| 초안 | 22섹션/7장 | 22섹션/7장 | 22섹션/7장 |
| 인증 401 | ✅ 정상 | ✅ 정상 | ✅ 정상 |
