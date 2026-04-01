# EIA Pre-Screen — 최종 마무리 실행 계획 v4

> 작성일: 2026-03-29
> 현재 상태: RAG 파이프라인 완성 (103건 보고서, 6,103 청크)
> 목표: 품질 검증 → 로컬 결과물 확인 → 문서 업데이트 → UI/UX → 배포

---

## 완료 현황 총정리

### Step 1~11 (완료)

| Step | 작업 | 상태 | 핵심 수치 |
|------|------|------|----------|
| 1 | 유사사례 자동 수집 | ✅ | 84건 (DeepSeek 태깅) |
| 2 | 규제 매핑 확장 | ✅ | 175개 (81+64+30) |
| 3 | 규칙 YAML 확장 | ✅ | 64개 (12 도메인, 16 파일) |
| 4 | 커넥터 14개 확장 | ✅ | 12종 실연동 |
| 5 | 데모 실데이터 교체 | ✅ | 3개 시나리오 |
| 6 | 최종 통합 검증 | ✅ | 97 tests |
| 7 | 벌크 수집 스크립트 | ✅ | 9,973건 실데이터 |
| 8 | 패턴 분석 | ✅ | 12개 유형별 통계 |
| 9 | 패턴 DB 서비스 통합 | ✅ | 프론트 대시보드 반영 |
| 10 | Draft Copilot | ✅ | 6장 18섹션 초안 생성 |
| 11 | 검토의견 예측 + 품질 체크 | ✅ | 예측 + 33개 품질 체크 |
| — | MEDIUM 6건 보완 | ✅ | nginx, Prometheus, 접근성 등 |
| — | EIASS 크롤링 + RAG | ✅ | 103건, 6,103 청크, 16 유형 |

### 현재 수치

| 항목 | 수치 |
|------|------|
| 테스트 | 174개 (161 passed + 13 skipped) |
| 실제 환평 보고서 | 103건 (526 PDF, 6.3GB) |
| RAG 청크 | 6,103개 (16개 사업유형) |
| 벌크 협의 데이터 | 9,973건 |
| 실연동 API | 12종 (34종 승인) |
| 규칙 YAML | 64개 (17개 사업유형 지원) |
| 유사사례 | 84건 |
| 규제 매핑 | 175개 |
| API 커넥터 | 14개 |
| 프론트엔드 라우트 | 7개 |
| 백엔드 엔드포인트 | 25개+ |

---

## 남은 Step (15~20)

### Step 15: RAG 품질 테스트

**목표**: RAG가 실제로 유의미한 답변을 생성하는지 검증

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 15를 실행해줘.
```

**상세 작업**:

1. 사업유형별 대표 질의 17개 테스트:
   - 도로: "도로 사업의 비산먼지 저감방안은?"
   - 에너지: "화력발전소의 대기오염물질 배출 저감 기술은?"
   - 산업입지: "산업단지 조성 시 수질 오염 방지 대책은?"
   - 도시개발: "택지개발 사업의 교통 영향 저감방안은?"
   - 철도: "철도 건설 시 소음진동 대책은?"
   - 항만: "항만 준설 시 해양생태계 보호 방안은?"
   - 공항: "공항 건설의 조류 충돌 방지 대책은?"
   - 하천: "하천 정비 사업의 수생태계 보전 방안은?"
   - 수자원: "댐 건설 시 수몰 지역 주민 대책은?"
   - 관광: "골프장 건설의 산림 훼손 대응 방안은?"
   - 산지: "채석 사업의 지형경관 영향 최소화 방안은?"
   - 체육: "스키장 건설의 생태계 영향은?"
   - 폐기물: "소각시설 주변 다이옥신 저감 대책은?"
   - 국방: "군사시설 건설의 자연환경 보전 방안은?"
   - 토석: "골재 채취의 하천 생태계 영향은?"
   - 매립: "매립 사업의 해양환경 영향 저감방안은?"
   - 기타: "물류센터 건설의 교통 영향 대책은?"

2. 각 질의에 대해 평가:
   - 응답 길이 (최소 200자 이상)
   - 출처 표시 여부 ("출처: OO사업 환경영향평가서, p.XX")
   - 도메인 관련성 (질의 유형과 응답 유형 일치 여부)
   - 구체성 (실제 수치, 기술명, 법령 언급 여부)

3. Draft Copilot RAG 연동 테스트:
   - 양평 도로 시나리오로 초안 생성
   - 초안에 "실제 평가서 참조" 내용이 포함되는지 확인
   - 보령 발전소 시나리오로도 동일 테스트

4. 품질 점수 산출:
   - 17개 질의 중 유의미한 답변 비율
   - 출처 정확성
   - 응답 다양성 (같은 출처만 반복하지 않는지)

5. 결과를 data/rag/quality_report.json에 저장

6. 품질이 낮은 유형이 있으면 원인 분석 (청크 수 부족, 텍스트 추출 오류 등)

---

### Step 16: 로컬 실행 + E2E 결과물 확인

**목표**: 프론트엔드+백엔드를 로컬에서 실행하고 3개 시나리오의 전체 흐름 검증

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 16을 실행해줘.
```

