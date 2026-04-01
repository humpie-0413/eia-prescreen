import { test, expect } from "@playwright/test";
import { setupApiMocks } from "../helpers/mock-api";

test.describe("R2 Form Validation — screening/new coordinate and submit validation", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("empty project name shows error on submit", async ({ page }) => {
    await page.goto("/screening/new");

    // Select a project type to advance to step 2
    await page.getByText("도로건설").click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });

    // Click submit without entering a name
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Should show inline error
    await expect(page.getByText("사업명을 입력하세요")).toBeVisible();
  });

  test("successful submission shows toast and redirects", async ({ page }) => {
    await page.goto("/screening/new");

    // Select project type
    await page.getByText("도로건설").click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });

    // Fill in project name
    await page.getByLabel("사업명 *").fill("테스트 사업");

    // Submit
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Toast should appear
    await expect(page.getByText("스크리닝 생성 완료")).toBeVisible({ timeout: 10000 });

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/screening\/test-001\/dashboard/, { timeout: 10000 });
  });

  test("submit failure shows error toast", async ({ page }) => {
    // Override POST /api/screening to return 500
    await setupApiMocks(page);
    await page.route("**/api/screening", (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({ status: 500, json: { detail: "Server Error" } });
      }
      return route.fallback();
    });

    await page.goto("/screening/new");

    // Select project type and fill name
    await page.getByText("도로건설").click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });
    await page.getByLabel("사업명 *").fill("테스트 사업");

    // Submit
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Should show error toast
    await expect(page.getByText("검토 요청 실패")).toBeVisible({ timeout: 10000 });
  });

  test("step 2 button click works when project type already selected", async ({ page }) => {
    await page.goto("/screening/new");

    // Select project type first (advances to step 2)
    await page.getByText("도로건설").click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });

    // Go back to step 1
    await page.getByText("사업유형").first().click();
    await expect(page.getByText("사업유형 선택")).toBeVisible({ timeout: 10000 });

    // Click step 2 button — should work since type is selected
    await page.locator("button").filter({ hasText: "사업정보 + 위치" }).click();
    await expect(page.getByText("사업 정보")).toBeVisible({ timeout: 10000 });
  });
});
