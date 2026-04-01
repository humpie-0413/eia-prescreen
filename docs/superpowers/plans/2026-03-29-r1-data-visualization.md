# Round 1: 데이터 시각화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대시보드에 Recharts 기반 차트 3개 추가, 지도 페이지에 레이어 토글 + 리스크 마커 확장, RAG 원문 검색 독립 페이지 신설.

**Architecture:** 차트 컴포넌트는 `src/components/charts/`에 독립 파일로 분리하고 대시보드에서 import. 지도는 기존 `map/page.tsx`에 레이어 토글 패널과 리스크 마커를 추가. RAG 페이지는 새 라우트 `screening/[id]/rag/page.tsx`로 생성하고 layout.tsx 탭에 추가.

**Tech Stack:** Recharts (SVG 차트), MapLibre GL JS (지도 레이어), Next.js 16 App Router, Tailwind CSS v4, shadcn/ui Card, lucide-react 아이콘.

**Spec:** `docs/superpowers/specs/2026-03-29-r1-data-visualization-design.md`

---

## File Structure

### New files (5)

| File | Responsibility |
|------|---------------|
| `src/components/charts/chart-empty-state.tsx` | 차트 빈 데이터 fallback UI (아이콘 + 메시지) |
| `src/components/charts/risk-donut-chart.tsx` | 리스크 심각도별 도넛 차트 (Recharts PieChart) |
| `src/components/charts/review-bar-chart.tsx` | 검토의견 예측 확률 수평 바 차트 (Recharts BarChart) |
| `src/components/charts/pattern-bar-chart.tsx` | 협의결과 예측 수직 바 차트 (Recharts BarChart) |
| `src/app/screening/[id]/rag/page.tsx` | RAG 원문 검색 페이지 (입력 → AI 답변 → 출처 카드) |

### Modified files (5)

| File | Change |
|------|--------|
| `package.json` | `recharts` 의존성 추가 |
| `src/app/globals.css` | severity CSS 변수 5개 추가 |
| `src/app/screening/[id]/dashboard/page.tsx` | 차트 3개 import + 렌더링 (~30줄) |
| `src/app/screening/[id]/map/page.tsx` | 레이어 토글 패널 + 리스크 마커 (~120줄) |
| `src/app/screening/[id]/layout.tsx` | TABS에 "원문 검색" 항목 추가 |
| `src/lib/api.ts` | `queryRag()` 함수 추가 |

---

## Task 1: Install Recharts + Add CSS Variables

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Install recharts**

```bash
cd frontend && pnpm add recharts
```

Expected: `recharts` appears in `package.json` dependencies.

- [ ] **Step 2: Add severity CSS variables to globals.css**

In `src/app/globals.css`, add after `:root {` block's existing variables (before the closing `}`), at the end of the `:root` block:

```css
  /* ── Severity chart colors ── */
  --color-severity-critical: oklch(0.637 0.237 25.331);
  --color-severity-major: oklch(0.702 0.183 54.116);
  --color-severity-review: oklch(0.623 0.214 259.815);
  --color-severity-info: oklch(0.551 0.027 264.364);
  --color-chart-primary: oklch(0.600 0.118 184.704);
```

And in the `.dark` block, add:

```css
  /* ── Severity chart colors (dark) ── */
  --color-severity-critical: oklch(0.704 0.191 22.216);
  --color-severity-major: oklch(0.752 0.183 55.934);
  --color-severity-review: oklch(0.707 0.165 254.624);
  --color-severity-info: oklch(0.610 0.027 264.364);
  --color-chart-primary: oklch(0.696 0.108 180.426);
```

- [ ] **Step 3: Verify build passes**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add package.json pnpm-lock.yaml src/app/globals.css
git commit -m "feat: add recharts dependency and severity CSS variables"
```

---

## Task 2: Chart Empty State Component

**Files:**
- Create: `frontend/src/components/charts/chart-empty-state.tsx`

- [ ] **Step 1: Create chart-empty-state.tsx**

```tsx
import { BarChart3 } from "lucide-react";

interface ChartEmptyStateProps {
  message?: string;
}

