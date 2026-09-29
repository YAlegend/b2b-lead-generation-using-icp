"""Run from the repo root: python webapp/tests/test_pdl.py. Mocks every external API."""
import json, re, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from unittest import mock
from fastapi.testclient import TestClient
import main, discovery, security
security.search_limiter.limit = 1000
c = TestClient(main.app)
def check(name, cond): print(("PASS " if cond else "FAIL ") + name)
def text(r): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script).*?</\1>", "", r.text, flags=re.S)))
class Resp:
    def __init__(s, code, data): s.status_code, s._d = code, data; s.text = json.dumps(data)
    def json(s): return s._d
crit = json.dumps({"job_titles": ["CTO", "Chief Technology Officer"], "industries_or_keywords": ["fintech"],
                   "company_size_ranges": ["11-50"], "locations": ["New York"]})
data = {"query": "CTOs at fintech startups in New York", "lead_provider": "pdl", "lead_key": "pdlkey123", "provider": "groq", "lead_count": "5"}
free = {"status": 200, "total": 2, "data": [
    {"id": "p1", "full_name": "Ana Lopez", "job_title": "CTO", "job_company_name": "PayCo", "work_email": True},
    {"id": "p2", "full_name": "Ben Kim", "job_title": "Chief Technology Officer", "job_company_name": "Ledgr", "work_email": False}]}

check("PDL option on page", 'value="pdl"' in c.get("/find").text)
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, free)) as post:
    r = c.post("/find", data=data); t = text(r)
    kw = post.call_args.kwargs; q = kw["json"]["query"]["bool"]
    check("PDL endpoint + X-Api-Key header", post.call_args.args[0] == "https://api.peopledatalabs.com/v5/person/search" and kw["headers"]["X-Api-Key"] == "pdlkey123")
    check("titles as OR of match_phrase", q["must"][0] == {"bool": {"should": [{"match_phrase": {"job_title": "cto"}}, {"match_phrase": {"job_title": "chief technology officer"}}]}})
    check("size filter uses terms", {"terms": {"job_company_size": ["11-50"]}} in q["must"])
    check("location filter", any("location_name" in json.dumps(m) for m in q["must"]))
    check("industry only ranks (should), not filters", q["should"] == [{"match": {"job_company_industry": "fintech"}}] and not any("industry" in json.dumps(m) for m in q["must"]))
    check("size param = lead count", kw["json"]["size"] == 5)
    check("rows rendered", "2 people found" in t and "Ana Lopez" in t and "Ledgr" in t)
    check("free-plan boolean email not shown as 'True'", "<th>Email</th>" not in r.text and "True" not in t)
paid = {"status": 200, "data": [{"id": "p1", "full_name": "Ana Lopez", "job_title": "CTO", "job_company_name": "PayCo", "work_email": "ana@payco.com"}]}
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(200, paid)):
    r = c.post("/find", data={**data, "with_emails": "true"}); check("paid-plan email shown", "ana@payco.com" in r.text)
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(404, {"status": 404, "error": {"type": "not_found"}})):
    r = c.post("/find", data=data); check("404 -> 'Nobody matched', not an error", "Nobody matched" in r.text and 'class="error"' not in r.text)
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(402, {"status": 402})):
    r = c.post("/find", data=data); check("402 -> free credits used up message", "used this month" in r.text)
with mock.patch.object(discovery, "call_llm", return_value=crit), mock.patch.object(discovery.requests, "post", return_value=Resp(401, {"error": {"message": "invalid key pdlkey123"}})):
    r = c.post("/find", data=data); check("401 shown, key redacted", "returned 401" in r.text and "pdlkey123" not in r.text)
