# EIA Pre-Screen — 이터레이션 계획 v3

> 작성일: 2026-03-29
> 기반: Claude Harness Framework
> 스킬: Supanova Design Skill, Playwright E2E

---

## 하네스 규칙

1. **QA는 새 세션에서 실행** — 생성자가 자기 결과를 평가하지 않음
2. **수락 기준** — 각 Step에 측정 가능한 AC 명시, 전부 통과해야 완료
3. **API 스텁** — Playwright에서 page.route()로 외부 API 고정, 테스트 Flakiness 제거
4. **시각적 확인은 사용자** — Claude는 데이터 바인딩/타입/에러만 검증, 렌더링 품질은 사용자가 확인
5. **코드 레벨 디자인 검증** — 하드코딩 색상, 간격 일관성, 아이콘 통일성은 Claude가 검증

---

## 사전 작업

**프롬프트**:
```
docs/ITERATION_PLAN.md를 읽고 사전 작업을 실행해줘.
```

**작업**:
1. CLAUDE.md에 자동 검증 hook 추가 (파일 수정 후 pnpm build + lint)
2. frontend/e2e/fixtures/api-stubs.ts — 에어코리아, V-world, 백엔드 API, DeepSeek 스텁 (최소 6개)
3. frontend/e2e/helpers/mock-api.ts — setupApiMocks(), setupErrorMocks(), setupEmptyMocks()
4. 기존 E2E 테스트에 setupApiMocks() 적용
5. 전체 E2E 통과 확인

**수락 기준**:
- [ ] api-stubs.ts에 6개+ API 스텁
- [ ] mock-api.ts에 3개 함수
- [ ] 기존 E2E 전체 통과
- [ ] pnpm build 클린, lint 에러 0건

---

## 1회차: 데이터 시각화

**프롬프트 (생성)**:
```
docs/ITERATION_PLAN.md를 읽고 1회차 디자인을 실행해줘. Supanova 디자인 스킬을 적용할 것.
```

**작업**:
1. 대시보드 차트 (recharts)
   - 리스크 도넛 차트 (severity별 비율, data-testid="risk-donut-{severity}")
   - 검토의견 바 차트 (확률%, data-testid="review-bar-{항목}")
   - 과거 패턴 막대 차트 (유형별 분포, data-testid="pattern-bar-{유형}")
   - 빈 데이터 시 "데이터 없음" fallback

2. 지도 시각화 강화
   - V-world GeoJSON 오버레이 (data-testid="risk-map")
   - 부지 반경 원, 리스크 마커 (severity별 색상)
   - 레이어 토글 (data-testid="layer-toggle-{name}", aria-checked)

3. RAG 질의 UI
   - 입력 필드 + 제출 (data-testid="rag-input", "rag-submit")
   - 응답 카드 + 출처 (data-testid="rag-response", "rag-source")
   - 로딩 인디케이터, 빈 질의 검증

4. pnpm build + lint 확인

**수락 기준**:
- [ ] 차트 3개가 Props로 데이터를 받아 SVG 렌더링
- [ ] 각 동적 요소에 data-testid 존재
- [ ] 빈 데이터 시 fallback 표시 (크래시 안 함)
- [ ] 지도 컨테이너 + 레이어 토글 3개+ 존재
- [ ] RAG 질의 → 응답 + 출처 카드 렌더링
- [ ] pnpm build 클린, lint 에러 0건

**프롬프트 (Playwright)**:
```
docs/ITERATION_PLAN.md를 읽고 1회차 Playwright를 실행해줘.
```

frontend/e2e/r1/ 에 테스트 작성:
- charts.spec.ts — SVG 존재, data-testid 값 = 스텁, 빈 데이터 fallback (4개+)
- map-layers.spec.ts — 컨테이너 존재, 토글 aria-checked, 콘솔 에러 0건 (3개+)
- rag-ui.spec.ts — 질의 → 응답 렌더링, 출처 존재, 빈 질의 검증 (4개+)
- 전체 setupApiMocks() 적용

