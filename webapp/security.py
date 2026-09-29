"""
Protections for the public web app.

The app runs on a public URL, handles people's API keys, spends the
server's own Groq key on every request, and fetches whatever URL a visitor
types in. This module covers each of those:

  - security headers + a per-request CSP nonce (limits what XSS could do
    with keys held in the page or in localStorage)
  - per-IP rate limiting on the expensive POST endpoints (bots/crawlers
    burning the server's LLM quota or hammering provider APIs)
  - SSRF-safe website fetching (no internal/cloud-metadata addresses, each
    redirect hop re-checked, response size capped)
  - redaction of submitted keys from any error text shown back
"""

from __future__ import annotations

import ipaddress
import os
import secrets
import socket
import threading
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from fastapi import Request

from run import extract_text

HONEYPOT_FIELD = "company_fax"  # hidden input: humans never fill it, form bots do

CSP = (
    "default-src 'self'; "
    "script-src 'nonce-{nonce}'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'; "
    "object-src 'none'"
)


async def security_headers(request: Request, call_next):
    request.state.csp_nonce = secrets.token_urlsafe(16)
    response = await call_next(request)
    h = response.headers
    h["Content-Security-Policy"] = CSP.format(nonce=request.state.csp_nonce)
    h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    h["X-Robots-Tag"] = "noindex, nofollow"
    if not request.url.path.startswith("/static/"):
        h["Cache-Control"] = "no-store"
    return response


# ── Rate limiting ────────────────────────────────────────────────────────

def client_ip(request: Request) -> str:
    # Render sits behind a proxy, so request.client is the proxy. The
    # leftmost X-Forwarded-For entry is the original client — but a client
    # can forge it to dodge its per-IP bucket, which is why server_key_limiter
    # below also caps total spend on the server's own key, unspoofably.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limit per key, in memory (one Render instance)."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque] = {}
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if len(self.hits) > 10_000:
                self.hits = {k: q for k, q in self.hits.items() if q and now - q[-1] < self.window}
            q = self.hits.setdefault(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


search_limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_10_MIN", "10")), 600)
# Site-wide cap on runs paid for by the server's GROQ_API_KEY (visitors who
# bring their own AI key aren't counted).
server_key_limiter = RateLimiter(int(os.getenv("SERVER_KEY_RUNS_PER_HOUR", "60")), 3600)


# ── SSRF-safe fetch ──────────────────────────────────────────────────────

MAX_PAGE_BYTES = 2_000_000


def check_public_url(url: str) -> None:
    """Raise ValueError unless url is http(s) to a public internet address."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only http:// and https:// website addresses are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("Website addresses with a username or password aren't allowed.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Couldn't find a website at {parsed.hostname}.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError("That address points to a private or internal network, which isn't allowed.")


def fetch_public_website(url: str) -> str:
    """Fetch readable text from a public website, re-checking every redirect."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"}
    for _ in range(5):
        check_public_url(url)
        with requests.get(url, headers=headers, timeout=15, stream=True, allow_redirects=False) as resp:
            if resp.is_redirect:
                url = urljoin(url, resp.headers.get("location", ""))
                continue
            resp.raise_for_status()
            body = resp.raw.read(MAX_PAGE_BYTES + 1, decode_content=True)
            if len(body) > MAX_PAGE_BYTES:
                body = body[:MAX_PAGE_BYTES]
            html = body.decode(resp.encoding or "utf-8", errors="replace")
            return extract_text(html)
    raise ValueError("That website redirected too many times.")


# ── Redaction ────────────────────────────────────────────────────────────

def redact(text: str, *keys: str) -> str:
    """Strip submitted keys (and the server's own key) out of text shown on a page."""
    for key in (*keys, os.getenv("GROQ_API_KEY", "")):
        if key and len(key) >= 6:
            text = text.replace(key, "[redacted]")
    return text