**상세 작업**:

1. 로컬 실행 환경 최종 점검:
   - .env 설정 확인 (DEMO_MODE=true, OPENROUTER_API_KEY, DATA_GO_KR_API_KEY)
   - frontend/.env.local 확인 (NEXT_PUBLIC_API_URL=http://localhost:8000)
   - pip install 누락 패키지 확인
   - pnpm install 확인

2. 백엔드 실행 + API 헬스체크:
   - uvicorn 실행
   - GET /health 정상 응답 확인
   - GET /docs (Swagger UI) 접근 확인

3. E2E 시나리오 3개 자동 테스트 스크립트 작성:
   backend/scripts/e2e_test.py 생성:

   시나리오 1: 양평 도로
   - POST /api/screening → 스크리닝 생성
   - GET /api/screening/{id}/risks → 리스크 목록 (Major 4건 확인)
   - GET /api/screening/{id}/regulations → 규제 매칭
   - GET /api/screening/{id}/cases → 유사사례
   - POST /api/screening/{id}/interpret → LLM 해석
   - POST /api/screening/{id}/draft → 초안 생성 (18섹션)
   - POST /api/screening/{id}/predict-review → 검토의견 예측
   - POST /api/screening/{id}/quality-check → 품질 체크
   - POST /api/rag/query → RAG 질의
   - GET /api/patterns/road → 과거 패턴
   - POST /api/screening/{id}/report/brief → PDF 생성

   시나리오 2: 보령 발전소
   - 동일 흐름 (Critical 2건 확인)

   시나리오 3: 세종 주거
   - 동일 흐름

4. 각 시나리오의 응답을 data/e2e_results/에 JSON으로 저장

5. 프론트엔드 페이지별 접근 가능 여부 확인:
   - / (랜딩)
   - /screening/new (새 스크리닝)
   - /screening/[id]/dashboard (대시보드)
   - /screening/[id]/cases (유사사례)
   - /screening/[id]/draft (초안)
   - /screening/compare (부지 비교)
   - /screening/[id]/report (보고서)

6. 발견된 문제점을 즉시 수정

---

### Step 17: 전체 문서 업데이트

**목표**: 프로젝트 문서를 현재 상태에 맞게 전면 갱신

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 17을 실행해줘.
```

**상세 작업**:

1. CLAUDE.md 전면 업데이트:
   - 기술 스택: RAG (ChromaDB + ko-sroberta) 추가
   - 데이터: 103건 보고서, 6,103 청크, 9,973건 벌크
   - API: 12종 실연동, 34종 승인
   - 사업유형: 17개 (환경영향평가법 시행령 별표3 전체)
   - 테스트: 174개

2. README.md 전면 재작성:
   - 프로젝트 한 줄 소개
   - 주요 기능 목록 (스크리닝, RAG, Draft Copilot, 검토의견 예측)
   - 기술 아키텍처 다이어그램 (텍스트)
   - 데이터 소스 목록 (API 34종)
   - 설치 및 실행 방법
   - 스크린샷 안내 (추후 추가)
   - 라이선스

3. PRODUCTION_READINESS.md 업데이트:
   - RAG 시스템 추가
   - 17개 사업유형 반영
   - 운영 준비도 재평가

4. DEMO.md 업데이트:
   - 3개 시나리오에 RAG 질의 예시 추가
   - 기대 결과 업데이트

5. docs/API_REFERENCE.md 신규 생성:
   - 전체 API 엔드포인트 목록 (25개+)
   - 각 엔드포인트별 요청/응답 예시
   - 인증 방법 (JWT)

6. docs/DATA_SOURCES.md 신규 생성:
   - 공공데이터 API 34종 전체 목록
   - 각 API별 상태 (실연동/장애/대기)
   - V-world, 환경공간정보 WMS 레이어 목록
   - EIASS 크롤링 데이터 현황

7. .env.example 업데이트:
   - EIASS_ID, EIASS_PW 추가
   - 전체 환경변수 설명 주석

---

### Step 18: UI/UX 디자인 개선

**목표**: 포트폴리오 첫인상을 결정하는 시각적 품질 향상

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 18을 실행해줘.
```

**상세 작업**:

1. 색상 체계 통일:
   - 환경/자연 톤 (teal-600 primary, green-500 accent, amber-500 warning, red-500 critical)
   - 리스크 severity별 색상 고정 (Critical=red, Major=orange, Moderate=yellow, Review=blue)
   - tailwind.config.ts에 커스텀 색상 등록

2. 랜딩 페이지 (/) 디자인:
   - 히어로 섹션: 프로젝트 소개 + "스크리닝 시작" CTA 버튼
   - 주요 기능 3개 카드 (리스크 분석, AI 초안 생성, 검토의견 예측)
   - 데이터 현황 숫자 (103건 보고서, 9,973건 분석, 64개 규칙)
   - 기술 스택 아이콘 로우

3. 대시보드 레이아웃 개선:
   - 리스크 요약을 상단 히어로 카드에
   - 과거 패턴 예측을 우측 사이드바에
   - 유사사례를 하단 카드 그리드에

4. 지도 시각화 강화:
   - V-world 용도지역 GeoJSON 오버레이
   - 부지 반경 원 표시
   - 리스크 포인트 마커 (severity별 색상)
   - WMS 토지피복도 배경 레이어 토글

5. 로딩 UX:
   - 스켈레톤 로딩 (shimmer)
   - RAG 질의 시 타이핑 애니메이션
   - Draft Copilot 생성 시 섹션별 순차 표시

6. 모바일 반응형 최종 점검

7. 다크모드 색상 점검

8. pnpm build 확인

---

### Step 19: GitHub 업로드 + 배포

**목표**: 실제 접근 가능한 URL 제공

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 19를 실행해줘.
```

**상세 작업**:

1. .gitignore 최종 점검:
   - data/reports/raw/ (PDF 6.3GB 제외)
   - data/bulk/raw/ (벌크 JSON 제외)
   - .env (키 보호)
   - node_modules/, __pycache__/, .next/
   - chromadb 로컬 DB 제외

2. 커밋 구조:
   - feat: initial project setup (Phase 0)
   - feat: risk engine + regulation matcher (Phase 1-2)
   - feat: case library + LLM integration (Phase 3)
   - feat: site comparison (Phase 4)
   - feat: auth + security + operations (Critical/High/Medium)
   - feat: data acquisition + API integration (Step 1-6)
   - feat: pattern analysis + service integration (Step 7-9)
   - feat: draft copilot + review prediction (Step 10-11)
   - feat: EIASS crawling + RAG system (RAG)
   - feat: UI/UX improvements (Step 18)

3. GitHub 리포지토리 생성 안내

4. GitHub Actions CI 워크플로우 동작 확인

5. 배포 안내:
   - 프론트엔드: Vercel (무료)
   - 백엔드: Railway 또는 Render (무료 티어)
   - DB: Supabase PostgreSQL (무료)

6. 릴리즈 태그: v1.0.0

---

### Step 20: 포트폴리오 발표 자료

**목표**: 프로젝트를 효과적으로 전달하는 발표 자료

**Claude Code 프롬프트**:
```
docs/FINAL_PLAN_V4.md를 읽고 Step 20을 실행해줘.
```

**상세 작업**:

1. docs/PORTFOLIO_PRESENTATION.md 생성:
   - 프로젝트 한 줄 소개
   - 해결하려는 문제 (환평 초기 검토의 비효율성)
   - 시스템 아키텍처 다이어그램
   - 핵심 기능 4가지 (스크리닝, RAG, Draft Copilot, 검토의견 예측)
   - 기술적 도전과 해결
   - 데이터 파이프라인 (34종 API → 9,973건 분석 → 103건 RAG)
   - 향후 계획
   - 데모 시나리오

2. 시스템 아키텍처 다이어그램 (mermaid)

3. 데이터 흐름 다이어그램 (mermaid)

4. 데모 스크립트:
   - 양평 도로 → 리스크 대시보드 → RAG 질의 → 초안 생성 (3분 데모)

---

## 실행 요약

| Step | 작업 | 프롬프트 | 예상 시간 |
|------|------|---------|----------|
| 15 | RAG 품질 테스트 | `Step 15를 실행해줘` | 15분 |
| 16 | 로컬 실행 + E2E 확인 | `Step 16을 실행해줘` | 15분 |
| 17 | 전체 문서 업데이트 | `Step 17을 실행해줘` | 15분 |
| 18 | UI/UX 디자인 개선 | `Step 18을 실행해줘` | 20~25분 |
| 19 | GitHub 업로드 + 배포 | `Step 19를 실행해줘` | 10분 |
| 20 | 포트폴리오 발표 자료 | `Step 20을 실행해줘` | 10분 |

**총 예상: 1.5~2시간**

---

## 사용 방법

```
docs/FINAL_PLAN_V4.md를 읽고 Step 15를 실행해줘.
```

Step 완료 후:

```
docs/FINAL_PLAN_V4.md를 읽고 Step 16을 실행해줘.
```

순서대로 Step 20까지.

---

## 주의사항

- Step 15 (RAG 테스트): sentence-transformers 첫 로드 시 모델 다운로드 시간 소요
- Step 16 (로컬 실행): 백엔드+프론트엔드 동시 실행 필요 (터미널 2개)
- Step 18 (UI/UX): 변경 범위가 크므로 pnpm build 꼭 확인
- Step 19 (GitHub): data/reports/raw/ 6.3GB는 반드시 .gitignore
- RAG 색인 데이터는 재구축 가능하므로 git에 포함하지 않음