export function ChartEmptyState({
  message = "데이터 없음",
}: ChartEmptyStateProps) {
  return (
    <div
      data-testid="chart-empty-state"
      className="flex flex-col items-center justify-center py-8 text-muted-foreground"
    >
      <BarChart3 className="size-10 mb-2 opacity-40" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/charts/chart-empty-state.tsx
git commit -m "feat: add ChartEmptyState fallback component"
```

---

## Task 3: Risk Donut Chart

**Files:**
- Create: `frontend/src/components/charts/risk-donut-chart.tsx`

- [ ] **Step 1: Create risk-donut-chart.tsx**

```tsx
"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { ChartEmptyState } from "./chart-empty-state";

interface DonutDatum {
  severity: string;
  count: number;
}

interface RiskDonutChartProps {
  data: DonutDatum[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--color-severity-critical)",
  major: "var(--color-severity-major)",
  review: "var(--color-severity-review)",
  info: "var(--color-severity-info)",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "Critical",
  major: "Major",
  review: "Review",
  info: "Info",
};

export function RiskDonutChart({ data }: RiskDonutChartProps) {
  const filtered = (data ?? []).filter((d) => d.count > 0);
  const total = filtered.reduce((sum, d) => sum + d.count, 0);

  if (filtered.length === 0) {
    return <ChartEmptyState message="리스크 데이터 없음" />;
  }

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-[160px] h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={filtered}
              dataKey="count"
              nameKey="severity"
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={2}
              strokeWidth={0}
            >
              {filtered.map((entry) => (
                <Cell
                  key={entry.severity}
                  fill={SEVERITY_COLORS[entry.severity] ?? "#6b7280"}
                  data-testid={`risk-donut-${entry.severity}`}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold">{total}</span>
        </div>
      </div>
      <div className="flex gap-3 mt-2 flex-wrap justify-center">
        {filtered.map((d) => (
          <span key={d.severity} className="flex items-center gap-1 text-xs">
            <span
              className="inline-block size-2 rounded-full"
              style={{ backgroundColor: SEVERITY_COLORS[d.severity] }}
            />
            {SEVERITY_LABELS[d.severity] ?? d.severity} {d.count}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/charts/risk-donut-chart.tsx
git commit -m "feat: add RiskDonutChart component"
```

---

## Task 4: Review Bar Chart (Horizontal)

**Files:**
- Create: `frontend/src/components/charts/review-bar-chart.tsx`

- [ ] **Step 1: Create review-bar-chart.tsx**

```tsx
"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import { ChartEmptyState } from "./chart-empty-state";

interface ReviewBarDatum {
  category: string;
  probability_pct: number;
}

interface ReviewBarChartProps {
  data: ReviewBarDatum[];
}

export function ReviewBarChart({ data }: ReviewBarChartProps) {
  const sorted = [...(data ?? [])].sort(
    (a, b) => b.probability_pct - a.probability_pct,
  );

  if (sorted.length === 0) {
    return <ChartEmptyState message="검토의견 예측 데이터 없음" />;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(sorted.length * 36, 80)}>
      <BarChart data={sorted} layout="vertical" margin={{ left: 0, right: 40, top: 4, bottom: 4 }}>
        <XAxis type="number" domain={[0, 100]} hide />
        <YAxis
          type="category"
          dataKey="category"
          width={50}
          tick={{ fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Bar
          dataKey="probability_pct"
          radius={[0, 4, 4, 0]}
          barSize={18}
        >
          {sorted.map((entry) => (
            <Cell
              key={entry.category}
              fill="var(--color-chart-primary)"
              data-testid={`review-bar-${entry.category}`}
            />
          ))}
          <LabelList
            dataKey="probability_pct"
            position="right"
            formatter={(v: number) => `${v}%`}
            style={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/charts/review-bar-chart.tsx
git commit -m "feat: add ReviewBarChart component"
```

---

## Task 5: Pattern Bar Chart (Vertical)

**Files:**
- Create: `frontend/src/components/charts/pattern-bar-chart.tsx`

- [ ] **Step 1: Create pattern-bar-chart.tsx**

```tsx
"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import { ChartEmptyState } from "./chart-empty-state";

interface PatternBarChartProps {
  data: Record<string, number>;
}

const PATTERN_COLORS: Record<string, string> = {
  "협의": "var(--color-severity-info)",
  "보완": "var(--color-severity-major)",
  "조건부협의": "var(--color-chart-primary)",
  "재검토": "var(--color-severity-critical)",
};

export function PatternBarChart({ data }: PatternBarChartProps) {
  const entries = Object.entries(data ?? {}).map(([name, value]) => ({
    name,
    value,
  }));

  if (entries.length === 0 || entries.every((e) => e.value === 0)) {
    return <ChartEmptyState message="패턴 데이터 없음" />;
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={entries} margin={{ top: 16, right: 4, bottom: 4, left: 4 }}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis hide domain={[0, 100]} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={36}>
          {entries.map((entry) => (
            <Cell
              key={entry.name}
              fill={PATTERN_COLORS[entry.name] ?? "var(--color-chart-primary)"}
              data-testid={`pattern-bar-${entry.name}`}
            />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            formatter={(v: number) => `${v}%`}
            style={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/components/charts/pattern-bar-chart.tsx
git commit -m "feat: add PatternBarChart component"
```

---

## Task 6: Dashboard Chart Integration

**Files:**
- Modify: `frontend/src/app/screening/[id]/dashboard/page.tsx` (lines 1-17 imports, line 1070 after SeveritySummaryGrid)

- [ ] **Step 1: Add chart imports to dashboard**

Add these imports at the top of `dashboard/page.tsx`, after the existing imports (after line 17):

```tsx
import { RiskDonutChart } from "@/components/charts/risk-donut-chart";
import { ReviewBarChart } from "@/components/charts/review-bar-chart";
import { PatternBarChart } from "@/components/charts/pattern-bar-chart";
```

- [ ] **Step 2: Add chart section in render**

In the return JSX, after `<SeveritySummaryGrid cards={riskCards} />` (line 1070) and before `{/* ── Risk Card Grid ── */}` (line 1072), add:

```tsx
      {/* ── Charts ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">리스크 분포</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskDonutChart
              data={SEVERITY_ORDER.map((sev) => ({
                severity: sev,
                count: countBySeverity(riskCards)[sev],
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">검토의견 예측</CardTitle>
          </CardHeader>
          <CardContent>
            <ReviewBarChart
              data={predictedComments.map((c) => ({
                category: c.category,
                probability_pct: c.probability_pct,
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">과거 패턴</CardTitle>
          </CardHeader>
          <CardContent>
            <PatternBarChart data={consultationPrediction} />
          </CardContent>
        </Card>
      </div>
```

Notes:
- `SEVERITY_ORDER` and `countBySeverity` are already defined in the file (lines 23-36).
- `predictedComments` is already a state variable (line 863).
- `consultationPrediction` is already a state variable (line 868).
- `Card`, `CardHeader`, `CardTitle`, `CardContent` are already imported (line 7).

- [ ] **Step 3: Verify build + lint**

```bash
cd frontend && pnpm build && pnpm lint
```

Expected: Both pass with no errors.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/app/screening/\[id\]/dashboard/page.tsx
git commit -m "feat: integrate charts into dashboard below severity summary"
```

---

## Task 7: Map Layer Toggle + Risk Markers

**Files:**
- Modify: `frontend/src/app/screening/[id]/map/page.tsx`

This task adds:
1. Layer visibility toggle panel (top-left overlay)
2. Risk markers with severity-colored pins
3. Legend updates for risk markers

- [ ] **Step 1: Add layer toggle state and severity color map**

In `map/page.tsx`, inside `RiskMapPage()` component (after line 90 `const [regulations, setRegulations] = useState...`), add:

```tsx
  // Layer toggle state
  const [layerVisibility, setLayerVisibility] = useState({
    buffer: true,
    riskMarkers: true,
    regulations: true,
  });

  const toggleLayer = useCallback((layerKey: keyof typeof layerVisibility) => {
    setLayerVisibility((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  }, []);
```

- [ ] **Step 2: Add risk marker creation in map.on("load")**

Inside the `map.on("load", () => { ... })` callback (after the 1km buffer circle code, around line 229), add:

```tsx
      // ── Risk markers ──
      const SEVERITY_MARKER_COLORS: Record<string, string> = {
        critical: "#ef4444",
        major: "#f97316",
        review: "#3b82f6",
        info: "#6b7280",
      };

      if (riskCards.length > 0) {
        const riskFeatures = riskCards.map((card, idx) => {
          // Offset markers around project location in a circle
          const angle = (idx / Math.max(riskCards.length, 1)) * 2 * Math.PI;
          const offsetLng = lng + 0.003 * Math.cos(angle);
          const offsetLat = lat + 0.003 * Math.sin(angle);
          return {
            type: "Feature" as const,
            geometry: { type: "Point" as const, coordinates: [offsetLng, offsetLat] },
            properties: {
              title: card.title,
              severity: card.severity,
              color: SEVERITY_MARKER_COLORS[card.severity] ?? "#6b7280",
            },
          };
        });

        map.addSource("risk-markers", {
          type: "geojson",
          data: { type: "FeatureCollection", features: riskFeatures },
        });

        map.addLayer({
          id: "risk-markers-circle",
          type: "circle",
          source: "risk-markers",
          paint: {
            "circle-radius": 8,
            "circle-color": ["get", "color"],
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
          },
        });

        // Popup on click
        map.on("click", "risk-markers-circle", (e) => {
          const feature = e.features?.[0];
          if (!feature || feature.geometry.type !== "Point") return;
          const coords = feature.geometry.coordinates.slice() as [number, number];
          const props = feature.properties;
          new maplibregl.Popup({ offset: 12 })
            .setLngLat(coords)
            .setHTML(`<strong>${props?.title ?? ""}</strong><br/><span style="text-transform:capitalize">${props?.severity ?? ""}</span>`)
            .addTo(map);
        });

        map.on("mouseenter", "risk-markers-circle", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "risk-markers-circle", () => {
          map.getCanvas().style.cursor = "";
        });
      }
```

- [ ] **Step 3: Add layer visibility toggle effect**

After the map initialization `useEffect` (after line 238), add a new `useEffect`:

```tsx
  // Sync layer visibility with map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const bufferLayers = ["buffer-500m-fill", "buffer-500m-line", "buffer-1km-fill", "buffer-1km-line"];
    const riskLayers = ["risk-markers-circle"];

    try {
      for (const id of bufferLayers) {
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", layerVisibility.buffer ? "visible" : "none");
        }
      }
      for (const id of riskLayers) {
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", layerVisibility.riskMarkers ? "visible" : "none");
        }
      }
    } catch {
      // Map may not be fully loaded yet — ignore
    }
  }, [layerVisibility]);
```

- [ ] **Step 4: Add layer toggle panel overlay in JSX**

In the map area `<div>` (around line 251, after `<div ref={mapContainerRef} className="absolute inset-0" />`), add:

```tsx
          {/* Layer toggle panel */}
          <div className="absolute top-4 left-4 bg-card/90 backdrop-blur-sm text-xs px-3 py-2.5 rounded-lg border border-border space-y-1.5 z-10">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">레이어</p>
            {([
              { key: "buffer" as const, label: "반경 표시" },
              { key: "riskMarkers" as const, label: "리스크 마커" },
              { key: "regulations" as const, label: "용도지역" },
            ] as const).map(({ key, label }) => (
              <button
                key={key}
                role="switch"
                aria-checked={layerVisibility[key]}
                data-testid={`layer-toggle-${key}`}
                onClick={() => toggleLayer(key)}
                className={`flex items-center gap-2 w-full px-1.5 py-1 rounded text-left transition-colors ${
                  layerVisibility[key]
                    ? "text-foreground"
                    : "text-muted-foreground opacity-60"
                }`}
              >
                <span
                  className={`inline-block size-3 rounded-sm border transition-colors ${
                    layerVisibility[key]
                      ? "bg-teal-500 border-teal-500"
                      : "bg-transparent border-muted-foreground"
                  }`}
                />
                {label}
              </button>
            ))}
          </div>
```

- [ ] **Step 5: Update legend with risk marker colors**

Replace the existing legend overlay (around line 255) with:

```tsx
          {/* Legend overlay */}
          <div className="absolute bottom-4 left-4 bg-card/90 backdrop-blur-sm text-xs px-3 py-2 rounded-lg border border-border space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-block w-4 h-0.5 border-t-2 border-dashed border-orange-500" />
              <span className="text-muted-foreground">500m 반경</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block w-4 h-0.5 border-t-2 border-dashed border-blue-500" />
              <span className="text-muted-foreground">1km 반경</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block size-2.5 rounded-full bg-red-500" />
              <span className="text-muted-foreground">Critical</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block size-2.5 rounded-full bg-orange-500" />
              <span className="text-muted-foreground">Major</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block size-2.5 rounded-full bg-blue-500" />
              <span className="text-muted-foreground">Review</span>
            </div>
          </div>
```

- [ ] **Step 6: Add data-testid to map container**

On the map container div (line 252), add `data-testid="risk-map"`:

```tsx
<div ref={mapContainerRef} data-testid="risk-map" className="absolute inset-0" />
```

- [ ] **Step 7: Verify build + lint**

```bash
cd frontend && pnpm build && pnpm lint
```

Expected: Both pass with no errors.

- [ ] **Step 8: Commit**

```bash
cd frontend && git add src/app/screening/\[id\]/map/page.tsx
git commit -m "feat: add layer toggles and risk markers to map page"
```

---

## Task 8: RAG API Function

**Files:**
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add RAG types and queryRag function**

At the end of `src/lib/api.ts` (before the `// ── Health ──` section, around line 245), add:

```typescript
// ── RAG ──

export interface RagSource {
  report_id: string;
  project_name: string;
  project_type: string;
  year: string;
  chapter: string;
  section: string;
  page_range: string;
  similarity: number;
  excerpt: string;
}

export interface RagResponse {
  answer: string;
  sources: RagSource[];
  total_indexed: number;
  generated_at?: string;
  disclaimer: string;
}

export function queryRag(question: string, projectType?: string) {
  return request<RagResponse>("/api/rag/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      n_results: 5,
      project_type: projectType,
    }),
  });
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && pnpm build
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
cd frontend && git add src/lib/api.ts
git commit -m "feat: add queryRag API function for RAG search"
```

---

## Task 9: RAG Page + Layout Tab

**Files:**
- Create: `frontend/src/app/screening/[id]/rag/page.tsx`
- Modify: `frontend/src/app/screening/[id]/layout.tsx`

- [ ] **Step 1: Create RAG page**

Create `src/app/screening/[id]/rag/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Search } from "lucide-react";
import { queryRag } from "@/lib/api";
import type { RagResponse } from "@/lib/api";

export default function RagPage() {
  const { id } = useParams<{ id: string }>();

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RagResponse | null>(null);

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    try {
      const res = await queryRag(trimmed);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "검색 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isEmpty = query.trim().length === 0;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Search className="size-6" />
          환경영향평가서 원문 검색
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          RAG 기반으로 실제 환경영향평가서 원문에서 답변을 검색합니다.
        </p>
      </div>

      {/* Query input */}
      <div className="flex gap-2">
        <input
          data-testid="rag-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="예: 도로 사업의 비산먼지 저감방안은?"
          className="flex-1 rounded-lg border border-input bg-background px-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <Button
          data-testid="rag-submit"
          onClick={handleSubmit}
          disabled={isEmpty || loading}
        >
          검색
        </Button>
      </div>
      {isEmpty && query.length > 0 && (
        <p className="text-xs text-muted-foreground">질문을 입력하세요</p>
      )}

      {/* Loading */}
      {loading && (
        <div data-testid="rag-loading" className="flex items-center gap-3 py-8 justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/20 border-t-primary" />
          <span className="text-sm text-muted-foreground">원문을 검색하고 있습니다...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="py-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Response */}
      {result && !loading && (
        <div className="space-y-4">
          {/* AI Answer */}
          <Card data-testid="rag-response">
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base">AI 답변</CardTitle>
                <Badge
                  variant="outline"
                  className="border-0 bg-teal-100 text-teal-700 dark:bg-teal-950 dark:text-teal-400 text-xs"
                >
                  RAG 기반
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed whitespace-pre-line">
                {result.answer}
              </p>
            </CardContent>
          </Card>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold mb-3">
                참조 원문 ({result.sources.length}건)
              </h2>
              <div className="space-y-2">
                {result.sources.map((source, idx) => (
                  <Card key={idx} data-testid="rag-source">
                    <CardContent className="py-3 px-4 space-y-1.5">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">
                          {source.project_name}
                        </span>
                        <Badge variant="outline" className="text-xs border-0 bg-muted">
                          {source.year}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {source.chapter}장 {source.section}절
                        </span>
                        {source.page_range && (
                          <span className="text-xs text-muted-foreground">
                            p.{source.page_range}
                          </span>
                        )}
                        <span className="ml-auto text-xs font-medium text-teal-700 dark:text-teal-400">
                          {Math.round(source.similarity * 100)}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {source.excerpt}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <p className="text-xs text-muted-foreground text-center">
            {result.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add "원문 검색" tab to layout.tsx**

In `src/app/screening/[id]/layout.tsx`, add `Search` to the lucide-react import:

```typescript
import { LayoutDashboard, Map, Database, BookOpen, FileText, Search } from "lucide-react";
```

Then add the RAG tab entry to the `TABS` array after the "draft" entry:

```typescript
  { key: "rag",         label: "원문 검색",   icon: Search,          href: (id: string) => `/screening/${id}/rag` },
```

Full updated TABS array should be:

```typescript
const TABS = [
  { key: "dashboard",   label: "대시보드",    icon: LayoutDashboard, href: (id: string) => `/screening/${id}/dashboard` },
  { key: "map",         label: "리스크 맵",   icon: Map,             href: (id: string) => `/screening/${id}/map` },
  { key: "data-status", label: "데이터 현황", icon: Database,        href: (id: string) => `/screening/${id}/data-status` },
  { key: "cases",       label: "유사사례",    icon: BookOpen,        href: (id: string) => `/screening/${id}/cases` },
  { key: "draft",       label: "초안 생성",   icon: FileText,        href: (id: string) => `/screening/${id}/draft` },
  { key: "rag",         label: "원문 검색",   icon: Search,          href: (id: string) => `/screening/${id}/rag` },
];
```

- [ ] **Step 3: Verify build + lint**

```bash
cd frontend && pnpm build && pnpm lint
```

Expected: Both pass.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add src/app/screening/\[id\]/rag/page.tsx src/app/screening/\[id\]/layout.tsx
git commit -m "feat: add RAG search page and tab navigation"
```

---

## Task 10: E2E Verification + Final Build

**Files:** None (verification only)

- [ ] **Step 1: Run full build + lint**

```bash
cd frontend && pnpm build && pnpm lint
```

Expected: Both pass with 0 errors.

- [ ] **Step 2: Run E2E tests**

```bash
cd frontend && npx playwright test --reporter=list
```

Expected: All existing tests pass. New pages may not have dedicated E2E tests yet (that's fine — stubs already cover RAG routes).

- [ ] **Step 3: Verify acceptance criteria**

Manual checklist:
- [ ] 3 chart components exist in `src/components/charts/`
- [ ] Each chart has `data-testid` attributes on dynamic elements
- [ ] ChartEmptyState renders when data is empty
- [ ] Map page has layer toggle panel with 3 toggles
- [ ] Map page has risk markers with severity colors
- [ ] RAG page renders at `/screening/[id]/rag`
- [ ] Layout tab shows "원문 검색"
- [ ] `pnpm build` clean, `pnpm lint` 0 errors

- [ ] **Step 4: Final commit (if any lint fixes needed)**

```bash
cd frontend && git add -A
git commit -m "chore: round 1 data visualization — final verification"
```
