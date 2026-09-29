"""Run from the repo root: python webapp/tests/test_emails.py. Mocks every external API."""
import json, re, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from unittest import mock
from fastapi.testclient import TestClient
import main, discovery, emails, security
security.search_limiter.limit = 1000
c = TestClient(main.app)
def check(name, cond): print(("PASS " if cond else "FAIL ") + name)
def text(r): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script).*?</\1>", "", r.text, flags=re.S)))
class Resp:
    def __init__(s, code, data=None): s.status_code, s._d = code, data or {}; s.text = json.dumps(s._d)
    def json(s): return s._d
crit = json.dumps({"job_titles": ["CTO"], "industries_or_keywords": [], "company_size_ranges": [], "locations": []})
pdl = {"data": [
    {"id": "1", "full_name": "Ana Lopez", "job_title": "CTO", "job_company_name": "PayCo", "job_company_website": "payco.com", "work_email": True},
    {"id": "2", "full_name": "Ben Kim", "job_title": "CTO", "job_company_name": "Ledgr", "job_company_website": "ledgr.io", "work_email": True},
    {"id": "3", "full_name": "Cara Diaz", "job_title": "CTO", "job_company_name": "NoSite Inc", "work_email": False},
    {"id": "4", "full_name": "Dan", "job_title": "CTO", "job_company_name": "Solo", "work_email": False}]}
HUNTER = {"ana@payco.com": None}
def fake_get(url, headers=None, params=None, timeout=None):
    if "hunter" in url:
        assert headers["X-API-KEY"] == "hkey1234"
        found = {"Ana Lopez": "ana@payco.com", "Ben Kim": "ben@ledgr.io", "Cara Diaz": "cara@nosite.com"}.get(params["full_name"])
        return Resp(200, {"data": {"email": found}}) if found else Resp(200, {"data": {"email": None}})
    if "quickemailverification" in url:
        e = params["email"]
        return Resp(200, {"success": "true", "result": {"ana@payco.com": "valid", "ben@ledgr.io": "valid", "cara@nosite.com": "invalid"}[e],
                          "accept_all": "true" if e == "ben@ledgr.io" else "false", "disposable": "false", "safe_to_send": "true"})
data = {"query": "CTOs", "lead_provider": "pdl", "lead_key": "pdlkey99", "hunter_key": "hkey1234", "qev_key": "qkey5678"}

with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get", side_effect=fake_get) as g:
    r = c.post("/find", data=data); t = text(r)
    hunter_calls = [k.kwargs["params"] for k in g.call_args_list if "hunter" in k.args[0]]
    check("Hunter uses domain when known", {"full_name": "Ana Lopez", "max_duration": 8, "domain": "payco.com"} in hunter_calls)
    check("Hunter falls back to company name", any(p.get("company") == "NoSite Inc" for p in hunter_calls))
    check("single-word name skipped (no wasted call)", not any(p["full_name"] == "Dan" for p in hunter_calls))
    check("emails shown", "ana@payco.com" in t and "ben@ledgr.io" in t and "cara@nosite.com" in t)
    check("status column: valid / risky (accept-all) / invalid", "<th>Check</th>" in r.text and 'status valid">valid' in r.text and 'status risky">risky' in r.text and 'status invalid">invalid' in r.text)
    check("CSV includes email_status", "name,title,company,email,email_status" in r.text and "ana@payco.com,valid" in r.text)
    check("QEV only called for rows with an email", sum("quickemailverification" in k.args[0] for k in g.call_args_list) == 3)

# Hunter quota exhausted -> note, people still shown, no further Hunter calls
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get", return_value=Resp(429)) as g, mock.patch.object(emails, "WORKERS", 1):
    r = c.post("/find", data={**data, "qev_key": ""}); t = text(r)
    check("Hunter 429 -> friendly note, results still shown", "free email-finder credits are used up" in t and "Ana Lopez" in t and 'class="error"' not in r.text)
    check("stops calling Hunter after quota hit", g.call_count == 1)

# QEV out of credits / bad keys
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get", side_effect=lambda url, **k: fake_get(url, **k) if "hunter" in url else Resp(402)):
    r = c.post("/find", data=data); check("QEV 402 -> daily credits note", "100/day" in text(r) and "ana@payco.com" in r.text)
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get", return_value=Resp(401)):
    r = c.post("/find", data={**data, "qev_key": ""}); check("Hunter bad key note", "Hunter rejected the API key" in text(r))
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get", side_effect=emails.requests.ConnectionError("https://api.quickemailverification.com/v1/verify?apikey=qkey5678")):
    r = c.post("/find", data=data); check("network error note never leaks key", "Couldn" in r.text and "qkey5678" not in r.text and "hkey1234" not in r.text)

# No extra keys -> no Hunter/QEV calls at all
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, pdl)), \
     mock.patch.object(emails.requests, "get") as g:
    c.post("/find", data={**data, "hunter_key": "", "qev_key": ""}); check("no keys -> no email API calls", not g.called)
check("key fields on page", 'name="hunter_key"' in c.get("/find").text and 'name="qev_key"' in c.get("/find").text)
