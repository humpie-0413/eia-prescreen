# Round 1: 데이터 시각화 디자인 스펙

> 작성일: 2026-03-29
> 기반: docs/ITERATION_PLAN.md 1회차

---

## 요약

대시보드에 Recharts 기반 차트 3개 추가, 기존 맵 페이지에 레이어 토글 + 리스크 마커 확장, RAG 원문 검색 독립 페이지 신설.

---

## 1. 차트 컴포넌트

### 1.1 라이브러리: Recharts

- `recharts` 패키지 추가 (React 19 호환, SVG 기반)
- `ResponsiveContainer`로 반응형 처리
- Tailwind CSS 변수를 fill/stroke에 바인딩 (하드코딩 hex 금지)

### 1.2 컴포넌트 목록

| 파일 | Props | data-testid | 설명 |
|------|-------|-------------|------|
| `src/components/charts/risk-donut-chart.tsx` | `{ data: { severity: string; count: number }[] }` | `risk-donut-{severity}` (각 arc) | 리스크 심각도별 도넛 차트. 중앙에 총 건수 라벨. |
| `src/components/charts/review-bar-chart.tsx` | `{ data: { category: string; probability_pct: number }[] }` | `review-bar-{category}` (각 bar) | 검토의견 예측 확률 수평 바 차트. 확률 내림차순 정렬. |
| `src/components/charts/pattern-bar-chart.tsx` | `{ data: Record<string, number> }` | `pattern-bar-{유형}` (각 bar) | 협의 결과 예측 수직 바 차트. 키: 협의/보완/조건부협의/재검토. |
| `src/components/charts/chart-empty-state.tsx` | `{ message?: string }` | `chart-empty-state` | 빈 데이터 fallback. 아이콘 + "데이터 없음" 메시지. |

### 1.3 색상 체계

CSS 변수로 정의하여 다크모드 자동 대응:

| Severity | Tailwind 토큰 | CSS 변수 |
|----------|--------------|----------|
| Critical | `red-500` | `--color-severity-critical` |
| Major | `orange-500` | `--color-severity-major` |
| Review | `blue-500` | `--color-severity-review` |
| Info | `gray-500` | `--color-severity-info` |
| Teal accent (바 차트) | `teal-600` | `--color-chart-primary` |

### 1.4 대시보드 통합

- 위치: 기존 `SeveritySummaryGrid` (4열 카드) 바로 아래
- 레이아웃: `grid grid-cols-1 md:grid-cols-3 gap-4`
- 각 차트를 `Card` 컴포넌트로 래핑
- 데이터 소스:
  - 도넛: `evaluationResult.summary` → `{ severity, count }[]` 변환
  - 검토의견 바: `reviewPrediction.predicted_comments` → `{ category, probability_pct }[]`
  - 패턴 바: `prediction.consultation_prediction` → `Record<string, number>`
- 빈 데이터 처리: 각 차트에서 `data.length === 0` 또는 모든 값이 0이면 `ChartEmptyState` 렌더링

### 1.5 빈 데이터 처리

- 차트별 개별 fallback (한 차트가 비어도 다른 차트는 정상 표시)
- `ChartEmptyState`: lucide-react `BarChart3` 아이콘 + 회색 메시지
- 크래시 방지: null/undefined data prop에 대해 빈 배열 기본값

---

## 2. 지도 레이어 확장

### 2.1 대상 파일

`src/app/screening/[id]/map/page.tsx` (현재 380줄)

### 2.2 추가 기능

#### 리스크 마커
- 평가 결과의 `risk_cards`에서 좌표가 있는 항목을 마커로 표시
- 좌표가 없는 리스크 카드는 사업지 주변에 오프셋 배치 (반경 내 균등 분포)
- 마커 색상: severity별 CSS 변수 사용 (Critical=빨강, Major=주황, Review=파랑)
- 마커 클릭 시 maplibregl.Popup으로 제목 + 심각도 표시
- `data-testid="risk-map"` — 맵 컨테이너

#### 레이어 토글 패널
- 맵 좌상단에 오버레이 패널 (`position: absolute`)
- 4개 토글:
  1. **반경 표시** — 기존 500m/1km 버퍼 원 (기본 ON)
  2. **리스크 마커** — 위 마커 레이어 (기본 ON)
  3. **용도지역** — 토지이용규제 GeoJSON 오버레이 (기본 ON)
  4. **생태자연도** — 생태등급 GeoJSON 오버레이 (기본 OFF)
- 각 토글: `<button role="switch" aria-checked={on} data-testid="layer-toggle-{name}">`
- 토글 상태: React `useState` (URL 상태 불필요)
- MapLibre `setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none')` 사용

#### GeoJSON 레이어
- V-world WFS 데이터를 백엔드가 프록시 → 프론트엔드는 `/api/screening/{id}/evaluate` 응답의 regulation_matches에서 geometry 추출
- 현재 evaluate 응답에 geometry가 없는 경우: 레이어 토글은 존재하되 비활성 상태 + "데이터 없음" 툴팁
- fill-opacity: 0.15, stroke: severity 색상, stroke-width: 2

