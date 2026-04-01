"""구조화 API 로깅 미들웨어.

모든 HTTP 요청/응답을 JSON 형식으로 기록한다.
- 요청: method, path, client IP, user_id (JWT에서 추출)
- 응답: status_code, latency_ms
- 500 에러 시 traceback 포함

순수 ASGI 미들웨어로 구현 (BaseHTTPMiddleware는 FastAPI dependency injection과
간섭하여 router-level dependencies가 미적용되는 버그가 있음).
"""

import logging
import time
from collections.abc import Callable

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("eia.api")


class APILoggingMiddleware:
    """API 요청·응답 구조화 로깅 미들웨어 (순수 ASGI)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        start = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        user_id = self._extract_user_id(request)

        # 요청 로깅
        logger.info(
            "request_start",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query),
                "client_ip": client_ip,
                "user_id": user_id,
            },
        )

        status_code = 500  # default in case we never get a response

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            log_extra = {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "user_id": user_id,
            }

            if status_code >= 500:
                logger.error("request_error", extra=log_extra)
            elif status_code >= 400:
                logger.warning("request_client_error", extra=log_extra)
            else:
                logger.info("request_complete", extra=log_extra)

    @staticmethod
    def _extract_user_id(request: Request) -> str | None:
        """Authorization 헤더에서 JWT sub claim을 추출한다 (디코드 없이 로깅용)."""
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            return f"token:{hash(auth) % 100000:05d}"
        return None
