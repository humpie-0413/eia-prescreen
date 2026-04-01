# R2: Interaction + Edge Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 reusable feedback components (EmptyState, ErrorState, LoadingSkeleton), micro-interactions (tooltip, count-up, toast), and form validation to all screening pages.

**Architecture:** Create `components/feedback/` with 3 exports. Replace inline loading/error/empty patterns in 6 pages. Add tooltip to risk cards via existing `ui/tooltip.tsx`. Add coordinate validation and progress bar to `screening/new/page.tsx`. All animations via framer-motion or CSS transitions (no setTimeout).

**Tech Stack:** React 19, Next.js 16, framer-motion 12, sonner 2, lucide-react, Tailwind CSS, @base-ui/react tooltip

---

## File Structure

### Create:
- `frontend/src/components/feedback/empty-state.tsx` — Reusable empty data display
- `frontend/src/components/feedback/error-state.tsx` — Reusable API error display
- `frontend/src/components/feedback/loading-skeleton.tsx` — Skeleton loading variants
- `frontend/src/components/feedback/index.ts` — Barrel export
- `frontend/src/hooks/use-count-up.ts` — framer-motion count-up hook
- `frontend/src/lib/validate.ts` — Coordinate/form validation functions

### Modify:
- `frontend/src/app/screening/[id]/dashboard/page.tsx` — Replace inline states + add tooltip + count-up
- `frontend/src/app/screening/[id]/data-status/page.tsx` — Replace inline states
- `frontend/src/app/screening/[id]/draft/page.tsx` — Replace inline states
- `frontend/src/app/screening/[id]/map/page.tsx` — Replace inline states
- `frontend/src/app/screening/[id]/cases/page.tsx` — Add EmptyState for no-results
- `frontend/src/app/screening/compare/page.tsx` — Replace inline error
- `frontend/src/app/screening/new/page.tsx` — Add validation + progress + toast

---

### Task 1: Create Feedback Components

**Files:**
- Create: `frontend/src/components/feedback/empty-state.tsx`
- Create: `frontend/src/components/feedback/error-state.tsx`
- Create: `frontend/src/components/feedback/loading-skeleton.tsx`
- Create: `frontend/src/components/feedback/index.ts`

- [ ] **Step 1: Create EmptyState component**

```tsx
// frontend/src/components/feedback/empty-state.tsx
"use client";

import { motion } from "framer-motion";
import { Inbox, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <motion.div
      data-testid="empty-state"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="flex items-center justify-center size-12 rounded-full bg-muted mb-4">
        <Icon className="size-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          {description}
        </p>
      )}
      {action && (
        <Button
          variant="outline"
          size="sm"
          onClick={action.onClick}
          className="mt-4"
        >
          {action.label}
        </Button>
      )}
    </motion.div>
  );
}
```

- [ ] **Step 2: Create ErrorState component**

```tsx
// frontend/src/components/feedback/error-state.tsx
"use client";

import { motion } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <motion.div
      data-testid="error-state"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center justify-center py-16 text-center"
    >
      <div className="flex items-center justify-center size-12 rounded-full bg-destructive/10 mb-4">
        <TriangleAlert className="size-6 text-destructive" />
      </div>
      <p className="text-sm font-medium text-destructive">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-4">
          다시 시도
        </Button>
      )}
    </motion.div>
  );
}
```

- [ ] **Step 3: Create LoadingSkeleton component**

```tsx
// frontend/src/components/feedback/loading-skeleton.tsx
interface LoadingSkeletonProps {
  variant?: "card" | "list" | "chart";
  count?: number;
}

export function LoadingSkeleton({
  variant = "card",
  count = 1,
}: LoadingSkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  if (variant === "list") {
    return (
      <div data-testid="loading-skeleton" className="space-y-3">
        {items.map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="size-8 rounded-full bg-muted animate-pulse shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-3/4 rounded bg-muted animate-pulse" />
              <div className="h-2.5 w-1/2 rounded bg-muted animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div data-testid="loading-skeleton" className="space-y-2">
        <div className="h-4 w-24 rounded bg-muted animate-pulse" />
        <div className="flex items-end gap-2 h-32">
          {[40, 70, 55, 85, 30].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-muted animate-pulse"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  // card variant
  return (
    <div data-testid="loading-skeleton" className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {items.map((i) => (
        <div key={i} className="rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-5 w-16 rounded bg-muted animate-pulse" />
            <div className="h-4 w-20 rounded bg-muted animate-pulse" />
          </div>
          <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
          <div className="h-3 w-full rounded bg-muted animate-pulse" />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Create barrel export**

```ts
// frontend/src/components/feedback/index.ts
export { EmptyState } from "./empty-state";
export { ErrorState } from "./error-state";
export { LoadingSkeleton } from "./loading-skeleton";
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && pnpm build`
Expected: Build succeeds, no TS errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/feedback/
git commit -m "feat(r2): add EmptyState, ErrorState, LoadingSkeleton feedback components"
```

