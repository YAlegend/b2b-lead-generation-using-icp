"""Run from the repo root: python webapp/tests/test_security.py. Mocks every external API."""
import json, re, sys, os
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from unittest import mock
from fastapi.testclient import TestClient
import main, discovery, security
c = TestClient(main.app)
def check(name, cond): print(("PASS " if cond else "FAIL ") + name)
class Resp:
    def __init__(s, code, data, headers=None): s.status_code, s._d = code, data; s.text = json.dumps(data); s.headers = headers or {}
    def json(s): return s._d
crit = json.dumps({"job_titles": ["CTO"], "industries_or_keywords": [], "company_size_ranges": [], "locations": []})
data = {"query": "CTOs", "lead_provider": "apollo", "lead_key": "SECRET-LEAD-KEY-123", "provider": "groq", "api_key": "SECRET-AI-KEY-456"}

# Headers / crawler surface
r = c.get("/find"); h = r.headers
m = re.search(r"'nonce-([^']+)'", h.get("content-security-policy", ""))
check("CSP with nonce, nonce matches script tag", m and f'<script nonce="{m.group(1)}">' in r.text)
check("CSP blocks framing/base/object", all(x in h["content-security-policy"] for x in ["frame-ancestors 'none'", "base-uri 'none'", "object-src 'none'"]))
check("HSTS, nosniff, DENY, no-referrer, noindex, no-store", h.get("strict-transport-security", "").startswith("max-age") and h.get("x-content-type-options") == "nosniff"
      and h.get("x-frame-options") == "DENY" and h.get("referrer-policy") == "no-referrer" and "noindex" in h.get("x-robots-tag", "") and h.get("cache-control") == "no-store")
check("nonce changes per request", re.search(r"'nonce-([^']+)'", c.get("/find").headers["content-security-policy"]).group(1) != m.group(1))
check("no inline event handlers in any page", all("onclick=" not in c.get(p).text for p in ["/", "/find"]))
check("/docs, /redoc, /openapi.json disabled", all(c.get(p).status_code == 404 for p in ["/docs", "/redoc", "/openapi.json"]))
r = c.get("/robots.txt"); check("robots.txt disallows all", "Disallow: /" in r.text)
check("static css still served + cacheable", c.get("/static/brand.css").status_code == 200 and "no-store" not in c.get("/static/brand.css").headers.get("cache-control", ""))

# Keys never echoed back; errors redacted
with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", return_value=Resp(401, {"error": "bad key SECRET-LEAD-KEY-123"})):
    r = c.post("/find", data=data)
    check("provider error shown but key redacted", "401" in r.text and "[redacted]" in r.text and "SECRET-LEAD-KEY-123" not in r.text and "SECRET-AI-KEY-456" not in r.text)
with mock.patch.dict(os.environ, {"GROQ_API_KEY": "gsk_SERVERKEY999"}):
    check("server Groq key always redacted", security.redact("leak gsk_SERVERKEY999 here") == "leak [redacted] here")

# Honeypot
with mock.patch.object(discovery, "search_people") as sp, mock.patch.object(main, "search_people") as sp2:
    r = c.post("/find", data={**data, "company_fax": "bot"}); check("honeypot blocks bot, no search run", not sp2.called and "Something went wrong" in r.text)
check("honeypot field present in both forms", all('name="company_fax"' in c.get(p).text for p in ["/", "/find"]))

# Per-IP rate limit
security.search_limiter.hits.clear(); security.search_limiter.limit = 3
with mock.patch.object(main, "search_people", return_value=({"job_titles": []}, [], "", [])) as sp:
    codes = [("Too many searches" in c.post("/find", data=data, headers={"x-forwarded-for": "1.2.3.4"}).text) for _ in range(5)]
    check("4th+ request from same IP refused", codes == [False, False, False, True, True] and sp.call_count == 3)
    check("other IP unaffected", "Too many searches" not in c.post("/find", data=data, headers={"x-forwarded-for": "5.6.7.8"}).text)
security.search_limiter.limit = 1000

# Server-key global cap (unspoofable)
security.server_key_limiter.hits.clear(); security.server_key_limiter.limit = 2
with mock.patch.object(main, "search_people", return_value=({"job_titles": []}, [], "", [])):
    res = ["free AI model is busy" in c.post("/find", data={**data, "api_key": ""}, headers={"x-forwarded-for": f"9.9.9.{i}"}).text for i in range(3)]
    check("server-key cap holds even with rotating IPs", res == [False, False, True])
    r = c.post("/find", data=data)
    check("own AI key bypasses server-key cap", "shared AI key is busy" not in r.text and "Nobody matched" in r.text)
security.server_key_limiter.limit = 1000

# SSRF
def rejects(u):
    try: security.check_public_url(u); return False
    except ValueError: return True
for u in ["http://127.0.0.1/", "http://localhost:8000/", "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/", "http://192.168.1.1/",
          "http://[::1]/", "file:///etc/passwd", "ftp://example.com/", "http://user:pw@example.com/", "http://0.0.0.0/", "gopher://x"]:
    check(f"blocks {u}", rejects(u))
check("allows public site (example.com)", not rejects("https://example.com/"))
class Stream:
    def __init__(s, redirect_to=None, body=b"<p>hi</p>"): s.is_redirect = bool(redirect_to); s.headers = {"location": redirect_to} if redirect_to else {}; s.encoding = "utf-8"; s.raw = mock.Mock(read=lambda n, decode_content: body[:n])
    def raise_for_status(s): pass
    def __enter__(s): return s
    def __exit__(s, *a): pass
with mock.patch.object(security.requests, "get", side_effect=[Stream(redirect_to="http://169.254.169.254/latest/")]) as g:
    try: security.fetch_public_website("https://example.com/"); ok = False
    except ValueError: ok = g.call_count == 1
    check("redirect to cloud metadata blocked before request", ok)
with mock.patch.object(security.requests, "get", return_value=Stream(body=b"<p>" + b"a" * 5_000_000 + b"</p>")):
    check("oversized page capped", len(security.fetch_public_website("https://example.com/")) <= 6100)
with mock.patch.object(main, "call_llm") as llm:
    r = c.post("/generate", data={"url": "http://169.254.169.254/", "provider": "groq"})
    check("/generate refuses internal URL, no LLM spend", "private or internal network" in r.text and not llm.called)

# Slug can't inject into attributes
check("slug sanitised", main._slug_from("https://a\"onmouseover=x.com", "") in ("aonmouseoverx", "my-company") and main._slug_from("https://www.Acme-Co.io", "") == "acme-co")
