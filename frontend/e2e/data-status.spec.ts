import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Data status page (/screening/[id]/data-status)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("renders data coverage summary", async ({ page }) => {
    await page.goto("/screening/test-001/data-status");

    await expect(page.getByRole("heading", { name: "데이터 현황" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("78%")).toBeVisible();
    await expect(page.getByText("데이터 커버리지")).toBeVisible();
  });

  test("shows connector status cards", async ({ page }) => {
    await page.goto("/screening/test-001/data-status");

    await expect(page.getByText("커넥터 상태")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("토지이용규제정보")).toBeVisible();
    await expect(page.getByText("에어코리아 대기오염")).toBeVisible();
  });

  test("displays demo badge in scenario label", async ({ page }) => {
    await page.goto("/screening/test-001/data-status");

    // Demo badge appears near the scenario label
    await expect(page.getByRole("heading", { name: "데이터 현황" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("데모").first()).toBeVisible();
  });

  test("shows freshness bar", async ({ page }) => {
    await page.goto("/screening/test-001/data-status");

    await expect(page.getByText("데이터 신선도")).toBeVisible({ timeout: 10000 });
  });
});
