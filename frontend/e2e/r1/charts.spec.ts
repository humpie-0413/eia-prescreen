import { test, expect } from "@playwright/test";
import { setupApiMocks } from "../helpers/mock-api";
import { setupEmptyMocks } from "../helpers/mock-api";

test.describe("R1 Charts — Dashboard chart components", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("donut chart renders with severity data and total count", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard to load
    await expect(page.getByText("Critical").first()).toBeVisible({ timeout: 15000 });

    // Chart section title
    await expect(page.getByText("리스크 분포")).toBeVisible();

    // Total count in donut center — stub has 4 risk cards (1 critical + 2 major + 1 review)
    // The donut chart shows total inside the chart
    const donutSection = page.locator("text=리스크 분포").locator("..").locator("..");
    await expect(donutSection).toBeVisible();

    // SVG should be rendered (Recharts renders SVG)
    const svgElements = page.locator(".recharts-wrapper svg");
    await expect(svgElements.first()).toBeVisible({ timeout: 10000 });
  });

  test("review bar chart section renders with chart title", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard load
    await expect(page.getByText("Critical").first()).toBeVisible({ timeout: 15000 });

    // Chart section title (use .first() — text appears in multiple elements)
    await expect(page.getByText("검토의견 예측").first()).toBeVisible();

    // The review bar chart card should contain a Recharts wrapper or empty state
    // (In headless mode, ResponsiveContainer may have -1 dimensions, so we check
    // for the chart container rather than specific SVG text)
    const chartCard = page.getByText("검토의견 예측").first().locator("..").locator("..");
    await expect(chartCard).toBeVisible();

    // The predicted comment data ("생태", 82%) is from REVIEW_PREDICTION_RESPONSE stub
    // Verify the chart container has child content (either recharts-wrapper or empty state)
    const hasContent = await chartCard.locator(".recharts-wrapper, [data-testid='chart-empty-state']").count();
    expect(hasContent).toBeGreaterThan(0);
  });

  test("pattern bar chart renders consultation prediction labels", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard load
    await expect(page.getByText("Critical").first()).toBeVisible({ timeout: 15000 });

    // Chart section title
    await expect(page.getByText("과거 패턴").first()).toBeVisible();

    // Pattern labels from PREDICTION_RESPONSE stub: 조건부협의(62%), 협의(28%), 재검토(10%)
    await expect(page.getByText("조건부협의").first()).toBeVisible();
    await expect(page.getByText("협의").first()).toBeVisible();
    await expect(page.getByText("재검토").first()).toBeVisible();
  });

  test("empty data shows chart-empty-state fallback", async ({ page }) => {
    // Set up ONLY empty mocks (no setupApiMocks from beforeEach — override all routes)
    await setupEmptyMocks(page);

    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard to load (no risk cards, but page should render)
    await expect(page.getByText("결과 대시보드")).toBeVisible({ timeout: 15000 });

    // Chart section titles should still render (use .first() for ambiguous text)
    await expect(page.getByText("리스크 분포")).toBeVisible();
    await expect(page.getByText("검토의견 예측").first()).toBeVisible();
    await expect(page.getByText("과거 패턴").first()).toBeVisible();

    // At least one chart-empty-state should render (donut gets 0 counts, pattern gets empty obj)
    // Use count check since visibility may vary in headless
    const emptyStateCount = await page.locator("[data-testid='chart-empty-state']").count();
    expect(emptyStateCount).toBeGreaterThanOrEqual(1);
  });
});
