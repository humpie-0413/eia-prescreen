# EIA Pre-Screen 프로젝트 전수조사 보고서

> 조사일: 2026-03-31 | 조사 도구: Claude Code (Opus 4.6) × 5 병렬 에이전트

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
9. RAG 기반 평가서 원문 검색 (103건, 6,104 청크)
10. Draft Copilot: 6장 18섹션 초안 자동 생성
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
| 모니터링 | Prometheus metrics |
| 인프라 | Docker Compose + Nginx + Certbot |
| 패키지 | pnpm (프론트) / pip + venv (백엔드) |

---

## 2. 아키텍처 현황

### 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx (:80/:443)                         │
│                  ┌──────────┬──────────────┐                    │
│                  │ /api/*   │ /*           │                    │
│                  ▼          ▼              │                    │
│  ┌──────────────────┐ ┌──────────────────┐│                    │
│  │ FastAPI (:8000)   │ │ Next.js (:3000)  ││                    │
│  │  14 서비스        │ │  10 페이지        ││                    │
│  │  32 엔드포인트    │ │  25 API 함수      ││                    │
│  │  17 커넥터        │ │  19 컴포넌트      ││                    │
│  └───────┬──────────┘ └──────────────────┘│                    │
│          │                                 │                    │
│  ┌───────▼──────────┐ ┌──────────────────┐│                    │
│  │ PostgreSQL+PostGIS│ │ ChromaDB (RAG)   ││                    │
│  │  4 테이블         │ │  6,104 청크       ││                    │
│  └──────────────────┘ └──────────────────┘│                    │
│          │                                 │                    │
│  ┌───────▼──────────────────────────────┐ │                    │
│  │ 파일 스토리지 (data/)                 │ │                    │
│  │  스크리닝 JSON / 캐시 스냅샷 / CSV    │ │                    │
│  │  사례 89건 / 규제 174개 / 규칙 64개   │ │                    │
│  │  벌크 분석 9,973건 / 보고서 103건     │ │                    │
│  └──────────────────────────────────────┘ │                    │
│                                            │                    │
│  ┌──────────────────────────────────────┐ │                    │
│  │ 외부 API (34종 승인, 12종 실연동)     │ │                    │
│  │  토지이용규제 / V-world / 에어코리아   │ │                    │
│  │  수질 / 토양 / 기상 / 교통 / 생태 등  │ │                    │
│  └──────────────────────────────────────┘ │                    │
│                                            │                    │
│  ┌──────────────────────────────────────┐ │                    │
│  │ OpenRouter (DeepSeek V3)              │ │                    │
│  │  리스크 해석문 / Draft / RAG 답변      │ │                    │
│  └──────────────────────────────────────┘ │                    │
└─────────────────────────────────────────────────────────────────┘
```

### 백엔드 서비스 목록 (14개)

| 서비스 | 파일 | 역할 |
|--------|------|------|
| ScreeningStore | `screening_store.py` | 스크리닝 CRUD (인메모리→JSON→DB 3계층 조회) |
| DataFetcher | `data_fetcher.py` | 14개 커넥터 병렬 호출 + 데이터 정규화 |
| RiskEngine | `risk_engine.py` | 64개 YAML 규칙 평가 → 리스크 카드 생성 |
| RegulationMatcher | `regulation_matcher.py` | 174개 규제 매핑 매칭 |
| ChecklistGenerator | `checklist_generator.py` | 심각도별 현장조사 체크리스트 생성 |
| CaseSearch | `case_search.py` | 89건 유사사례 검색 (다중 요인 유사도) |
| LLMInterpreter | `llm_interpreter.py` | DeepSeek V3 자연어 해석문 생성 |
| ReportGenerator | `report_generator.py` | PDF 4종 생성 (ReportLab) |
| DraftCopilot | `draft_copilot.py` | 6장 18섹션 초안 (템플릿+RAG+LLM) |
| ReviewPredictor | `review_predictor.py` | 검토의견 예측 (PatternAdvisor 기반) |
| QualityChecker | `quality_checker.py` | 33항목 품질 체크 |
| PatternAdvisor | `pattern_advisor.py` | 9,973건 벌크 데이터 패턴 분석 |
| ReportRAG | `report_rag.py` | ChromaDB RAG 검색 + LLM 답변 생성 |
| CacheManager | `cache_manager.py` | 파일 기반 스냅샷 캐시 (TTL 24h) |

### 프론트엔드 페이지 목록 (10개)

| 라우트 | 기능 |
|--------|------|
| `/` | 랜딩 (히어로, 기능 소개, 통계, CTA) |
| `/screening/new` | 스크리닝 생성 (사업유형 선택 → 상세 입력 + 지도) |
| `/screening/compare` | 부지 비교 (최대 3개 선택 → 매트릭스 + PDF) |
| `/screening/[id]/dashboard` | 리스크 대시보드 (차트, 카드, 체크리스트, 패턴, 검토의견) |
| `/screening/[id]/map` | 리스크 지도 (placeholder — 개발 중) |
| `/screening/[id]/data-status` | 데이터 가용성 (커넥터 상태, 커버리지, 신선도) |
| `/screening/[id]/cases` | 유사사례 + PDF 보고서 + AI 해석 |
| `/screening/[id]/draft` | Draft Copilot (6장 18섹션 초안) |
| `/screening/[id]/rag` | RAG 원문 검색 (질의 → AI 답변 + 출처) |

### 데이터 흐름

```
[사용자: 좌표 + 사업유형 입력]
    │
    ▼
screening_store.create() → 인메모리 + JSON 파일 + DB(가용 시)
    │
    ▼
data_fetcher.fetch_all() → 17개 커넥터 병렬 (asyncio.gather, 45s 타임아웃)
    │                        → 실패 시 캐시 → 캐시 없으면 빈 결과
    ▼
risk_engine.evaluate() → 64개 YAML 규칙 → 리스크 카드
    │
    ▼
regulation_matcher.match() → 174개 규제 매핑 → 규제 매칭
    │
    ▼
screening_store.update_evaluation() → 결과 저장
    │
    ├─→ similar-cases: 유사사례 검색 (다중 요인 유사도)
    ├─→ interpret: LLM 자연어 해석문
    ├─→ checklist: 현장조사 체크리스트
    ├─→ draft: 18섹션 초안 (템플릿 + RAG + LLM)
    ├─→ predict-review: 검토의견 예측 (패턴 분석)
    ├─→ quality-check: 33항목 품질 체크
    ├─→ report: PDF 생성
    └─→ rag: 원문 검색 + AI 답변
```

---

## 3. 데이터 자산 현황

### 커넥터 17개 상세

| # | 커넥터 | 계층 | 데이터 소스 | 인증 | 데이터 규모 |
|---|--------|------|-----------|------|-----------|
| 1 | land_use | A | 토지이용규제정보 (Luris) + V-world 11개 레이어 | DATA_GO_KR + VWORLD API Key | 실시간 |
| 2 | weather | A | 기상청 ASOS 일기상 | DATA_GO_KR API Key | 실시간 + 캐시 |
| 3 | air_quality | B | 에어코리아 대기오염 | DATA_GO_KR API Key | 실시간 + 캐시 |
| 4 | water_quality | B | 수질측정정보 (WEIS) | DATA_GO_KR API Key | 2007-2011 고정 + 캐시 |
| 5 | ecology | B | 생태자연도 (EGIS WMS) | 공개 (키 불필요) | 실시간 + 캐시 |
| 6 | eia_info | B | 환경영향평가정보 11종 | DATA_GO_KR API Key | 실시간 + 캐시 |
| 7 | geology | B | 지형지질 CSV | 로컬 파일 | 2,060건 |
| 8 | soil | B | 토양오염 CSV | 로컬 파일 | 2,949건 |
| 9 | noise | B | 소음진동 CSV | 로컬 파일 | 144,927건 |
| 10 | population | B | 인구주거 CSV | 로컬 파일 | 18,614 + 939건 |
| 11 | traffic | B | 한국도로공사 교통량 | DATA_EX API Key | 실시간 + 캐시 |
| 12 | vworld | B | V-world WFS 연속지적도 | VWORLD API Key | 실시간 |
| 13 | marine | B | 해양환경 (EIASS + MOF) | DATA_GO_KR API Key | 실시간 + 캐시 |
| 14 | cultural | C | 문화재청 GIS | DATA_GO_KR API Key | 실시간 + 캐시 |
| 15 | landscape | C | 국가경관포털 | DATA_GO_KR API Key | 실시간 + 캐시 |
| 16 | greenhouse | C | 온실가스 인벤토리 CSV | 로컬 파일 | 162건 (1990-2023) |
| 17 | project_area | C | 사업면적 DBF | 로컬 파일 | 2,766건 |

**스냅샷 캐시**: 3,462개 JSON 파일 (13.5MB), 8개 커넥터 유형

### 규칙 64개 (16개 도메인)

| 도메인 | 규칙 수 | 도메인 | 규칙 수 |
|--------|--------|--------|--------|
| land_regulation | 8 | marine | 4 |
| ecology | 7 | cultural | 3 |
| air_quality | 5 | geology | 3 |
| water | 5 | greenhouse | 3 |
| noise | 4 | hazard | 3 |
| soil | 4 | landscape | 3 |
| traffic | 4 | population | 3 |
| | | social | 3 |
| | | waste | 2 |

### 규제 매핑 174개

| 파일 | 매핑 수 | 내용 |
|------|--------|------|
| zone_code_mapping.json | 80 | 용도지역/지구 코드별 법적 근거, 허용/제한 용도, EIA 트리거 |
| conservation_type_mapping.json | 64 | 보전지역 유형별 제한 수준, 완충지대, 허가 기관 |
| eia_thresholds.json | 30 | 사업유형별 EIA 임계값, 평가 유형, 관할 기관 |

### 유사사례 89건 (유형별 분포)

| 유형 | 건수 | 유형 | 건수 |
|------|------|------|------|
| 도로 | 12 | 공항 | 5 |
| 항만 | 10 | 군사시설 | 4 |
| 산업단지 | 8 | 상하수도 | 3 |
| 발전소 | 7 | 철도 | 3 |
| 주거단지 | 6 | 공원/교육/물류/의료 | 각 3 |
| 하천 | 6 | 해양 | 2 |
| 관광단지 | 5 | 매립/간척 | 1 |
| 폐기물 | 5 | | |

### RAG 시스템

| 항목 | 수치 |
|------|------|
| 원본 보고서 | 103건 (526 PDF, 6.3GB, 16개 사업유형) |
| 추출 성공 | 99건 (4건 추출 실패) |
| 벡터 청크 | 6,104개 (500자/청크, 50자 오버랩) |
| 임베딩 모델 | jhgan/ko-sroberta-multitask |
| 벡터 DB | ChromaDB (97MB SQLite + 88MB HNSW 인덱스) |
| RAG 품질 점수 | 94.0/100 (검색 90.3, LLM 92.7) |

**청크 유형별 분포 (상위 5)**:
하천이용개발 569 / 철도건설 512 / 산업입지 509 / 토석광물채취 506 / 도시개발 506

### 벌크 데이터

| 항목 | 수치 |
|------|------|
| 협의 원본 | 9,973건 (conslt_list_all.json, 2.3MB) |
| 분석 유형 | 19개 사업유형 |
| 분석 파일 | 6개 (패턴, 위험 매트릭스, 공통 이슈, 보완 패턴, 제안 규칙, 전체 요약) |
| 연도 범위 | 2010-2026 |

---

## 4. 환경영향평가법 별표1 기준 데이터 커버리지

### 6개 분야 20개 항목

| 분야 | 항목 | 커버리지 | 커넥터 | 비고 |
|------|------|---------|--------|------|
| **자연환경** | 기상 | ✅ | weather (ASOS) | 기온/강수/풍향/풍속/일조 |
| | 지형·지질 | ✅ | geology (CSV 2,060건) | 표고/경사/지질도/광산 |
| | 동·식물상 | ⚠️ | ecology (WMS 등급) | 생태자연도 등급만 — 종 목록 미보유 |
| | 해양환경 | ⚠️ | marine (EIASS+MOF) | 해양생태 기본 — 수심/조류 미보유 |
| | 수리·수문 | ⚠️ | water_quality (WEIS) | 수질측정만 — 유량/수위 미보유 |
| **생활환경** | 대기질 | ✅ | air_quality (에어코리아) | PM10/PM2.5/NO2/O3/CO/SO2 |
| | 수질 | ✅ | water_quality (WEIS) | BOD/COD/SS/DO/TP |
| | 토양 | ✅ | soil (CSV 2,949건) | 중금속 8항목 |
| | 폐기물 | ⚠️ | — | 규칙만 있고 실데이터 없음 |
| | 소음·진동 | ✅ | noise (CSV 144,927건) | 도시별 소음 통계 |
| | 악취 | ❌ | — | 커넥터 없음 |
| | 전파장해 | ❌ | — | 커넥터 없음 |
| | 일조장해 | ❌ | — | 커넥터 없음 |
| | 위락시설 | ❌ | — | 커넥터 없음 |
| **사회·경제** | 인구 | ✅ | population (CSV 18,614건) | 인구/세대/밀도 |
| | 주거 | ✅ | population (CSV) | 주거유형/밀도 |
| | 산업 | ❌ | — | 커넥터 없음 |
| | 교통 | ✅ | traffic (도로공사) | 고속도로 교통량 실시간 |
| | 문화재 | ✅ | cultural (문화재청 GIS) | 문화재 위치/보호구역 |
| | 경관 | ✅ | landscape (경관포털) | 경관자원/조망점 |

**커버리지 요약**: ✅ 11개 / ⚠️ 4개 / ❌ 5개 (55% 완전, 20% 부분, 25% 미보유)

### 미보유 항목별 확보 가능 공공 API

| 미보유 항목 | 확보 가능 API | 제공기관 |
|-----------|------------|---------|
| 악취 | 악취측정망 API (data.go.kr) | 국립환경과학원 |
| 전파장해 | 전파환경측정 API | 과학기술정보통신부 |
| 일조장해 | 기상청 ASOS 일사량 데이터 (이미 weather 커넥터에 추가 가능) | 기상청 |
| 위락시설 | 국가공간정보포털 POI | 국토교통부 |
| 산업 | 산업통계 API, 사업체조사 | 통계청 |
| 동·식물상 (종) | 국가생물종정보 API | 국립생물자원관 |
| 수리·수문 (유량) | 수문관측 API | 한국수자원공사 |
| 해양 (수심/조류) | 해양조사원 API | 국립해양조사원 |
| 폐기물 (실데이터) | 폐기물발생현황 API | 한국환경공단 |

---

## 5. 테스트 현황

### 단위 테스트 (pytest)

| 파일 | 테스트 수 | 설명 |
|------|----------|------|
| `tests/test_risk_evaluation.py` | 35 | 리스크 엔진 평가 (3 시나리오 + 체크리스트) |
| `tests/test_smoke_e2e.py` | 33 | API 스모크 테스트 |
| `tests/test_medium_items.py` | 23 | 재시도, 심각도, 매처, LLM, PDF, 메트릭 |
| `tests/test_cache_and_fallback.py` | 6 | 캐시 저장/로드, 스냅샷, 커넥터 폴백 |
| `backend/tests/test_draft_copilot.py` | 27 | 드래프트 생성, 템플릿, 패턴 통합 |
| `backend/tests/test_report_rag.py` | 24 | RAG 메타데이터, 청킹, 쿼리, 크롤러 |
| `backend/tests/test_pattern_advisor.py` | 24 | 패턴 로딩, 유형별 분석, 제안 규칙 |
| `backend/tests/test_review_predictor.py` | 23 | 검토의견 예측, 품질 체크, API |
| `backend/tests/test_eia_info_connector.py` | 10 | 하버사인 거리, XML 파싱, 필터링 |
| **합계** | **205** | 190 통과 / 15 스킵(DB) / 0 실패 |

### E2E 테스트 (Playwright)

| 파일 | 테스트 수 | 설명 |
|------|----------|------|
| `landing.spec.ts` | 5 | 히어로, 통계, 기능, CTA, 사이드바 |
| `screening-new.spec.ts` | 5 | 17유형 그리드, 선택, 빈 제출 에러, 리다이렉트, 스텝 |
| `dashboard.spec.ts` | 4 | 리스크 요약, 탭, 카드, 증거 드로어 |
| `draft.spec.ts` | 6 | 섹션 렌더링, 면책, 뱃지, 아코디언, 통계 |
| `data-status.spec.ts` | 4 | 커버리지, 커넥터 상태, 데모 뱃지, 신선도 |
| `compare.spec.ts` | 5 | 헤딩, 목록, 3개 선택 제한, 비교 실행, 비활성화 |
| `accessibility.spec.ts` | 5 | 헤딩 계층, 키보드, 포커스, 라벨, 아코디언 |
| `responsive.spec.ts` | 7 | 모바일/태블릿/데스크톱 반응형 |
| `r1/charts.spec.ts` | 4 | 도넛/바/패턴 차트, 빈 데이터 |
| `r1/map-layers.spec.ts` | 4 | 맵 컨테이너, 레이어 토글, 콘솔 에러 |
| `r1/rag-ui.spec.ts` | 5 | 입력, 응답, 메타데이터, 빈 쿼리, Enter |
| `r2/error-states.spec.ts` | 5 | 500 에러, 빈 데이터, 빈 사례 |
| `r2/interactions.spec.ts` | 4 | 호버 툴팁, 키보드, 스켈레톤, 프로그레스 |
| `r2/form-validation.spec.ts` | 4 | 빈 이름 에러, 성공 토스트, 실패 에러, 스텝2 |
| **합계** | **67** | 전체 통과 |

### 현재 통과율

| 항목 | 결과 |
|------|------|
| pytest | 190/205 통과 (15 스킵 — DB 의존, 0 실패) |
| Playwright E2E | 67/67 통과 |
| pnpm build | 성공 (7.3s) |
| tsc --noEmit | 0 에러 |
| ESLint | 0 에러 |

---

## 6. 알려진 이슈

### P0 (기능 미동작)
없음 — 전 기능 정상 (51건 전수 테스트 통과)

### P1 (데이터 부정확)
| # | 이슈 | 영향 |
|---|------|------|
| 1 | 유사사례 5개 사업유형(urban_dev, mountain, sports, mining, other) 매칭 0건 | 사례 라이브러리 태깅 체계와 API project_type 간 매핑 갭 |
| 2 | water_quality 커넥터가 2007-2011 고정 데이터 반환 | 수질 데이터 최신성 부족 |

### P2 (품질 미흡)
| # | 이슈 | 영향 |
|---|------|------|
| 1 | README.md 수치 불일치 (테스트 114→205+67, 커넥터 18→17, 엔드포인트 29→32) | 문서 신뢰성 |
| 2 | README.md에 삭제된 데모 시나리오 참조 잔존 | 사용자 혼란 |
| 3 | .env.example의 DEMO_MODE 설명 오래됨 (data/demo/ 참조) | 설정 혼란 |
| 4 | CLAUDE.md에 ITERATION_PLAN_V2.md 참조하나 파일 부재 | 문서 불일치 |
| 5 | CLAUDE.md에 report.py, regulation.py 라우터 명시하나 실제 없음 | 문서 불일치 |
| 6 | E2E 테스트 24곳에서 `?scenario=yangpyeong` 잔존 (기능 영향 없음) | 코드 정리 필요 |
| 7 | data/demo/ 디렉토리 잔존 (내용은 비어있음) | CLAUDE.md "삭제 완료" 불일치 |
| 8 | dashboard/page.tsx 1,124줄 — 컴포넌트 분리 권장 | 유지보수성 |

### P3 (개선 권장)
| # | 이슈 | 영향 |
|---|------|------|
| 1 | /screening/[id]/map 페이지 placeholder (미구현) | 지도 기능 부재 |
| 2 | Auth 구현 완료되었으나 데이터 엔드포인트에 미적용 | 보안 미비 |
| 3 | 15개 DB 의존 테스트 스킵 (CI에서 미실행) | 테스트 커버리지 갭 |
| 4 | react-map-gl, zustand 선언되었으나 미사용 | 불필요 의존성 |
| 5 | CI/CD 파이프라인 없음 (.github/workflows/ 비어있음) | 자동 배포 불가 |
| 6 | Backend Dockerfile에 non-root 사용자, 헬스체크 없음 | 보안/운영 |
| 7 | docker-compose.yml에서 dev 모드 실행 (--reload / pnpm dev) | 프로덕션 미적합 |
| 8 | RAG/ML 패키지 버전 미고정 (>=) | 재현성 리스크 |

---

## 7. 최종 수치 요약표

| 항목 | 수치 |
|------|------|
| 백엔드 서비스 | 14개 |
| API 엔드포인트 | 32개 (30 앱 + 2 인프라) |
| API 라우터 | 10개 |
| 프론트엔드 페이지 | 10개 |
| 프론트엔드 컴포넌트 | 19개 |
| API 호출 함수 | 25개 |
| 커넥터 | 17개 파일 (14개 DataFetcher 등록) |
| 규칙 (YAML) | 64개 (16개 도메인) |
| 규제 매핑 | 174개 (3개 파일) |
| 유사사례 | 89건 (18개 유형) |
| RAG 보고서 | 103건 (526 PDF, 6.3GB) |
| RAG 청크 | 6,104개 |
| RAG 품질 | 94.0/100 |
| 벌크 데이터 | 9,973건 |
| 패턴 분석 유형 | 19개 (8,949건) |
| 사업유형 | 17개 (환경영향평가법 시행령 별표3) |
| 단위 테스트 | 205개 (190 통과 / 15 스킵) |
| E2E 테스트 | 67개 (67 통과) |
| TypeScript 에러 | 0개 |
| ESLint 에러 | 0개 |
| TODO/FIXME | 1개 (deploy.yml) |
| 환경변수 | 21개 |
| 데이터 총 용량 | ~6.6GB |
| 스냅샷 캐시 | 3,462개 파일 (13.5MB) |
| 저장된 스크리닝 | 371건 |
| 별표1 커버리지 | 55% 완전 / 20% 부분 / 25% 미보유 |
