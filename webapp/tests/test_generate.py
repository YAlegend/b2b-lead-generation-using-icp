"""Run from the repo root: python webapp/tests/test_generate.py. Mocks every external API."""
import re, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from unittest import mock
from fastapi.testclient import TestClient
import main

import security
security.search_limiter.limit = 1000
c = TestClient(main.app)

def check(name, cond): print(("PASS " if cond else "FAIL ") + name); return cond

# Home page leads with the no-key path; keys are tucked away
r = c.get("/")
check("GET / says no API key needed", r.status_code == 200 and "No API key needed" in r.text)
check("Groq is the default provider", re.search(r'<option value="groq" selected>', r.text) is not None)
check("own-key and lead settings are collapsible", 'id="ai-settings"' in r.text and 'id="lead-settings"' in r.text)

data = {"url": "", "description": "We sell X to Y", "provider": "groq", "api_key": ""}

# No key at all: ICP, emails and product are generated via the server's Groq key
with mock.patch.object(main, "fetch_public_website", return_value=""), \
     mock.patch.object(main, "call_llm", side_effect=["# Product", "# Target", "# Emails"]) as llm:
    r = c.post("/generate", data=data)
    check("no-key run produces results", r.status_code == 200 and llm.call_count == 3)
    check("no-key run used groq with empty key", all(a.args[0] == "groq" and a.args[1] == "" for a in llm.call_args_list))

# Free quota exhausted: friendly message instead of the raw Groq error
with mock.patch.object(main, "call_llm", side_effect=main.LLMError("https://api.groq.com/openai/v1 returned 429: rate_limit_exceeded")):
    r = c.post("/generate", data=data)
    check("groq 429 -> friendly limit message", "free AI model has hit its limit" in r.text and "rate_limit_exceeded" not in r.text)

# Own-key 429s still show the provider's error (it's their quota, not ours)
with mock.patch.object(main, "call_llm", side_effect=main.LLMError("https://api.openai.com/v1 returned 429: quota")):
    r = c.post("/generate", data={**data, "provider": "openai", "api_key": "sk-test"})
    check("own-key 429 keeps provider error", "returned 429" in r.text)

# Invented recipient claims and years are scrubbed from the model's emails
live = """# Cold Email Sequence

## Email 1 — Day 0
**Subject:** AI kiosk for your 2025 lobby

[specific detail about recipient's company] caught my eye, especially your recent push to modernize lobbies.

We build AI concierge kiosks. Would you have 20 minutes to see how this fits your 2025 refresh?

## Email 2 — Follow-Up (Day 5)
**Subject:** Quick follow-up

I noticed you just opened a new wing. Our kiosks speak 11 languages.
"""
out = main.scrub_invented_claims(live, "We build AI concierge kiosks in 11 languages.")
check("scrub: Email 1 starts with the hook", "**Subject:** AI kiosk for your lobby\n\n" + main.HOOK + "\n\nWe build" in out)
check("scrub: recipient claims removed", "caught my eye" not in out and "recent push" not in out and "I noticed" not in out)
check("scrub: invented years removed", "2025" not in out)
check("scrub: product facts kept", "speak 11 languages" in out and "20 minutes" in out)
with mock.patch.object(main, "fetch_public_website", return_value=""), \
     mock.patch.object(main, "call_llm", side_effect=["# Product", "# Target", live]):
    r = c.post("/generate", data=data)
    check("generate applies the scrub", "recent push" not in r.text and "Hook: one specific" in r.text)
