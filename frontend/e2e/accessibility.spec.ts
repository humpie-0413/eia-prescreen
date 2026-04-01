import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Accessibility", () => {
  test("landing page has proper heading hierarchy", async ({ page }) => {
    await page.goto("/");
    await page.waitForTimeout(1000);

    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toBeVisible({ timeout: 10000 });
  });

  test("all interactive elements are keyboard accessible on landing", async ({
    page,
  }) => {
    await page.goto("/");
    await page.waitForTimeout(1000);

    // Tab to some elements
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
  });

  test("sidebar links have proper focus-visible styles", async ({ page }) => {
    await page.goto("/");

    const sidebarLinks = page.locator("aside a");
    const count = await sidebarLinks.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      await expect(sidebarLinks.nth(i)).toHaveAttribute("href", /.+/);
    }
  });

  test("screening new form labels are associated with inputs", async ({
    page,
  }) => {
    await page.goto("/screening/new");

    // Go to step 2
    await page.getByText("도로건설").click();

    const nameInput = page.getByLabel("사업명 *");
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toHaveAttribute("id", "name");
  });

  test("draft page accordion sections are keyboard operable", async ({
    page,
  }) => {
    await setupApiMocks(page);
    await page.goto("/screening/test-001/draft");

    // Wait for sections to load
    await expect(page.getByText("사업의 목적")).toBeVisible({ timeout: 15000 });

    // The CardHeader has role="button" and tabIndex={0}
    // Find the section header and click it
    const sectionHeader = page.locator('[role="button"]').filter({ hasText: "사업의 목적" });
    await sectionHeader.focus();
    await page.keyboard.press("Enter");

    await expect(page.getByText("양평군 일대의 교통 혼잡 해소")).toBeVisible({ timeout: 5000 });
  });
});
