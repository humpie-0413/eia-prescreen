"""Rate limiting configuration using slowapi."""

import os
import tempfile

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_key(request: Request) -> str:
    """Rate limit key: hash of auth token if present, else IP address."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return f"user:{hash(auth)}"
    return get_remote_address(request)


# slowapi reads .env via starlette.Config with system encoding.
# On Korean Windows (cp949), UTF-8 .env with Korean comments causes UnicodeDecodeError.
# Workaround: point config_filename to a harmless empty file.
_empty = os.path.join(tempfile.gettempdir(), ".slowapi_empty")
if not os.path.exists(_empty):
    open(_empty, "w").close()

limiter = Limiter(key_func=_get_key, config_filename=_empty)

# Pre-built limit strings for common tiers
LIMIT_DEFAULT = "60/minute"
LIMIT_UNAUTHENTICATED = "10/minute"
LIMIT_LLM = "10/minute"
LIMIT_PDF = "20/minute"
