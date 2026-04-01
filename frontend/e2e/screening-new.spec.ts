import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Screening new (/screening/new)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("renders project type selection grid with 17 types", async ({ page }) => {
    await page.goto("/screening/new");

    // Page heading
    await expect(page.getByText("새 사전검토 시작")).toBeVisible();

    // Step 1 should be active — card title visible
    await expect(page.getByText("사업유형 선택")).toBeVisible();

    // Count project type buttons in the grid
    const typeButtons = page.locator("button").filter({ hasText: /도시개발|산업단지|에너지개발|항만건설|도로건설|수자원개발|철도건설|공항건설|하천이용|관광단지|산지개발|체육시설|폐기물처리|국방·군사|광업|매립·간척|특정지역/ });
    await expect(typeButtons.first()).toBeVisible();
  });

  test("selecting a project type advances to step 2", async ({ page }) => {
    await page.goto("/screening/new");

    // Click 도로건설 type
    await page.getByText("도로건설").click();

    // Step 2 should now show the form
    await expect(page.getByLabel("사업명 *")).toBeVisible();
    await expect(page.getByText("도로건설", { exact: false })).toBeVisible();
  });

  test("shows error on empty submission", async ({ page }) => {
    await page.goto("/screening/new");

    // Select type to go to step 2
    await page.getByText("도로건설").click();
    await expect(page.getByLabel("사업명 *")).toBeVisible();

    // Submit without filling name
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Should show validation error
    await expect(page.getByText("사업명을 입력하세요")).toBeVisible();
  });

  test("submitting with valid data redirects to dashboard", async ({ page }) => {
    await page.goto("/screening/new");

    // Select type
    await page.getByText("도로건설").click();

    // Fill required field
    await page.getByLabel("사업명 *").fill("테스트 도로사업");

    // Submit
    await page.getByRole("button", { name: "검토 시작" }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/screening\/.*\/dashboard/, { timeout: 10000 });
  });

  test("step indicator allows navigation between steps", async ({ page }) => {
    await page.goto("/screening/new");

    // Go to step 2
    await page.getByText("도로건설").click();
    await expect(page.getByLabel("사업명 *")).toBeVisible();

    // Click step 1 indicator to go back
    await page.getByRole("button", { name: /사업유형/ }).click();

    // Should show type grid again
    await expect(page.getByText("사업유형 선택")).toBeVisible();
  });
});