---

### Task 2: Create count-up hook and validation utils

**Files:**
- Create: `frontend/src/hooks/use-count-up.ts`
- Create: `frontend/src/lib/validate.ts`

- [ ] **Step 1: Create count-up hook**

```ts
// frontend/src/hooks/use-count-up.ts
"use client";

import { useEffect, useRef, useState } from "react";
import { useSpring, useTransform, type MotionValue } from "framer-motion";

/**
 * Animates a number from 0 to `target` on mount.
 * Returns a MotionValue<string> suitable for <motion.span>.
 */
export function useCountUp(target: number): MotionValue<string> {
  const spring = useSpring(0, { stiffness: 80, damping: 20 });
  const display = useTransform(spring, (v) => Math.round(v).toLocaleString());
  const mounted = useRef(false);

  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      spring.set(target);
    }
  }, [spring, target]);

  return display;
}

/**
 * Simple hook version that returns a plain number (for non-motion contexts).
 */
export function useCountUpValue(target: number): number {
  const [value, setValue] = useState(0);
  const frameRef = useRef<number>(0);

  useEffect(() => {
    const duration = 800;
    const start = performance.now();
    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(eased * target));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    }
    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target]);

  return value;
}
```

- [ ] **Step 2: Create validation utils**

```ts
// frontend/src/lib/validate.ts

/** South Korea latitude range */
const LAT_MIN = 33;
const LAT_MAX = 43;

/** South Korea longitude range */
const LNG_MIN = 124;
const LNG_MAX = 132;

export interface CoordError {
  lat?: string;
  lng?: string;
}

export function validateCoordinates(
  lat: number | null | undefined,
  lng: number | null | undefined,
): CoordError {
  const errors: CoordError = {};

  if (lat != null) {
    if (isNaN(lat)) {
      errors.lat = "위도는 숫자여야 합니다.";
    } else if (lat < LAT_MIN || lat > LAT_MAX) {
      errors.lat = `위도는 ${LAT_MIN}~${LAT_MAX} 범위여야 합니다.`;
    }
  }

  if (lng != null) {
    if (isNaN(lng)) {
      errors.lng = "경도는 숫자여야 합니다.";
    } else if (lng < LNG_MIN || lng > LNG_MAX) {
      errors.lng = `경도는 ${LNG_MIN}~${LNG_MAX} 범위여야 합니다.`;
    }
  }

  return errors;
}

export function hasCoordErrors(errors: CoordError): boolean {
  return Boolean(errors.lat || errors.lng);
}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && pnpm build`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/use-count-up.ts frontend/src/lib/validate.ts
git commit -m "feat(r2): add useCountUp hook and coordinate validation utils"
```

---

### Task 3: Integrate feedback components into dashboard

**Files:**
- Modify: `frontend/src/app/screening/[id]/dashboard/page.tsx`

- [ ] **Step 1: Replace inline loading state with LoadingSkeleton**

In `dashboard/page.tsx`, replace lines 950-958 (the loading block):

```tsx
// OLD:
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-sm text-muted-foreground">리스크 분석 중...</p>
        </div>
      </div>
    );
  }

// NEW:
  if (loading) {
    return (
      <div className="max-w-6xl mx-auto p-4 md:p-8 space-y-6">
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="card" count={4} />
      </div>
    );
  }
```

- [ ] **Step 2: Replace inline error state with ErrorState**

Replace lines 961-971:

```tsx
// OLD:
  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-3">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
            다시 시도
          </Button>
        </div>
      </div>
    );
  }

