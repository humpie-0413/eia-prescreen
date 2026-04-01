import { test, expect } from "@playwright/test";
import { setupApiMocks } from "./helpers/mock-api";

test.describe("Compare page (/screening/compare)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("renders page heading and site selector", async ({ page }) => {
    await page.goto("/screening/compare");

    await expect(page.getByRole("heading", { name: "부지 비교" })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("비교 부지 선택")).toBeVisible();
  });

  test("lists evaluated screenings from API", async ({ page }) => {
    await page.goto("/screening/compare");

    // Wait for API data
    await expect(page.getByText("양평 국도 우회도로")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("세종 주거단지")).toBeVisible();
    await expect(page.getByText("보령 발전소")).toBeVisible();
  });

  test("can select up to 3 sites", async ({ page }) => {
    await page.goto("/screening/compare");

    await expect(page.getByText("양평 국도 우회도로")).toBeVisible({ timeout: 10000 });

    await page.getByText("양평 국도 우회도로").click();
    await expect(page.getByText("1번")).toBeVisible();

    await page.getByText("세종 주거단지").click();
    await expect(page.getByText("2번")).toBeVisible();

    await page.getByText("보령 발전소").click();
    await expect(page.getByText("3번")).toBeVisible();

    await expect(page.getByText("3/3 선택됨")).toBeVisible();
  });

  test("compare button executes and shows results", async ({ page }) => {
    await page.goto("/screening/compare");

    await expect(page.getByText("양평 국도 우회도로")).toBeVisible({ timeout: 10000 });

    await page.getByText("양평 국도 우회도로").click();
    await page.getByText("세종 주거단지").click();

    await page.getByText("비교 실행").click();

    await expect(page.getByText("부지별 리스크 요약")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("종합 추천")).toBeVisible();
    await expect(page.getByText("리스크 비교 매트릭스")).toBeVisible();
  });

  test("compare button disabled when less than 2 selected", async ({ page }) => {
    await page.goto("/screening/compare");

    await expect(page.getByText("비교 부지 선택")).toBeVisible({ timeout: 10000 });

    const compareBtn = page.getByText("비교 실행");
    await expect(compareBtn).toBeDisabled();

    await page.getByText("양평 국도 우회도로").click({ timeout: 10000 });
    await expect(compareBtn).toBeDisabled();
  });
});
