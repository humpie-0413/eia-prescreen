import type { Page } from "@playwright/test";
import {
  SCREENING_RESPONSE,
  SCREENING_DETAIL_RESPONSE,
  SCREENINGS_LIST,
  EVALUATION_RESPONSE,
  CHECKLIST_RESPONSE,
  CASES_RESPONSE,
  DRAFT_RESPONSE,
  DATA_STATUS_RESPONSE,
  PREDICTION_RESPONSE,
  REVIEW_PREDICTION_RESPONSE,
  QUALITY_CHECK_RESPONSE,
  COMPARE_RESPONSE,
  INTERPRETATION_RESPONSE,
  RAG_RESPONSE,
  MOCK_PDF_BODY,
  EMPTY_EVALUATION,
  EMPTY_CASES,
  EMPTY_DRAFT,
  EMPTY_DATA_STATUS,
  EMPTY_PREDICTION,
  EMPTY_REVIEW_PREDICTION,
  EMPTY_QUALITY_CHECK,
  EMPTY_COMPARE,
} from "../fixtures/api-stubs";

/**
 * Intercept all backend API calls and return realistic mock data.
 * Use in beforeEach for normal-path E2E tests.
 */
export async function setupApiMocks(page: Page) {
  // Screening CRUD
  await page.route("**/api/screening", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: SCREENING_RESPONSE });
    }
    return route.fulfill({ status: 200, json: SCREENINGS_LIST });
  });

  // Compare must be registered BEFORE the wildcard /api/screening/* routes
  await page.route("**/api/screening/compare/report*", (route) =>
    route.fulfill({
      status: 200,
      headers: { "content-type": "application/pdf" },
      body: MOCK_PDF_BODY,
    }),
  );

  await page.route("**/api/screening/compare*", (route) =>
    route.fulfill({ status: 200, json: COMPARE_RESPONSE }),
  );

  // Evaluate
  await page.route("**/api/screening/*/evaluate*", (route) =>
    route.fulfill({ status: 200, json: EVALUATION_RESPONSE }),
  );

  // Checklist
  await page.route("**/api/screening/*/checklist*", (route) =>
    route.fulfill({ status: 200, json: CHECKLIST_RESPONSE }),
  );

  // Similar cases
  await page.route("**/api/screening/*/similar-cases*", (route) =>
    route.fulfill({ status: 200, json: CASES_RESPONSE }),
  );

  // Cases search
  await page.route("**/api/cases*", (route) =>
    route.fulfill({ status: 200, json: CASES_RESPONSE }),
  );

  // Draft
  await page.route("**/api/screening/*/draft*", (route) =>
    route.fulfill({ status: 200, json: DRAFT_RESPONSE }),
  );

  // Data status
  await page.route("**/api/data-status/**", (route) =>
    route.fulfill({ status: 200, json: DATA_STATUS_RESPONSE }),
  );

  // Patterns
  await page.route("**/api/patterns/**", (route) =>
    route.fulfill({ status: 200, json: PREDICTION_RESPONSE }),
  );

  // Predict review
  await page.route("**/api/screening/*/predict-review*", (route) =>
    route.fulfill({ status: 200, json: REVIEW_PREDICTION_RESPONSE }),
  );

  // Quality check
  await page.route("**/api/screening/*/quality-check*", (route) =>
    route.fulfill({ status: 200, json: QUALITY_CHECK_RESPONSE }),
  );

  // Interpretation (DeepSeek LLM)
  await page.route("**/api/screening/*/interpret*", (route) =>
    route.fulfill({ status: 200, json: INTERPRETATION_RESPONSE }),
  );

  // RAG query
  await page.route("**/api/rag/**", (route) =>
    route.fulfill({ status: 200, json: RAG_RESPONSE }),
  );

  // Report PDF
  await page.route("**/api/screening/*/report*", (route) =>
    route.fulfill({
      status: 200,
      headers: { "content-type": "application/pdf" },
      body: MOCK_PDF_BODY,
    }),
  );

  // Individual screening GET — MUST be last (catch-all for /api/screening/:id)
  // Only handle GET; fallback for POST so compare/evaluate routes still work
  await page.route("**/api/screening/*", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ status: 200, json: SCREENING_DETAIL_RESPONSE });
    }
    return route.fallback();
  });
}

/**
 * Intercept all backend API calls and return 500 errors.
 * Use to test ErrorState rendering and error handling.
 */
export async function setupErrorMocks(page: Page) {
  const errorBody = { detail: "Internal Server Error" };

  await page.route("**/api/screening", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 500, json: errorBody });
    }
    return route.fulfill({ status: 500, json: errorBody });
  });

  await page.route("**/api/screening/compare*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/evaluate*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/checklist*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/similar-cases*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/cases*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/draft*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/data-status/**", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/patterns/**", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/predict-review*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/quality-check*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/interpret*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/rag/**", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  await page.route("**/api/screening/*/report*", (route) =>
    route.fulfill({ status: 500, json: errorBody }),
  );

  // Individual screening GET
  await page.route("**/api/screening/*", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ status: 500, json: errorBody });
    }
    return route.fallback();
  });
}

/**
 * Intercept all backend API calls and return empty (but valid) responses.
 * Use to test EmptyState rendering and zero-data scenarios.
 */
export async function setupEmptyMocks(page: Page) {
  await page.route("**/api/screening", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: SCREENING_RESPONSE });
    }
    return route.fulfill({ status: 200, json: [] });
  });

  await page.route("**/api/screening/compare*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_COMPARE }),
  );

  await page.route("**/api/screening/*/evaluate*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_EVALUATION }),
  );

  await page.route("**/api/screening/*/checklist*", (route) =>
    route.fulfill({
      status: 200,
      json: { screening_id: "test-001", total_items: 0, sections: [] },
    }),
  );

  await page.route("**/api/screening/*/similar-cases*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_CASES }),
  );

  await page.route("**/api/cases*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_CASES }),
  );

  await page.route("**/api/screening/*/draft*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_DRAFT }),
  );

  await page.route("**/api/data-status/**", (route) =>
    route.fulfill({ status: 200, json: EMPTY_DATA_STATUS }),
  );

  await page.route("**/api/patterns/**", (route) =>
    route.fulfill({ status: 200, json: EMPTY_PREDICTION }),
  );

  await page.route("**/api/screening/*/predict-review*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_REVIEW_PREDICTION }),
  );

  await page.route("**/api/screening/*/quality-check*", (route) =>
    route.fulfill({ status: 200, json: EMPTY_QUALITY_CHECK }),
  );

  await page.route("**/api/screening/*/interpret*", (route) =>
    route.fulfill({
      status: 200,
      json: { screening_id: "test-001", interpretation: "", disclaimer: "" },
    }),
  );

  await page.route("**/api/rag/**", (route) =>
    route.fulfill({
      status: 200,
      json: { answer: "", sources: [], total_indexed: 0, disclaimer: "" },
    }),
  );

  await page.route("**/api/screening/*/report*", (route) =>
    route.fulfill({
      status: 200,
      headers: { "content-type": "application/pdf" },
      body: MOCK_PDF_BODY,
    }),
  );

  // Individual screening GET
  await page.route("**/api/screening/*", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ status: 200, json: SCREENING_DETAIL_RESPONSE });
    }
    return route.fallback();
  });
}

/** @deprecated Use setupApiMocks instead */
export const mockAllApiRoutes = setupApiMocks;