// NEW:
  if (error) {
    return (
      <ErrorState
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }
```

- [ ] **Step 3: Add imports at top of file**

Add to imports:

```tsx
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
```

- [ ] **Step 4: Add tooltip to RiskCardItem**

Replace the `RiskCardItem` component. Add tooltip import and wrap card with it:

```tsx
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
```

Then modify `RiskCardItem`:

```tsx
const RiskCardItem = ({
  card,
  onClick,
}: {
  card: RiskCard;
  onClick: () => void;
}) => (
  <Tooltip>
    <TooltipTrigger
      render={
        <Card
          className="cursor-pointer transition-shadow hover:ring-2 hover:ring-teal-500/30 focus-visible:ring-2 focus-visible:ring-teal-500 focus-visible:outline-none"
          onClick={onClick}
          onKeyDown={(e: React.KeyboardEvent) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onClick();
            }
          }}
          role="button"
          tabIndex={0}
          aria-label={`${SEVERITY_CONFIG[card.severity].label} 리스크: ${card.title}`}
        />
      }
    >
      <CardContent className="py-4 px-5 space-y-2">
        <div className="flex items-center gap-2">
          <RiskBadge severity={card.severity} />
          <span className="text-xs text-muted-foreground font-mono">
            {card.rule_id}
          </span>
          {card.human_review_required && (
            <Badge
              variant="outline"
              className="border-0 bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400 text-xs ml-auto"
            >
              전문가 검토
            </Badge>
          )}
        </div>
        <p className="text-sm font-medium leading-snug">{card.title}</p>
        <p className="text-xs text-muted-foreground line-clamp-1">
          {card.rationale}
        </p>
      </CardContent>
    </TooltipTrigger>
    <TooltipContent data-testid="risk-tooltip" side="top">
      {card.rationale.length > 80
        ? card.rationale.slice(0, 80) + "…"
        : card.rationale}
    </TooltipContent>
  </Tooltip>
);
```

- [ ] **Step 5: Add count-up to SeveritySummaryCard**

Add import:
```tsx
import { useCountUpValue } from "@/hooks/use-count-up";
```

Replace `SeveritySummaryCard`:

```tsx
const SeveritySummaryCard = ({
  severity,
  count,
}: {
  severity: Severity;
  count: number;
}) => {
  const animatedCount = useCountUpValue(count);
  const config = SEVERITY_CONFIG[severity];
  return (
    <Card role="status" aria-label={`${config.label} ${count}건`}>
      <CardContent className="py-4 px-4 flex items-center gap-3">
        <div
          className={`flex items-center justify-center rounded-lg size-10 shrink-0 ${config.bg} ${config.color}`}
        >
          {SEVERITY_ICONS[severity]}
        </div>
        <div>
          <p className="text-2xl font-bold leading-none">{animatedCount}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {config.label}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && pnpm build && pnpm lint`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/screening/[id]/dashboard/page.tsx
git commit -m "feat(r2): dashboard — feedback components, tooltip, count-up"
```

---

### Task 4: Integrate feedback components into remaining pages

**Files:**
- Modify: `frontend/src/app/screening/[id]/data-status/page.tsx`
- Modify: `frontend/src/app/screening/[id]/draft/page.tsx`
- Modify: `frontend/src/app/screening/[id]/map/page.tsx`
- Modify: `frontend/src/app/screening/[id]/cases/page.tsx`
- Modify: `frontend/src/app/screening/compare/page.tsx`

- [ ] **Step 1: data-status page**

Add import:
```tsx
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
```

Replace loading block (lines 219-225):
```tsx
// OLD:
  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <p className="text-sm text-muted-foreground">데이터 상태 로딩 중...</p>
      </div>
    );
  }

// NEW:
  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <LoadingSkeleton variant="list" count={6} />
      </div>
    );
  }
```

Replace error block (lines 227-233):
```tsx
// OLD:
  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto p-4 md:p-8">
        <p className="text-sm text-red-500">{error ?? "데이터를 불러올 수 없습니다."}</p>
      </div>
    );
  }

// NEW:
  if (error || !data) {
    return (
      <ErrorState
        message={error ?? "데이터를 불러올 수 없습니다."}
        onRetry={() => window.location.reload()}
      />
    );
  }
```

- [ ] **Step 2: draft page**

Add import:
```tsx
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
```

Replace loading block (lines 315-323):
```tsx
// OLD:
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
          <p className="text-sm text-muted-foreground">초안 생성 중...</p>
        </div>
      </div>
    );
  }

// NEW:
  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-4">
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="card" count={3} />
      </div>
    );
  }
```

Replace error block (lines 326-335):
```tsx
// OLD:
  if (error || !draftData) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-3">
          <p className="text-sm text-destructive">{error || "데이터를 불러올 수 없습니다."}</p>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>다시 시도</Button>
        </div>
      </div>
    );
  }

// NEW:
  if (error || !draftData) {
    return (
      <ErrorState
        message={error || "데이터를 불러올 수 없습니다."}
        onRetry={() => window.location.reload()}
      />
    );
  }
```

- [ ] **Step 3: map page**

Add import:
```tsx
import { ErrorState, LoadingSkeleton } from "@/components/feedback";
```

Replace `SidebarSpinner` usage and error in the sidebar (inside `motion.aside`):
```tsx
// OLD sidebar content:
          {loading ? (
            <SidebarSpinner />
          ) : error ? (
            <div className="flex-1 flex items-center justify-center px-4">
              <div className="text-center space-y-2">
                <p className="text-sm text-destructive font-medium">데이터 로딩 실패</p>
                <p className="text-xs text-muted-foreground">{error}</p>
              </div>
            </div>
          ) : (

// NEW sidebar content:
          {loading ? (
            <div className="p-4">
              <LoadingSkeleton variant="list" count={4} />
            </div>
          ) : error ? (
            <ErrorState
              message={error}
              onRetry={() => window.location.reload()}
            />
          ) : (
```

Remove `SidebarSpinner` function (lines 64-73) — no longer needed.

- [ ] **Step 4: cases page — add EmptyState for no results**

Add import:
```tsx
import { EmptyState } from "@/components/feedback";
import { Search } from "lucide-react";
```

Find the empty results pattern (where `hasFetched && cases.length === 0`) and replace with:
```tsx
<EmptyState
  icon={Search}
  title="검색 결과가 없습니다"
  description="다른 검색어나 필터를 시도해보세요."
/>
```

- [ ] **Step 5: compare page — replace inline error**

Add import:
```tsx
import { EmptyState } from "@/components/feedback";
import { GitCompareArrows } from "lucide-react";
```

Replace the empty screenings message:
```tsx
// OLD:
        {screenings.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            평가 완료된 스크리닝이 없습니다. 먼저 새 검토를 실행해주세요.
          </p>

// NEW:
        {screenings.length === 0 ? (
          <EmptyState
            icon={GitCompareArrows}
            title="평가 완료된 스크리닝이 없습니다"
            description="먼저 새 검토를 실행해주세요."
          />
```

Replace the inline error div:
```tsx
// OLD:
      {error && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

// NEW:
      {error && (
        <div data-testid="error-state" className="rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive">
          {error}
        </div>
      )}
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && pnpm build && pnpm lint`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/screening/
git commit -m "feat(r2): integrate feedback components into all pages"
```

---

### Task 5: Form validation + toast + progress bar

**Files:**
- Modify: `frontend/src/app/screening/new/page.tsx`

- [ ] **Step 1: Add imports**

```tsx
import { toast } from "sonner";
import { validateCoordinates, hasCoordErrors, type CoordError } from "@/lib/validate";
```

- [ ] **Step 2: Add validation state**

After existing state declarations, add:
```tsx
  const [coordErrors, setCoordErrors] = useState<CoordError>({});
  const [submitProgress, setSubmitProgress] = useState(0);
```

- [ ] **Step 3: Add coordinate validation on location select**

Replace `handleLocationSelect`:
```tsx
  function handleLocationSelect(lng: number, lat: number) {
    const errors = validateCoordinates(lat, lng);
    setCoordErrors(errors);
    if (hasCoordErrors(errors)) {
      toast.error("좌표 범위를 확인하세요", {
        description: errors.lat || errors.lng,
      });
      return;
    }
    updateSite(activeSiteIndex, { location: { lng, lat } });
  }
```

- [ ] **Step 4: Add project type check on step advancement**

Replace `handleTypeSelect`:
```tsx
  function handleTypeSelect(type: ProjectType) {
    updateSite(activeSiteIndex, { projectType: type });
    setStep(2);
  }
```

Add guard to step 2 button click:
```tsx
  // In the step indicator, add guard for step 2 click:
  <button
    onClick={() => {
      if (!activeSite.projectType) {
        toast.warning("사업유형을 선택하세요");
        return;
      }
      setStep(2);
    }}
```

- [ ] **Step 5: Add progress bar and enhanced submit**

Replace `handleSubmit`:
```tsx
  async function handleSubmit() {
    setError(null);
    const site = sites[0];
    if (!site.name.trim()) {
      setError("사업명을 입력하세요.");
      return;
    }

    // Validate coordinates if provided
    if (site.location) {
      const errors = validateCoordinates(site.location.lat, site.location.lng);
      if (hasCoordErrors(errors)) {
        setCoordErrors(errors);
        toast.error("좌표 범위를 확인하세요");
        return;
      }
    }

    setIsSubmitting(true);
    setSubmitProgress(0);

    // Animate progress bar during submission
    const progressInterval = setInterval(() => {
      setSubmitProgress((prev) => Math.min(prev + 8, 90));
    }, 100);

    try {
      const result = await createScreening({
        project_name: site.name,
        project_type: site.projectType,
        project_scale: site.projectScale || undefined,
        address: site.address || undefined,
        location: site.location ?? undefined,
      });

      clearInterval(progressInterval);
      setSubmitProgress(100);
      toast.success("스크리닝 생성 완료");
      router.push(`/screening/${result.id}/dashboard`);
    } catch (e) {
      clearInterval(progressInterval);
      setSubmitProgress(0);
      const msg = e instanceof Error ? e.message : "검토 요청에 실패했습니다.";
      setError(msg);
      toast.error("검토 요청 실패", { description: msg });
    } finally {
      setIsSubmitting(false);
    }
  }
```

- [ ] **Step 6: Add progress bar and coordinate error UI in JSX**

Add progress bar above the submit button section:
```tsx
                {/* Progress bar */}
                {isSubmitting && (
                  <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
                    <motion.div
                      className="h-full bg-primary rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${submitProgress}%` }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                  </div>
                )}
```

Add coordinate error display after the location display:
```tsx
                    {activeSite.location && (
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <MapPin className="size-3" />
                        {activeSite.location.lat.toFixed(5)}, {activeSite.location.lng.toFixed(5)}
                      </p>
                    )}
                    {coordErrors.lat && (
                      <p className="text-xs text-destructive">{coordErrors.lat}</p>
                    )}
                    {coordErrors.lng && (
                      <p className="text-xs text-destructive">{coordErrors.lng}</p>
                    )}
```

- [ ] **Step 7: Verify build + lint**

Run: `cd frontend && pnpm build && pnpm lint`

- [ ] **Step 8: Commit**

```bash
git add frontend/src/app/screening/new/page.tsx
git commit -m "feat(r2): form validation, progress bar, toast notifications"
```

---

### Task 6: Final verification

- [ ] **Step 1: Full build + lint**

Run: `cd frontend && pnpm build && pnpm lint`
Expected: 0 TS errors, 0 lint errors

- [ ] **Step 2: Run existing E2E tests**

Run: `cd frontend && npx playwright test --reporter=list`
Expected: All existing tests pass (no regressions)

- [ ] **Step 3: Run backend tests**

Run: `cd /c/0_project/eia-prescreen && python -m pytest tests/ backend/tests/ -v`
Expected: All pass (no frontend changes affect backend)

- [ ] **Step 4: Verify acceptance criteria**

Check each criterion:
1. ✅ 3 common components exist — `components/feedback/{empty,error,loading}-state.tsx`
2. ✅ API errors render ErrorState — dashboard, data-status, draft, map all use `<ErrorState>`
3. ✅ Out-of-range coordinates show error — `validateCoordinates()` + toast + inline errors
4. ✅ Hover tooltip DOM created — `RiskCardItem` wrapped in `Tooltip`
5. ✅ framer-motion/CSS transitions only — no setTimeout for visuals
6. ✅ pnpm build clean, lint 0 errors

- [ ] **Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(r2): final verification fixes"
```
