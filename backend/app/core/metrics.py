"""Prometheus 메트릭 수집 모듈.

요청 수, 응답 시간, 에러율, 커넥터 성공/실패, LLM 호출 메트릭을 수집한다.

순수 ASGI 미들웨어로 구현 (BaseHTTPMiddleware는 FastAPI dependency injection과
간섭하여 router-level dependencies가 미적용되는 버그가 있음).
"""

import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# ── HTTP 요청 메트릭 ──
REQUEST_COUNT = Counter(
    "eia_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "eia_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

REQUEST_IN_PROGRESS = Gauge(
    "eia_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
)

# ── 커넥터 메트릭 ──
CONNECTOR_REQUESTS = Counter(
    "eia_connector_requests_total",
    "Total connector fetch attempts",
    ["connector", "status"],  # status: success, fallback, error
)

CONNECTOR_LATENCY = Histogram(
    "eia_connector_duration_seconds",
    "Connector fetch latency in seconds",
    ["connector"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ── LLM 메트릭 ──
LLM_REQUESTS = Counter(
    "eia_llm_requests_total",
    "Total LLM API calls",
    ["model", "status"],  # status: success, error, no_key
)

LLM_LATENCY = Histogram(
    "eia_llm_duration_seconds",
    "LLM API call latency in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ── 규칙 엔진 메트릭 ──
RULES_EVALUATED = Counter(
    "eia_rules_evaluated_total",
    "Total rules evaluated",
)

RISKS_FOUND = Counter(
    "eia_risks_found_total",
    "Total risks found by severity",
    ["severity"],
)


class MetricsMiddleware:
    """HTTP 요청/응답 Prometheus 메트릭을 수집하는 순수 ASGI 미들웨어."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)

        # /metrics 엔드포인트는 메트릭 수집하지 않음
        if request.url.path == "/metrics":
            await self.app(scope, receive, send)
            return

        method = request.method
        path = request.url.path
        for segment in path.split("/"):
            if segment.isdigit() or (len(segment) > 20 and "-" in segment):
                path = path.replace(segment, "{id}")

        REQUEST_IN_PROGRESS.inc()
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_COUNT.labels(
                method=method, endpoint=path, status_code=status_code
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(elapsed)
            REQUEST_IN_PROGRESS.dec()


def metrics_endpoint(request: Request) -> Response:
    """GET /metrics — Prometheus 스크래핑 엔드포인트."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
