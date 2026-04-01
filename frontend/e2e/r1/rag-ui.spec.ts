import { test, expect } from "@playwright/test";
import { setupApiMocks } from "../helpers/mock-api";

test.describe("R1 RAG UI — Query, response, and source cards", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test("RAG page renders with input and submit button", async ({ page }) => {
    await page.goto("/screening/test-001/rag");

    // Page heading
    await expect(page.getByText("환경영향평가서 원문 검색")).toBeVisible({ timeout: 10000 });

    // Input field
    const input = page.locator("[data-testid='rag-input']");
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute("type", "text");

    // Submit button (disabled when empty)
    const submitBtn = page.locator("[data-testid='rag-submit']");
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toBeDisabled();
  });

  test("submitting query renders AI response and source cards", async ({ page }) => {
    await page.goto("/screening/test-001/rag");

    // Type a query
    const input = page.locator("[data-testid='rag-input']");
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("도로 사업의 비산먼지 저감방안");

    // Submit button should now be enabled
    const submitBtn = page.locator("[data-testid='rag-submit']");
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Response card should appear with RAG_RESPONSE stub data
    const responseCard = page.locator("[data-testid='rag-response']");
    await expect(responseCard).toBeVisible({ timeout: 10000 });

    // Answer text from stub: "도로 사업의 비산먼지 저감방안으로는 포장, 살수, 방진망 설치 등이 있습니다."
    await expect(page.getByText("비산먼지 저감방안")).toBeVisible();

    // RAG 기반 badge (scope to response card to avoid matching subtitle text)
    await expect(responseCard.getByText("RAG 기반")).toBeVisible();
  });

  test("source cards render with metadata", async ({ page }) => {
    await page.goto("/screening/test-001/rag");

    // Submit a query
    const input = page.locator("[data-testid='rag-input']");
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("비산먼지");
    await page.locator("[data-testid='rag-submit']").click();

    // Wait for response
    await expect(page.locator("[data-testid='rag-response']")).toBeVisible({ timeout: 10000 });

    // Source card should exist
    const sourceCard = page.locator("[data-testid='rag-source']");
    await expect(sourceCard.first()).toBeVisible();

    // Source metadata from RAG_RESPONSE stub
    await expect(page.getByText("경주 도로 사업")).toBeVisible();
    await expect(page.getByText("2024")).toBeVisible();
    await expect(page.getByText("94%")).toBeVisible(); // similarity 0.94 → 94%

    // Disclaimer text
    await expect(page.getByText(/참고용/)).toBeVisible();
  });

  test("empty query does not submit", async ({ page }) => {
    await page.goto("/screening/test-001/rag");

    const input = page.locator("[data-testid='rag-input']");
    await expect(input).toBeVisible({ timeout: 10000 });

    // Submit button disabled when input empty
    const submitBtn = page.locator("[data-testid='rag-submit']");
    await expect(submitBtn).toBeDisabled();

    // Type spaces only — should still be disabled
    await input.fill("   ");
    await expect(submitBtn).toBeDisabled();

    // No response card should appear
    await expect(page.locator("[data-testid='rag-response']")).not.toBeVisible();
  });

  test("Enter key submits query", async ({ page }) => {
    await page.goto("/screening/test-001/rag");

    const input = page.locator("[data-testid='rag-input']");
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("비산먼지 저감");

    // Press Enter to submit
    await input.press("Enter");

    // Response should appear
    await expect(page.locator("[data-testid='rag-response']")).toBeVisible({ timeout: 10000 });
  });
});