**프롬프트 (QA — 반드시 새 세션)**:
```
당신은 EIA Pre-Screen의 '데이터 바인딩 및 디자인 일관성 검사자'입니다.
이전 생성 과정의 의도나 맥락을 무시하고 결과물만 평가하십시오.
시각적 렌더링 품질은 검증 범위에서 제외합니다.

[검증 범위]
1. API 응답 → 차트/지도 Props 타입/구조 정합성
2. data-testid가 모든 동적 요소에 존재
3. 빈 데이터/에러 시 fallback UI 렌더링 (크래시 없음)
4. TypeScript 타입 불일치 0건
5. 하드코딩 hex 색상 0건 (CSS 변수/Tailwind 토큰만)
6. 간격 일관성, lucide-react 아이콘만 사용
7. 콘솔 런타임 에러 0건

[실행]
1. cd frontend && npx playwright test --reporter=list
2. cd .. && python -m pytest tests/ backend/tests/ -v
3. cd frontend && pnpm build && pnpm lint
4. grep -rn "#[0-9a-fA-F]\{3,6\}" frontend/src/ --include="*.tsx"

[출력] P0~P3 분류. P0/P1만 수정.
```

**QA 후 → 사용자 시각적 확인**:
- [ ] 도넛 차트가 리스크 비율을 반영하는가
- [ ] 바 차트 확률(%) 수치가 읽기 쉬운가
- [ ] 지도 레이어 토글이 동작하는가
- [ ] RAG 응답이 읽기 쉬운가
- [ ] 전체 색상/레이아웃이 자연스러운가

---

## 2회차: 인터랙션 + 엣지케이스

**프롬프트 (생성)**:
```
docs/ITERATION_PLAN.md를 읽고 2회차 디자인을 실행해줘. Supanova 디자인 스킬을 적용할 것. 이전 회차의 구현 세부사항은 무시할 것.
```

**작업**:
1. 마이크로 인터랙션
   - 리스크 카드 호버 → 툴팁 (data-testid="risk-tooltip")
   - 탭 전환 슬라이드, 버튼 피드백, 숫자 카운트업
   - 토스트 알림 (sonner)

2. 빈 상태/에러 처리 공통 컴포넌트
   - EmptyState (data-testid="empty-state")
   - ErrorState (data-testid="error-state")
   - LoadingSkeleton (data-testid="loading-skeleton")
   - 모든 데이터 fetch 지점에 3상태 적용

3. 폼 UX
   - 좌표 실시간 유효성 (위도 33~43, 경도 124~132)
   - 사업유형 미선택 경고
   - 제출 후 프로그레스 바

4. pnpm build + lint 확인

**수락 기준**:
- [ ] 3개 공통 컴포넌트 존재 (EmptyState, ErrorState, LoadingSkeleton)
- [ ] API 에러 시 ErrorState 렌더링 (앱 크래시 안 함)
- [ ] 좌표 범위 밖 입력 시 에러 메시지
- [ ] 호버 툴팁 DOM 생성
- [ ] framer-motion/CSS transition 사용 (setTimeout 금지)
- [ ] pnpm build 클린, lint 에러 0건

**프롬프트 (Playwright)**:
```
docs/ITERATION_PLAN.md를 읽고 2회차 Playwright를 실행해줘. 이전 회차의 구현 세부사항은 무시할 것.
```

frontend/e2e/r2/:
- error-states.spec.ts — setupErrorMocks() → error-state/empty-state 확인 (3개+)
- form-validation.spec.ts — 빈/범위밖 입력 → 에러 메시지 (3개+)
- interactions.spec.ts — 호버 툴팁, 토스트 (2개+)

**프롬프트 (QA — 반드시 새 세션)**:
```
당신은 EIA Pre-Screen의 '에러 처리 및 엣지케이스 검사자'입니다.
이전 생성 과정의 의도나 맥락을 무시하고 결과물만 평가하십시오.
시각적 렌더링 품질은 검증 범위에서 제외합니다.

[검증 범위]
1. API 에러(500/403/timeout) 시 ErrorState 렌더링
2. 빈 데이터 시 EmptyState 렌더링 (크래시 없음)
3. 폼 유효성이 모든 엣지케이스 커버
4. try-catch 누락 unhandled rejection 없음
5. 하드코딩 hex 색상 0건, 간격 일관성

[실행] 동일 (playwright, pytest, build, lint, grep)
[출력] P0~P3 분류. P0/P1만 수정.
```

**QA 후 → 사용자 시각적 확인**:
- [ ] 에러 상태 UI가 자연스러운가
- [ ] 스켈레톤 로딩이 적절한가
- [ ] 호버 툴팁이 읽기 쉬운가
- [ ] 토스트 위치/타이밍이 적절한가
- [ ] 폼 에러 메시지가 명확한가

