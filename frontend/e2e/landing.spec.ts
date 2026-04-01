import { test, expect } from "@playwright/test";

test.describe("Landing page (/)", () => {
  test("renders hero section with key elements", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(1000); // Wait for framer-motion animations

    // Hero heading
    await expect(page.getByText("사업지 입력 한 번으로")).toBeVisible({ timeout: 10000 });

    // Subtitle pill
    await expect(page.getByText("환경영향평가 사전검토 지원 도구")).toBeVisible();

    // CTA button
    const ctaLink = page.getByRole("link", { name: /스크리닝 시작/ }).first();
    await expect(ctaLink).toBeVisible();
    await expect(ctaLink).toHaveAttribute("href", "/screening/new");
  });

  test("displays stats section", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(1000);

    await expect(page.getByText("103건", { exact: true })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("64개", { exact: true })).toBeVisible();
  });

  test("displays features section", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(1000);

    await expect(page.getByRole("heading", { name: "주요 기능" })).toBeVisible({ timeout: 10000 });
  });

  test("CTA navigates to /screening/new", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(1000);

    await page.getByRole("link", { name: /스크리닝 시작/ }).first().click();
    await expect(page).toHaveURL(/\/screening\/new/);
  });

  test("sidebar navigation is visible on desktop", async ({ page }) => {
    await page.goto("/");

    const sidebar = page.locator("aside").first();
    await expect(sidebar).toBeVisible();

    await expect(page.locator("aside").getByRole("link", { name: "홈" })).toBeVisible();
    await expect(page.locator("aside").getByRole("link", { name: "새 검토" })).toBeVisible();
  });
});
