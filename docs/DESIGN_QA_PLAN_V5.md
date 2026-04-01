# EIA Pre-Screen — 디자인 + QA 검증 실행 계획 v5

> 작성일: 2026-03-29
> 선행 완료: Step 15~17 (RAG 94점, E2E 105/105, 문서 갱신)
> 목표: Supanova 디자인 스킬 적용 → Playwright QA 검증 → 배포

---

## Step 18: Supanova 디자인 스킬 설치 + 적용

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 18을 실행해줘.
```

**상세 작업**:

1. Supanova 디자인 스킬 설치:
   - git clone https://github.com/uxjoseph/supanova-design-skill.git /mnt/skills/user/supanova-design
   - SKILL.md 읽고 디자인 원칙 파악
   - 프로젝트에 적용할 디자인 토큰/컴포넌트 식별

2. 전체 페이지 디자인 적용 (8개 라우트):

   a. 랜딩 페이지 (/)
      - 히어로 섹션: 프로젝트 소개 + "스크리닝 시작" CTA
      - 주요 기능 3개 카드 (리스크 분석, AI 초안 생성, 검토의견 예측)
      - 데이터 현황 숫자 (103건 보고서, 9,973건 분석, 64개 규칙)
      - 기술 스택 섹션

   b. 스크리닝 생성 (/screening/new)
      - 사업유형 17개 선택 UI (아이콘 + 라벨 그리드)
      - 좌표 입력 + 지도 프리뷰
      - 입력 폼 스텝 구조 (사업정보 → 위치 → 규모 → 확인)

   c. 대시보드 (/screening/[id]/dashboard)
      - 리스크 요약 히어로 카드 (Critical/Major/Moderate/Review 카운트)
      - 리스크 맵 (MapLibre + V-world 레이어 오버레이)
      - 과거 패턴 예측 섹션 (확률 바 차트)
      - 검토의견 예측 카드 (확률순 정렬)
      - 품질 체크 결과 카드

   d. 유사사례 (/screening/[id]/cases)
      - 카드 그리드 레이아웃
      - 필터 사이드바 (사업유형, 지역, 연도)
      - 사례 상세 모달

   e. 초안 생성 (/screening/[id]/draft)
      - 챕터별 아코디언 UI
      - 배지 시스템 (자동생성/현장조사필요/전문가검토필요)
      - RAG 참조 출처 하이라이트
      - AI 면책 문구 배너

   f. 부지 비교 (/screening/compare)
      - 3개 부지 Side-by-side 카드
      - 리스크 비교 테이블
      - 레이더 차트 (도메인별 비교)

   g. 보고서 (/screening/[id]/report)
      - 보고서 유형 선택 카드
      - 미리보기 + PDF 다운로드

   h. RAG 질의 (대시보드 내 섹션 또는 별도 탭)
      - 채팅형 UI
      - 출처 카드 (보고서명, 페이지, 유사도)

3. 공통 디자인 요소:
   - 색상: 환경 톤 (teal-600 primary, green-500 accent)
   - 리스크 severity 색상 고정 (Critical=red-600, Major=orange-500, Moderate=amber-400, Review=blue-400)
   - 타이포그래피: Pretendard (한국어) + Inter (영문)
   - 아이콘: lucide-react
   - 애니메이션: framer-motion (페이지 전환, 카드 등장)
   - 스켈레톤 로딩 (shimmer)
   - 모바일 반응형

4. 지도 시각화 강화:
   - V-world 용도지역 GeoJSON 오버레이
   - 부지 반경 원 표시 (distance buffer)
   - 리스크 포인트 마커 (severity별 색상/크기)
   - WMS 토지피복도 배경 레이어 토글
   - 주변 환평 사업 마커 (좌표 기반 검색 API 결과)

5. pnpm build 확인

---

## Step 19: Playwright E2E QA 검증

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 19를 실행해줘.
```

**상세 작업**:

1. Playwright 설치 + 설정:
   ```
   cd frontend
   pnpm add -D @playwright/test
   npx playwright install chromium
   ```

2. playwright.config.ts 생성:
   - baseURL: http://localhost:3000
   - webServer: pnpm dev (자동 실행)
   - retries: 2
   - screenshot: only-on-failure
   - video: retain-on-failure

