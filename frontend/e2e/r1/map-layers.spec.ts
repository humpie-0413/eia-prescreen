import { test, expect } from "@playwright/test";
import { setupApiMocks } from "../helpers/mock-api";

test.describe("R1 Map Layers — Layer toggles and risk markers", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("map container with data-testid exists", async ({ page }) => {
    await page.goto("/screening/test-001/map");

    // risk-map container should be attached (may be "hidden" in headless due to WebGL)
    const mapContainer = page.locator("[data-testid='risk-map']");
    await mapContainer.waitFor({ state: "attached", timeout: 15000 });
    const count = await mapContainer.count();
    expect(count).toBe(1);
  });

  test("layer toggle buttons exist with aria-checked", async ({ page }) => {
    await page.goto("/screening/test-001/map");

    // 3 layer toggles should exist
    const bufferToggle = page.locator("[data-testid='layer-toggle-buffer']");
    const riskMarkersToggle = page.locator("[data-testid='layer-toggle-riskMarkers']");
    const regulationsToggle = page.locator("[data-testid='layer-toggle-regulations']");

    await expect(bufferToggle).toBeVisible({ timeout: 15000 });
    await expect(riskMarkersToggle).toBeVisible();
    await expect(regulationsToggle).toBeVisible();

    // All toggles should have role="switch"
    await expect(bufferToggle).toHaveRole("switch");
    await expect(riskMarkersToggle).toHaveRole("switch");
    await expect(regulationsToggle).toHaveRole("switch");

    // Default: buffer and riskMarkers ON, regulations ON
    await expect(bufferToggle).toHaveAttribute("aria-checked", "true");
    await expect(riskMarkersToggle).toHaveAttribute("aria-checked", "true");
    await expect(regulationsToggle).toHaveAttribute("aria-checked", "true");
  });

  test("clicking toggle changes aria-checked state", async ({ page }) => {
    await page.goto("/screening/test-001/map");

    const bufferToggle = page.locator("[data-testid='layer-toggle-buffer']");
    await expect(bufferToggle).toBeVisible({ timeout: 15000 });
    await expect(bufferToggle).toHaveAttribute("aria-checked", "true");

    // Click to toggle off
    await bufferToggle.click();
    await expect(bufferToggle).toHaveAttribute("aria-checked", "false");

    // Click again to toggle back on
    await bufferToggle.click();
    await expect(bufferToggle).toHaveAttribute("aria-checked", "true");
  });

  test("no console errors from map initialization", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/screening/test-001/map");

    // Wait for map container to be attached (may be hidden in headless due to WebGL)
    await page.locator("[data-testid='risk-map']").waitFor({ state: "attached", timeout: 15000 });

    // Allow time for async map operations
    await page.waitForTimeout(3000);

    // Filter out known non-critical errors (MapLibre WebGL in headless, fetch errors for tile loading)
    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes("projection") &&
        !e.includes("WebGL") &&
        !e.includes("Failed to fetch") &&
        !e.includes("ERR_CONNECTION_REFUSED") &&
        !e.includes("basemaps.cartocdn.com"),
    );

    expect(criticalErrors).toEqual([]);
  });
});