#### 범례
- 맵 좌하단에 컴팩트 범례 (기존 위치 유지)
- 마커 색상 + 반경선 스타일 표시

### 2.3 콘솔 에러 0건

- MapLibre GL 초기화 에러 방어: `map.on('error', ...)` 핸들러
- GeoJSON 소스 추가 시 try-catch로 잘못된 geometry 방어

---

## 3. RAG 원문 검색 페이지

### 3.1 라우트

`/screening/[id]/rag` → `src/app/screening/[id]/rag/page.tsx`

### 3.2 스크리닝 탭 추가

`src/app/screening/[id]/layout.tsx`의 `TABS` 배열에 항목 추가:

```typescript
{ key: "rag", label: "원문 검색", icon: Search, href: (id: string) => `/screening/${id}/rag` }
```

탭 순서: 대시보드 → 리스크 맵 → 데이터 현황 → 유사사례 → 초안 생성 → **원문 검색**

### 3.3 UI 구성

```
┌─────────────────────────────────────────┐
│ 🔍 환경영향평가서 원문 검색              │
│                                         │
│ ┌─────────────────────────────┐ [검색]  │
│ │ 질의 입력 (rag-input)       │(submit) │
│ └─────────────────────────────┘         │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ 🤖 AI 답변 (rag-response)          │ │
│ │ 답변 텍스트...                      │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ 📚 참조 원문 (N건)                      │
│ ┌─────────────────────────────────────┐ │
│ │ 보고서명 · 연도 · 장절 · 유사도    │ │
│ │ 발췌문 (rag-source)                │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ⚠ AI 생성 참고용 disclaimer            │
└─────────────────────────────────────────┘
```

### 3.4 컴포넌트 상세

| 요소 | data-testid | 동작 |
|------|-------------|------|
| 질의 입력 | `rag-input` | `<input>` + Enter 키 제출 지원 |
| 검색 버튼 | `rag-submit` | 빈 질의 시 비활성 + 에러 메시지 표시 |
| 응답 카드 | `rag-response` | AI 답변 + RAG 기반 뱃지 + disclaimer |
| 출처 카드 | `rag-source` | 보고서명, 연도, 장/절, 페이지, 유사도%, 발췌문 |
| 로딩 | `rag-loading` | 스피너 + "원문을 검색하고 있습니다..." |

### 3.5 API 연동

- `POST /api/rag/query` — `{ question: string, n_results: 5, project_type: string }`
- 응답: `{ answer, sources[], total_indexed, disclaimer }`
- E2E 스텁: `e2e/fixtures/api-stubs.ts`의 `RAG_RESPONSE` 이미 존재
- 에러 처리: try-catch → 에러 메시지 카드 표시 (앱 크래시 안 함)

### 3.6 빈 질의 검증

- 입력값 `trim()` 후 빈 문자열이면 제출 차단
- 검색 버튼 disabled + "질문을 입력하세요" 안내 텍스트

---

## 4. 신규/수정 파일 목록

### 신규 파일 (5개)

| 파일 | 설명 |
|------|------|
| `src/components/charts/risk-donut-chart.tsx` | 리스크 도넛 차트 |
| `src/components/charts/review-bar-chart.tsx` | 검토의견 수평 바 차트 |
| `src/components/charts/pattern-bar-chart.tsx` | 패턴 수직 바 차트 |
| `src/components/charts/chart-empty-state.tsx` | 차트 빈 데이터 fallback |
| `src/app/screening/[id]/rag/page.tsx` | RAG 원문 검색 페이지 |
| *(없음 — `src/lib/api.ts`에 `queryRag` 함수 추가)* | |

### 수정 파일 (5개)

| 파일 | 변경 |
|------|------|
| `src/app/screening/[id]/dashboard/page.tsx` | 차트 섹션 import + 렌더링 추가 (~30줄) |
| `src/app/screening/[id]/map/page.tsx` | 레이어 토글 패널 + 리스크 마커 + GeoJSON 레이어 (~150줄) |
| `src/app/screening/[id]/layout.tsx` | TABS 배열에 "원문 검색" 항목 추가 |
| `src/lib/api.ts` | `queryRag()` 함수 추가 |
| `package.json` | `recharts` 의존성 추가 |

### E2E (이미 완료)

- `e2e/fixtures/api-stubs.ts` — `RAG_RESPONSE` 포함
- `e2e/helpers/mock-api.ts` — `/api/rag/**` 라우트 포함

---

## 5. 수락 기준 (ITERATION_PLAN.md 기준)

- [ ] 차트 3개가 Props로 데이터를 받아 SVG 렌더링
- [ ] 각 동적 요소에 data-testid 존재
- [ ] 빈 데이터 시 fallback 표시 (크래시 안 함)
- [ ] 지도 컨테이너 + 레이어 토글 3개+ 존재
- [ ] RAG 질의 → 응답 + 출처 카드 렌더링
- [ ] pnpm build 클린, lint 에러 0건