3. E2E 테스트 작성 (frontend/e2e/):

   a. landing.spec.ts — 랜딩 페이지
      - 페이지 로드 + 주요 요소 존재 확인
      - "스크리닝 시작" 버튼 클릭 → /screening/new 이동
      - 반응형 (모바일 뷰포트)

   b. screening-new.spec.ts — 스크리닝 생성
      - 사업유형 17개 렌더링 확인
      - 유형 선택 → 폼 입력 → 제출
      - 필수 필드 검증 (빈 제출 시 에러)
      - 제출 성공 → 대시보드 리다이렉트

   c. dashboard.spec.ts — 대시보드
      - 리스크 카드 렌더링 (양평: Major 4건)
      - 탭 네비게이션 (대시보드/유사사례/초안/보고서)
      - 검토의견 예측 버튼 → 결과 표시
      - 품질 체크 버튼 → 결과 표시
      - 지도 렌더링 확인

   d. draft.spec.ts — 초안 생성
      - "초안 생성" 버튼 클릭 → 18섹션 생성
      - 아코디언 열기/닫기
      - 배지 표시 확인
      - AI 면책 문구 표시 확인

   e. compare.spec.ts — 부지 비교
      - 3개 부지 선택 → 비교 실행
      - Side-by-side 테이블 렌더링
      - PDF 다운로드 버튼 존재

   f. rag.spec.ts — RAG 질의
      - 질의 입력 → 응답 표시
      - 출처 카드 표시
      - 로딩 상태 확인

   g. accessibility.spec.ts — 접근성
      - Tab 키 순서
      - aria-label 존재
      - focus-visible 스타일
      - 색상 대비 (axe-core)

   h. responsive.spec.ts — 반응형
      - 모바일 (375px)
      - 태블릿 (768px)
      - 데스크탑 (1280px)
      - 네비게이션 메뉴 동작

4. 테스트 실행:
   ```
   cd frontend
   npx playwright test --reporter=html
   ```

5. 실패 테스트에 대해 스크린샷 + 에러 로그 분석

---

## Step 20: QA 엔지니어 모드 검증

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 20을 실행해줘.
```

**상세 작업**:

이 Step에서 Claude Code는 다음 역할로 전환합니다:

```
당신은 지금부터 EIA Pre-Screen 프로젝트의 '엄격한 QA 엔지니어 및 코드 평가자(Evaluator)' 역할을 수행합니다.
새로운 기능을 임의로 기획하거나 코드를 무작정 생성하지 마십시오.

[핵심 임무]
1. 현재 작성된 코드베이스와 Playwright E2E 테스트 실행 결과를 교차 검증하십시오.
2. 터미널의 테스트 실패 로그, DOM 렌더링 누락, 라우팅 오류, 논리적 결함을 찾아내십시오.
3. 발견된 문제의 '근본 원인'과 '해결을 위한 최소한의 코드 수정 방안'만 직설적으로 제시하십시오.

[프로젝트 컨텍스트]
- 환경영향평가 사전검토 시스템 (EIA Pre-Screen)
- Next.js 16 + TypeScript + Tailwind + shadcn/ui (프론트엔드)
- FastAPI + SQLAlchemy + PostGIS (백엔드)
- DeepSeek V3 via OpenRouter (LLM)
- ChromaDB + sentence-transformers (RAG)
- 8개 라우트, 35개 API 엔드포인트, 174개 pytest, 103건 환평 보고서 RAG
- DEMO_MODE=true에서 DB 없이 동작

[실행 및 평가 지침]
1. 허가된 권한을 사용하여 다음 명령을 순서대로 실행하고 결과를 분석하십시오:
   - cd frontend && npx playwright test --reporter=list 2>&1
   - cd .. && python -m pytest tests/ backend/tests/ -v 2>&1
   - cd frontend && pnpm build 2>&1
   - cd frontend && pnpm lint 2>&1

2. 코드나 구현 방식에 대한 주관적인 칭찬, 긍정적 수식어는 철저히 배제하십시오.

3. 수정이 필요한 경우 다음 형식으로 출력하십시오:
   [파일 경로]
   [기존 코드의 문제점]
   [정확한 수정 코드]

4. 장황하거나 비효율적인 로직이 발견되면 간결하게 리팩토링할 방법을 지적하십시오.

5. 에러 로그가 길 경우, 가장 치명적인 에러(블로커)부터 순차적으로 해결책을 제시하십시오.

