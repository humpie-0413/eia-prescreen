import { test, expect } from "@playwright/test";
import { setupErrorMocks, setupEmptyMocks } from "../helpers/mock-api";

test.describe("R2 Error/Empty States — ErrorState and EmptyState rendering", () => {
  test("dashboard renders ErrorState on API 500", async ({ page }) => {
    await setupErrorMocks(page);
    await page.goto("/screening/test-001/dashboard");

    const errorState = page.getByTestId("error-state");
    await expect(errorState).toBeVisible({ timeout: 15000 });

    // Should show error message text
    await expect(errorState.locator("text=Internal Server Error").or(errorState.locator("p"))).toBeVisible();

    // Should have retry button
    await expect(errorState.getByRole("button", { name: "다시 시도" })).toBeVisible();
  });

  test("data-status renders ErrorState on API 500", async ({ page }) => {
    await setupErrorMocks(page);
    await page.goto("/screening/test-001/data-status");

    const errorState = page.getByTestId("error-state");
    await expect(errorState).toBeVisible({ timeout: 15000 });
    await expect(errorState.getByRole("button", { name: "다시 시도" })).toBeVisible();
  });

  test("draft page renders ErrorState on API 500", async ({ page }) => {
    await setupErrorMocks(page);
    await page.goto("/screening/test-001/draft");

    const errorState = page.getByTestId("error-state");
    await expect(errorState).toBeVisible({ timeout: 15000 });
    await expect(errorState.getByRole("button", { name: "다시 시도" })).toBeVisible();
  });

  test("dashboard renders EmptyState/empty data gracefully with setupEmptyMocks", async ({ page }) => {
    await setupEmptyMocks(page);
    await page.goto("/screening/test-001/dashboard");

    // With empty evaluation (0 risk cards), dashboard should not crash
    // It may show "0" counts or empty content — the point is no crash
    await page.waitForTimeout(3000);

    // Page should not show an unhandled error
    const body = page.locator("body");
    await expect(body).not.toContainText("unhandled");
    await expect(body).not.toContainText("Application error");
  });

  test("cases page renders EmptyState when no cases found", async ({ page }) => {
    await setupEmptyMocks(page);
    await page.goto("/screening/test-001/cases");

    // Need to trigger a search to see EmptyState (initial state is "click to search")
    // Use the emerald action button, not the tab button
    const similarBtn = page.locator("button.bg-emerald-600", { hasText: "유사사례" });
    await expect(similarBtn).toBeVisible({ timeout: 15000 });
    await similarBtn.click();

    // EmptyState should appear for empty search results
    const emptyState = page.getByTestId("empty-state");
    await expect(emptyState).toBeVisible({ timeout: 15000 });
  });
});
