import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Draft page (/screening/[id]/draft)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("renders draft sections after loading", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    // Title
    await expect(page.getByText("평가서 초안 생성")).toBeVisible({ timeout: 10000 });

    // AI disclaimer badge
    await expect(page.getByText("AI 생성 참고용")).toBeVisible();
  });

  test("displays disclaimer banner", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    await expect(
      page.getByText("이 초안은 AI가 생성한 참고 자료이며"),
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows section badges", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    // Wait for loading to complete
    await expect(page.getByText("사업의 목적")).toBeVisible({ timeout: 10000 });

    // Badge texts rendered inside Badge components
    await expect(page.getByText("자동 생성").first()).toBeVisible();
    // "현장조사 필요" and "전문가 검토 필요" may need expand all to be visible
    await page.getByText("모두 펼치기").click();
    await expect(page.locator('[data-slot="badge"]').filter({ hasText: "현장조사 필요" })).toBeVisible();
    await expect(page.locator('[data-slot="badge"]').filter({ hasText: "전문가 검토 필요" })).toBeVisible();
  });

  test("accordion toggle opens and closes section content", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    // Wait for sections — target the card header button
    const sectionHeader = page.locator('[role="button"]').filter({ hasText: "사업의 목적" });
    await expect(sectionHeader).toBeVisible({ timeout: 10000 });

    // Click the card header to expand
    await sectionHeader.click();

    // Content should appear
    await expect(
      page.getByText("양평군 일대의 교통 혼잡 해소"),
    ).toBeVisible({ timeout: 5000 });

    // Click header again to collapse
    await sectionHeader.click();

    // Content should be hidden
    await expect(
      page.getByText("양평군 일대의 교통 혼잡 해소"),
    ).not.toBeVisible({ timeout: 5000 });
  });

  test("expand all / collapse all button works", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    await expect(page.getByText("모두 펼치기")).toBeVisible({ timeout: 10000 });

    // Click expand all
    await page.getByText("모두 펼치기").click();

    // Content should be visible
    await expect(
      page.getByText("양평군 일대의 교통 혼잡 해소"),
    ).toBeVisible();

    // Button text should change
    await expect(page.getByText("모두 접기")).toBeVisible();
  });

  test("summary stats show correct counts", async ({ page }) => {
    await page.goto("/screening/test-001/draft");

    // Total sections
    await expect(page.getByText("18")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("전체 섹션")).toBeVisible();
  });
});