6. 발견된 이슈를 다음 우선순위로 분류하십시오:
   - P0 (블로커): 빌드 실패, 라우팅 깨짐, 핵심 기능 미동작
   - P1 (크리티컬): 데이터 표시 오류, API 연동 실패, 상태 관리 버그
   - P2 (메이저): UI 깨짐, 반응형 미대응, 접근성 위반
   - P3 (마이너): 스타일 불일치, 타이포, 콘솔 워닝

7. 모든 P0, P1 이슈를 수정한 후에만 "검증 통과"를 선언하십시오.
```

실행 흐름:
1. Playwright E2E 테스트 실행 → 실패 목록 수집
2. pytest 전체 실행 → 실패 목록 수집
3. pnpm build → TypeScript 에러 수집
4. pnpm lint → ESLint 경고/에러 수집
5. 전체 이슈를 P0~P3으로 분류
6. P0부터 순차 수정
7. 수정 후 전체 재실행 → 통과 확인
8. 최종 결과 보고서 생성: docs/QA_REPORT.md

---

## Step 21: 최종 수정 + 재검증

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 21을 실행해줘.
```

**상세 작업**:

1. Step 20에서 발견된 P0~P1 이슈 전부 수정
2. Playwright 재실행 → 전체 통과 확인
3. pytest 재실행 → 전체 통과 확인
4. pnpm build → 클린 확인
5. pnpm lint → 경고 0개 확인
6. 3개 시나리오 수동 확인 (양평/세종/보령)
7. docs/QA_REPORT.md에 최종 결과 기록:
   - 발견된 총 이슈 수
   - P0/P1/P2/P3 분류
   - 수정된 이슈 수
   - 미수정 이슈 (있으면 사유)
   - 최종 테스트 통과율

---

## Step 22: GitHub 업로드

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 22를 실행해줘.
```

**상세 작업**:

1. .gitignore 최종 점검:
   - data/reports/raw/ (6.3GB PDF 제외)
   - data/bulk/raw/ (벌크 JSON 제외)
   - chroma_db/ (재구축 가능)
   - .env, node_modules/, __pycache__/, .next/
   - playwright-report/, test-results/

2. 커밋 구조 (의미 단위):
   - feat: project setup + risk engine
   - feat: case library + LLM integration
   - feat: site comparison + auth
   - feat: data acquisition + API integration
   - feat: pattern analysis + draft copilot
   - feat: EIASS crawling + RAG system
   - feat: review prediction + quality check
   - style: UI/UX design improvements
   - test: playwright E2E + QA verification
   - docs: documentation update

3. GitHub 리포지토리 생성 안내
4. GitHub Actions CI 워크플로우 확인
5. 릴리즈 태그: v1.0.0

---

## Step 23: 포트폴리오 발표 자료

**Claude Code 프롬프트**:
```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 23을 실행해줘.
```

**상세 작업**:

1. docs/PORTFOLIO_PRESENTATION.md:
   - 프로젝트 소개 (한 줄)
   - 해결하려는 문제
   - 시스템 아키텍처 다이어그램 (mermaid)
   - 데이터 파이프라인 다이어그램 (mermaid)
   - 핵심 기능 4가지
   - 기술적 도전과 해결
   - 데모 시나리오 (3분 스크립트)
   - 향후 계획

2. 아키텍처 다이어그램 파일 (mermaid → SVG)

3. 데모 스크린샷 캡처 스크립트 (playwright)

---

## 실행 요약

| Step | 작업 | 프롬프트 | 예상 시간 |
|------|------|---------|----------|
| 18 | Supanova 디자인 적용 | `Step 18을 실행해줘` | 25~30분 |
| 19 | Playwright E2E 작성 | `Step 19를 실행해줘` | 15~20분 |
| 20 | QA 엔지니어 모드 검증 | `Step 20을 실행해줘` | 15~20분 |
| 21 | 최종 수정 + 재검증 | `Step 21을 실행해줘` | 10~15분 |
| 22 | GitHub 업로드 | `Step 22를 실행해줘` | 10분 |
| 23 | 포트폴리오 발표 자료 | `Step 23을 실행해줘` | 10분 |

**총 예상: 1.5~2시간**

---

## 사용 방법

```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 18을 실행해줘.
```

Step 완료 후:

```
docs/DESIGN_QA_PLAN_V5.md를 읽고 Step 19를 실행해줘.
```

순서대로 Step 23까지.
