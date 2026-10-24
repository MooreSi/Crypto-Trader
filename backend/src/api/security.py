"""Keeps other websites from driving this dashboard.

The dashboard listens on 127.0.0.1 only and has no login, the same choice
FOREX Trader made for a single-user local app. That leaves two browser
attacks a local trading app must close, because its endpoints place orders:

* **Cross-site request forgery** -- any page the owner visits could POST to
  `http://127.0.0.1:8890/api/...`. Every request that changes something must
  carry the `X-Crypto-Trader` header. A browser will not send a custom header
  cross-origin without a CORS preflight, and this server answers no
  preflight, so a foreign page cannot add it.
* **DNS rebinding** -- a foreign domain re-pointed at 127.0.0.1 would pass a
  same-origin check. The `Host` header must name localhost or 127.0.0.1.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

CSRF_HEADER = "x-crypto-trader"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


def host_allowed(host_header: str) -> bool:
    host = host_header.rsplit(":", 1)[0] if not host_header.startswith("[") \
        else host_header.split("]")[0] + "]"
    return host.lower() in ALLOWED_HOSTS


class LocalOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not host_allowed(request.headers.get("host", "")):
            return JSONResponse({"detail": "host not allowed"}, status_code=403)
        if request.method not in SAFE_METHODS and request.url.path.startswith("/api/") \
                and request.headers.get(CSRF_HEADER) != "1":
            return JSONResponse({"detail": "missing X-Crypto-Trader header"}, status_code=403)
        return await call_next(request)