---

## 3회차: 성능 + 접근성 + 최종

**프롬프트 (생성)**:
```
docs/ITERATION_PLAN.md를 읽고 3회차 디자인을 실행해줘. 이전 회차의 구현 세부사항은 무시할 것.
```

**작업**:
1. 성능 최적화
   - next/dynamic: 지도, 차트 클라이언트 전용 로드
   - Suspense fallback (LoadingSkeleton)
   - 번들 분석 → 500KB 초과 청크 분리

2. 접근성 (WCAG 2.1 AA)
   - @axe-core/playwright 설치
   - 전체 aria-label 보강, 키보드 탐색 (Tab/Enter/Space)
   - focus trap (모달/드롭다운), skip navigation
   - 색상 대비 4.5:1

3. SEO
   - 각 페이지 title, meta description
   - h1 한 개만 존재

4. pnpm build + lint 확인

**수락 기준**:
- [ ] 지도/차트가 dynamic import 사용
- [ ] 메인 번들 500KB 이하
- [ ] axe-core violation 0건 (critical + serious)
- [ ] Tab 키 전체 순회 가능
- [ ] skip-nav 링크 존재
- [ ] 각 페이지 고유 title 존재
- [ ] pnpm build 클린, lint 에러 0건

**프롬프트 (Playwright)**:
```
docs/ITERATION_PLAN.md를 읽고 3회차 Playwright를 실행해줘. 이전 회차의 구현 세부사항은 무시할 것.
```

frontend/e2e/r3/:
- performance.spec.ts — DOMContentLoaded 3초, 번들 확인
- accessibility.spec.ts — axe-core 0건, Tab 순회, Enter/Space
- seo.spec.ts — title, meta, h1 존재

**프롬프트 (QA — 반드시 새 세션)**:
```
당신은 EIA Pre-Screen의 '최종 릴리즈 검증자'입니다.
이전 생성 과정의 의도나 맥락을 무시하고 결과물만 평가하십시오.
시각적 렌더링 품질은 검증 범위에서 제외합니다.

[검증 범위]
1. 전체 Playwright E2E (기존 + R1 + R2 + R3) 통과
2. 전체 pytest 통과
3. pnpm build 클린, lint 에러 0건
4. axe-core violation 0건
5. 하드코딩 hex 색상 0건
6. 콘솔 런타임 에러 0건
7. 메인 번들 500KB 이하

[판정] 모든 항목 통과 → "릴리즈 가능". 실패 → 수정 방안 제시.
```

**QA 후 → 사용자 최종 확인**:
- [ ] 랜딩 페이지 첫인상
- [ ] 스크리닝 → 대시보드 전체 흐름
- [ ] 차트/지도가 데이터 반영
- [ ] 모바일(375px) 깨짐 없음
- [ ] 다크모드 가독성
- [ ] 애니메이션 자연스러움
- [ ] 에러/빈 상태 사용자 친화

---

## 실행 흐름

| 순서 | 작업 | 프롬프트 | 세션 |
|------|------|---------|------|
| 1 | 사전 작업 | `사전 작업을 실행해줘` | 세션 1 |
| 2 | 1회차 디자인 | `1회차 디자인을 실행해줘` | 세션 2 |
| 3 | 1회차 Playwright | `1회차 Playwright를 실행해줘` | 세션 2 (이어서) |
| 4 | 1회차 QA | QA 프롬프트 복사 | **새 세션** |
| 5 | **사용자 시각 확인** | 브라우저에서 직접 | — |
| 6 | 2회차 디자인 | `2회차 디자인을 실행해줘` | 세션 3 |
| 7 | 2회차 Playwright | `2회차 Playwright를 실행해줘` | 세션 3 (이어서) |
| 8 | 2회차 QA | QA 프롬프트 복사 | **새 세션** |
| 9 | **사용자 시각 확인** | 브라우저에서 직접 | — |
| 10 | 3회차 디자인 | `3회차 디자인을 실행해줘` | 세션 4 |
| 11 | 3회차 Playwright | `3회차 Playwright를 실행해줘` | 세션 4 (이어서) |
| 12 | 3회차 QA | QA 프롬프트 복사 | **새 세션** |
| 13 | **사용자 최종 확인** | 브라우저에서 직접 | — |
