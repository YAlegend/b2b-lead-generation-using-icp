"""Run from the repo root: python webapp/tests/test_find.py. Mocks every external API."""
import json, re, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from unittest import mock
from fastapi.testclient import TestClient
import main, discovery

import security
security.search_limiter.limit = 1000
c = TestClient(main.app)
def text(r): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(style|script).*?</\1>", "", r.text, flags=re.S)))

class Resp:
    def __init__(s, code, data): s.status_code, s._d = code, data; s.text = json.dumps(data)
    def json(s): return s._d

crit = json.dumps({"job_titles": ["CTO", "VP Engineering"], "industries_or_keywords": ["fintech"],
                   "company_size_ranges": [], "locations": ["New York"]})
people = {"people": [{"id": "a1", "first_name": "Ana", "last_name_obfuscated": "Lo***z", "title": "CTO", "organization": {"name": "PayCo"}},
                     {"id": "b2", "first_name": "Ben", "last_name_obfuscated": "K***", "title": "VP Engineering", "organization": {"name": "Ledgr"}}]}
data = {"query": "CTOs at fintech startups in New York", "lead_provider": "apollo", "lead_key": "k", "provider": "groq", "lead_count": "5"}

def check(name, cond): print(("PASS " if cond else "FAIL ") + name); return cond

r = c.get("/find"); check("GET /find 200 + heading", r.status_code == 200 and "Help me find people" in r.text)
r = c.get("/"); check("GET / still works + link", r.status_code == 200 and 'href="/find"' in r.text)
r = c.post("/find", data={**data, "lead_key": ""}); check("missing key -> error", "Add your lead database API key" in r.text)
r = c.post("/find", data={**data, "query": " "}); check("empty query -> error", "Describe who you want to find" in r.text)

with mock.patch.object(discovery, "call_llm", return_value=crit) as llm, \
     mock.patch.object(discovery.requests, "post", return_value=Resp(200, people)) as post:
    r = c.post("/find", data=data); t = text(r)
    body = post.call_args.kwargs["json"]
    check("apollo request built from criteria", body["person_titles"] == ["CTO", "VP Engineering"] and body["person_locations"] == ["New York"] and "organization_num_employees_ranges" not in body)
    check("uses QUERY_SYSTEM prompt", llm.call_args.args[3] is discovery.QUERY_SYSTEM)
    check("criteria chips shown", "Title CTO" in t and "Location New York" in t and "Industry fintech" in t)
    check("table rows + count", "2 people found" in t and "Ana Lo***z" in t and "Ledgr" in t)
    check("csv embedded", "name,title,company,email" in r.text and "Download CSV" in r.text)
    check("no email column when not revealed", "<th>Email</th>" not in r.text)
    check("query + count preserved", "CTOs at fintech startups in New York" in r.text and 'value="5"' in r.text)

with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", side_effect=[Resp(200, people), Resp(200, {"matches": [{"first_name": "Ana", "last_name": "Lopez", "email": "ana@payco.com"}, {}]})]):
    r = c.post("/find", data={**data, "with_emails": "true"}); t = text(r)
    check("reveal -> email column, full name, 'not found'", "<th>Email</th>" in r.text and "ana@payco.com" in t and "Ana Lopez" in t and "not found" in t)

with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", return_value=Resp(200, {"people": []})):
    r = c.post("/find", data=data); check("no matches -> empty state", "Nobody matched" in r.text)

with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", return_value=Resp(401, {"error": "invalid api key"})):
    r = c.post("/find", data=data); check("bad key -> provider error shown", "Apollo search returned 401" in r.text and "invalid api key" in r.text)

with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", side_effect=discovery.requests.ConnectionError("down")):
    r = c.post("/find", data=data); check("network error -> friendly error, not 500", r.status_code == 200 and "Could not reach apollo" in r.text)

with mock.patch.object(discovery, "call_llm", return_value='{"job_titles":[],"industries_or_keywords":[],"company_size_ranges":[],"locations":[]}'):
    r = c.post("/find", data={**data, "query": "hello"}); check("unparseable search -> guidance", "Couldn&#39;t pick out any" in r.text)

rr = {"profiles": [{"id": 7, "name": "Cara Diaz", "current_title": "CTO", "current_employer": "Fintro"}]}
with mock.patch.object(discovery, "call_llm", return_value=crit), \
     mock.patch.object(discovery.requests, "post", return_value=Resp(200, rr)) as post:
    r = c.post("/find", data={**data, "lead_provider": "rocketreach"})
    check("rocketreach path", "Cara Diaz" in r.text and post.call_args.kwargs["headers"]["Api-Key"] == "k" and "1 person found" in text(r))
