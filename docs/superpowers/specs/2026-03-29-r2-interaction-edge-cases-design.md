# R2 Design: Interaction + Edge Cases

> Date: 2026-03-29
> Source: docs/ITERATION_PLAN.md 2회차
> Approach: A (minimal change, no React Query refactor)

## 1. Common Feedback Components

Create `frontend/src/components/feedback/` with 3 components:

### EmptyState
- Props: `icon?: LucideIcon`, `title: string`, `description?: string`, `action?: { label: string; onClick: () => void }`
- `data-testid="empty-state"`
- Icon defaults to `Inbox` from lucide-react
- Uses framer-motion fade-in

### ErrorState
- Props: `message: string`, `onRetry?: () => void`
- `data-testid="error-state"`
- Icon: `AlertTriangle` from lucide-react
- Retry button shown when `onRetry` provided
- Red/destructive color scheme via Tailwind tokens (no hex)

### LoadingSkeleton
- Props: `variant: "card" | "list" | "chart"`, `count?: number`
- `data-testid="loading-skeleton"`
- Uses `animate-pulse` (Tailwind) — no framer-motion needed for skeleton
- Variants: card (h-32 rounded box), list (4 rows), chart (bar placeholder)

### Integration Points
Replace inline loading/error/empty patterns in these pages:
- `screening/[id]/dashboard/page.tsx` — loading spinner + error div
- `screening/[id]/cases/page.tsx` — inline empty/error/loading
- `screening/[id]/data-status/page.tsx` — inline loading/error
- `screening/[id]/draft/page.tsx` — inline loading/error
- `screening/[id]/map/page.tsx` — SidebarSpinner + error div
- `screening/compare/page.tsx` — inline loading/error

## 2. Micro Interactions

### Risk Card Tooltip
- Location: dashboard page `RiskCardItem` inline component
- Use existing `ui/tooltip.tsx` (already built, unused)
- Content: `card.rationale` (truncated to ~80 chars)
- `data-testid="risk-tooltip"` on TooltipContent
- Trigger: hover (mouse), focus (keyboard)

### Number Count-up
- Location: dashboard SeveritySummaryCard counts
- Implementation: framer-motion `useSpring` + `useTransform` + `motion.span`
- Duration: 0.8s, spring damping
- Only animates on initial mount (not on re-render)

### Button Feedback
- Add `whileTap={{ scale: 0.97 }}` to primary action buttons via framer-motion
- Targets: form submit, retry buttons, tab nav buttons in new page

### Toast Notifications (sonner)
- sonner already installed and configured in Providers
- Add toast calls for:
  - Form submit success: `toast.success("스크리닝 생성 완료")`
  - Coordinate validation error: `toast.error("좌표 범위를 확인하세요")`
  - Project type unselected: `toast.warning("사업유형을 선택하세요")`

## 3. Form UX (screening/new/page.tsx)

### Coordinate Validation
- Real-time validation on `onChange` (not just on submit)
- Latitude: 33 ≤ lat ≤ 43 (South Korea range)
- Longitude: 124 ≤ lng ≤ 132
- Visual feedback: `aria-invalid={true}` on Input + inline error `<p>` below field
- Validation function: pure, no side effects

### Project Type Unselected Warning
- On "다음" (next step) click with no type selected: `toast.warning`
- Prevent step advancement until type is selected

### Submit Progress Bar
- `motion.div` with `animate={{ width: "100%" }}` during submission
- Positioned at top of form card
- Colors: `bg-primary` (Tailwind token)
- Submit button: disabled + spinner during submission
- No `setTimeout` — tied to actual API call promise

## 4. Animation Constraints

- All animations use framer-motion or CSS transitions (Tailwind `transition-*`)
- Zero `setTimeout` / `setInterval` for visual effects
- Durations: 0.2-0.4s for micro, 0.6-0.8s for count-up
- Easing: `[0.16, 1, 0.3, 1]` (consistent with existing)

## 5. Acceptance Criteria (from ITERATION_PLAN.md)

- [ ] 3 common components exist (EmptyState, ErrorState, LoadingSkeleton)
- [ ] API errors render ErrorState (no app crash)
- [ ] Out-of-range coordinates show error message
- [ ] Hover tooltip DOM created on risk cards
- [ ] framer-motion/CSS transitions only (no setTimeout)
- [ ] pnpm build clean, lint 0 errors
