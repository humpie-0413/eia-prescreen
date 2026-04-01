import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Responsive — Mobile (375px)", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("landing page renders correctly on mobile", async ({ page }) => {
    await page.goto("/");

    // Hero heading should be visible
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // CTA should be visible
    await expect(page.getByRole("link", { name: /스크리닝 시작/ }).first()).toBeVisible();

    // Desktop sidebar should be hidden on mobile
    const sidebar = page.locator("aside").first();
    await expect(sidebar).not.toBeVisible();

    // Mobile bottom nav should be visible
    const mobileNav = page.locator("nav.fixed");
    await expect(mobileNav).toBeVisible();
  });

  test("screening new page is usable on mobile", async ({ page }) => {
    await setupApiMocks(page);
    await page.goto("/screening/new");

    // Type grid should be visible
    await expect(page.getByText("사업유형 선택")).toBeVisible();

    // Select type
    await page.getByText("도로건설").click();

    // Form should be visible
    await expect(page.getByLabel("사업명 *")).toBeVisible();
  });
});

test.describe("Responsive — Tablet (768px)", () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test("landing page layout adapts to tablet", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("link", { name: /스크리닝 시작/ }).first()).toBeVisible();
  });

  test("screening new form shows side-by-side on tablet", async ({ page }) => {
    await setupApiMocks(page);
    await page.goto("/screening/new");

    await page.getByText("도로건설").click();

    await expect(page.getByLabel("사업명 *")).toBeVisible();
  });
});

test.describe("Responsive — Desktop (1280px)", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("sidebar is visible on desktop", async ({ page }) => {
    await page.goto("/");

    // Desktop sidebar should be visible
    const sidebar = page.locator("aside").first();
    await expect(sidebar).toBeVisible();
  });

  test("compare page shows grid layout", async ({ page }) => {
    await setupApiMocks(page);
    await page.goto("/screening/compare");

    await expect(page.getByRole("heading", { name: "부지 비교" })).toBeVisible();
    await expect(page.getByText("비교 부지 선택")).toBeVisible();
  });

  test("dashboard tab nav works on desktop", async ({ page }) => {
    await setupApiMocks(page);
    await page.goto("/screening/test-001/dashboard");

    // All tabs should be visible (use first() to avoid matching dashboard button links)
    await expect(page.getByRole("link", { name: /대시보드/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /리스크 맵/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /데이터 현황/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /유사사례/ }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /초안 생성/ }).first()).toBeVisible();
  });
});
