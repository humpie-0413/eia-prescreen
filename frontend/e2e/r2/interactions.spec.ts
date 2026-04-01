import { test, expect } from "@playwright/test";
import { setupApiMocks } from "../helpers/mock-api";

test.describe("R2 Interactions — tooltip, loading skeleton, and toast", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("risk card hover shows tooltip with rationale", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard content to load
    await expect(page.getByText("결과 대시보드")).toBeVisible({ timeout: 15000 });

    // Find first risk card and hover
    const riskCard = page.locator("[role='button'][aria-label*='리스크']").first();
    await expect(riskCard).toBeVisible({ timeout: 10000 });
    await riskCard.hover();

    // Tooltip content should appear
    const tooltip = page.getByTestId("risk-tooltip");
    await expect(tooltip).toBeVisible({ timeout: 5000 });

    // Tooltip should contain rationale text (from stub: "사업지 반경" is in multiple rationales)
    const tooltipText = await tooltip.textContent();
    expect(tooltipText).toBeTruthy();
    expect(tooltipText!.length).toBeGreaterThan(0);
  });

  test("risk card tooltip accessible via keyboard focus", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    await expect(page.getByText("결과 대시보드")).toBeVisible({ timeout: 15000 });

    // Tab to the first risk card button
    const riskCard = page.locator("[role='button'][aria-label*='리스크']").first();
    await expect(riskCard).toBeVisible({ timeout: 10000 });
    await riskCard.focus();

    // Tooltip should appear on focus
    const tooltip = page.getByTestId("risk-tooltip");
    await expect(tooltip).toBeVisible({ timeout: 5000 });
  });

  test("dashboard loading skeleton shows before data loads", async ({ page }) => {
    // Delay the evaluate response to observe loading state
    await page.route("**/api/screening/*/evaluate*", async (route) => {
      await new Promise((r) => setTimeout(r, 2000));
      return route.fulfill({
        status: 200,
        json: (await import("../fixtures/api-stubs")).EVALUATION_RESPONSE,
      });
    });
    // Still mock other routes normally
    await setupApiMocks(page);

    await page.goto("/screening/test-001/dashboard");

    // LoadingSkeleton should be visible while waiting
    const skeleton = page.getByTestId("loading-skeleton");
    await expect(skeleton.first()).toBeVisible({ timeout: 5000 });
  });

  test("successful form submit shows progress bar animation", async ({ page }) => {
    await page.goto("/screening/new");

    // Select project type and fill form
    await page.getByText("도로건설").click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });
    await page.getByLabel("사업명 *").fill("테스트 사업");

    // Delay the screening POST to observe progress bar
    await page.route("**/api/screening", async (route) => {
      if (route.request().method() === "POST") {
        await new Promise((r) => setTimeout(r, 1500));
        return route.fulfill({
          status: 200,
          json: { id: "test-001", project_name: "테스트 사업", project_type: "road", status: "created" },
        });
      }
      return route.fallback();
    });

    // Click submit
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Button should change to "분석 중..."
    await expect(page.getByText("분석 중...")).toBeVisible({ timeout: 3000 });

    // Progress bar should be visible (motion.div inside a container with bg-muted)
    const progressContainer = page.locator(".bg-muted.overflow-hidden");
    await expect(progressContainer).toBeVisible({ timeout: 3000 });
  });
});
