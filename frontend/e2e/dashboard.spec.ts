import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Dashboard (/screening/[id]/dashboard)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("renders risk summary after loading", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for data to load — the severity summary cards appear
    await expect(page.getByText("Critical").first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Major").first()).toBeVisible();
  });

  test("tab navigation links are present", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for dashboard content to load before interacting with nav
    await expect(page.getByText("결과 대시보드")).toBeVisible({ timeout: 15000 });

    // Tab nav links (use first() to avoid matching dashboard button links)
    await expect(page.getByRole("link", { name: /대시보드/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /유사사례/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /초안 생성/ }).first()).toBeVisible();

    // Navigate to cases tab
    await page.getByRole("link", { name: /유사사례/ }).first().click();
    await expect(page).toHaveURL(/\/cases/, { timeout: 10000 });
  });

  test("renders risk cards section", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for risk cards header
    await expect(page.getByText("리스크 카드")).toBeVisible({ timeout: 15000 });

    // At least one risk card title should be visible (use role=button to target RiskCardItem)
    await expect(page.getByRole("button", { name: /생태자연도 1등급 권역 인접/ })).toBeVisible();
  });

  test("risk card click opens evidence drawer", async ({ page }) => {
    await page.goto("/screening/test-001/dashboard");

    // Wait for cards (use role=button to target RiskCardItem)
    const riskCard = page.getByRole("button", { name: /생태자연도 1등급 권역 인접/ });
    await expect(riskCard).toBeVisible({ timeout: 15000 });

    // Click a risk card
    await riskCard.click();

    // Evidence drawer should appear (the component renders rule_id, rationale etc.)
    await expect(page.getByText("ECO-001").first()).toBeVisible({ timeout: 5000 });
  });
});
