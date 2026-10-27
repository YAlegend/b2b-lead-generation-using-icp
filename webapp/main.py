"""
B2B Outreach Framework — Web App

The non-technical front door to the framework: fill in a form, get your
product/ICP/email-sequence files and (optionally) a first batch of leads,
no terminal required.
"""

import csv
import io
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run import PRODUCT_SYSTEM, PRODUCT_PROMPT, TARGET_SYSTEM, TARGET_PROMPT  # noqa: E402

from llm import call_llm, PROVIDERS, LLMError  # noqa: E402
from leads import find_leads, LeadsError  # noqa: E402
from discovery import find_leads_apollo, find_leads_rocketreach, search_people, DiscoveryError  # noqa: E402
from security import (  # noqa: E402
    HONEYPOT_FIELD, client_ip, fetch_public_website, redact,
    search_limiter, security_headers, server_key_limiter,
)

# No /docs, /redoc or /openapi.json: nothing for crawlers to enumerate.
app = FastAPI(title="B2B Outreach Framework", docs_url=None, redoc_url=None, openapi_url=None)
app.middleware("http")(security_headers)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

MAX_QUERY_CHARS = 500
MAX_DESCRIPTION_CHARS = 2000


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return "User-agent: *\nDisallow: /\n"


def _abuse_check(request: Request, honeypot: str, provider: str, api_key: str) -> str:
    """Return an error message if this submission should be refused, else ''."""
    if honeypot:
        return "Something went wrong. Please try again."
    if not search_limiter.allow(client_ip(request)):
        return "Too many searches from your connection. Please wait a few minutes and try again."
    if provider == "groq" and not api_key and not server_key_limiter.allow("server"):
        return "The free AI model is busy right now. Add your own AI key, or try again later."
    return ""

EMAIL_SYSTEM = """You are a B2B sales copywriter writing a cold email sequence
for use in an AI-powered lead generation tool called OpenOutreach.
You know nothing about the recipient. Every fact about the recipient, and
every number, result or customer you have not been given, is a [placeholder].
Output ONLY the markdown content — no preamble, no explanation."""

EMAIL_PROMPT = """
Here is a company's product description and target market:

PRODUCT:
{product}

TARGET MARKET:
{target}

Write a 3-email cold outreach sequence for this company, following these rules:

- Email 1: 120 words MAX, no exceptions
- Email 2 (Follow-Up, Day 5): 80 words MAX
- Email 3 (Breakup, Day 12): 60 words MAX
- Subject line under 8 words, no clickbait, no ALL CAPS
- One soft CTA per email (a 20-minute call) — never a hard sell
- Email 1's first line must be exactly this placeholder, on its own line,
  and nothing else about the recipient anywhere in the sequence:
  [Hook: one specific, true detail about the recipient's company]
- You know NOTHING about the recipient. Do not guess their plans, projects,
  priorities, news, budget year or pain points. Banned: "your recent",
  "your push to", "your plans", "I noticed", "I saw", "congratulations",
  "as you expand", or any year or date
- Never invent facts about the sender either: no statistics, numbers,
  timeframes ("live within weeks"), results ("operators report…"), customer
  names or features unless they appear word-for-word in the PRODUCT text.
  If a claim would help but isn't there, write a [placeholder] instead
- Tone must match the target market's industry (formal for professional
  services, concise/peer-level for tech, etc.)

Output as markdown with this structure:

# Cold Email Sequence

## Email 1 — Day 0
**Subject:** ...

[Hook: one specific, true detail about the recipient's company]

[body]

## Email 2 — Follow-Up (Day 5)
**Subject:** ...

[body]

## Email 3 — Breakup (Day 12)
**Subject:** ...

[body]
"""

HOOK = "[Hook: one specific, true detail about the recipient's company]"

# Phrases that claim knowledge of the recipient. Small models still write
# them despite the prompt, so sentences containing them are swapped out.
_RECIPIENT_CLAIM = re.compile(
    r"\b(your (recent|latest|new|ongoing|upcoming|current) |your (push|plans?|efforts?|focus|move|drive|initiative)\b"
    r"|you('ve| have)? (recently|just)\b|i (noticed|saw|read|came across)\b|congrat"
    r"|as you (expand|grow|scale|modernis|moderniz)|caught my eye)",
    re.I,
)
_YEAR = re.compile(r" ?\b(?:19|20)\d{2}\b")


def scrub_invented_claims(email_md: str, product_md: str) -> str:
    """Remove recipient claims and years the model made up.

    Years not in the product text are removed, and a sentence that claims
    to know the recipient is dropped (a line left empty becomes the [Hook]
    placeholder). Email 1 is made to start with the hook.
    """
    def drop_years(text: str) -> str:
        return _YEAR.sub(lambda m: m.group(0) if m.group(0).strip() in product_md else "", text)

    def fix_line(line: str) -> str:
        line = drop_years(line)
        if line.startswith("#") or line.startswith("**Subject"):
            return line
        kept = [p for p in re.split(r"(?<=[.!?])\s+", line) if not _RECIPIENT_CLAIM.search(p)]
        if line.strip() and not kept:
            return HOOK
        return " ".join(kept)

    out = "\n".join(fix_line(l) for l in email_md.splitlines())

    m = re.search(r"(## Email 1[^\n]*\n(?:\*\*Subject:\*\*[^\n]*\n)?\s*)", out)
    if m and HOOK not in out[m.end():m.end() + len(HOOK) + 2]:
        rest = out[m.end():]
        first, _, after = rest.partition("\n")
        if re.fullmatch(r"\[[^\]]*\]\s*", first):  # model's own lone placeholder
            rest = after
        out = out[:m.end()] + HOOK + "\n\n" + rest.lstrip("\n")
    return re.sub(r"\n{3,}", "\n\n", out)


def _slug_from(url: str, description: str) -> str:
    if url:
        domain = (urlparse(url).hostname or "").replace("www.", "")
        slug = re.sub(r"[^a-z0-9-]", "", domain.split(".")[0].lower())
        if slug:
            return slug
    return "my-company"


def _parse_leads_csv(raw: str):
    """Parse OpenOutreach's CSV stdout into (header, rows) for table display."""
    raw = raw.strip()
    if not raw:
        return [], []
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _llm_env_for(provider: str, api_key: str) -> dict:
    """Env vars so OpenOutreach's own LLM calls use the same provider/key."""
    if provider == "anthropic" and api_key:
        return {"ANTHROPIC_API_KEY": api_key}
    if provider == "openai" and api_key:
        return {"OPENAI_API_KEY": api_key}
    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if key:
            return {
                "OPENAI_API_KEY": key,
                "OPENAI_BASE_URL": "https://api.groq.com/openai/v1",
                "OPENAI_MODEL": PROVIDERS["groq"]["default_model"],
            }
    return {}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "providers": PROVIDERS}
    )


@app.get("/find", response_class=HTMLResponse)
def find_page(request: Request):
    return templates.TemplateResponse(
        "find.html", {"request": request, "providers": PROVIDERS, "form": {}}
    )


@app.post("/find", response_class=HTMLResponse)
def find(
    request: Request,
    query: str = Form(""),
    lead_provider: str = Form("apollo"),
    lead_key: str = Form(""),
    provider: str = Form("groq"),
    api_key: str = Form(""),
    lead_count: int = Form(10),
    with_emails: bool = Form(False),
    hunter_key: str = Form(""),
    qev_key: str = Form(""),
    company_fax: str = Form(""),  # honeypot, see security.HONEYPOT_FIELD
):
    lead_key, api_key = lead_key.strip(), api_key.strip()
    hunter_key, qev_key = hunter_key.strip(), qev_key.strip()
    form = {
        "query": query.strip()[:MAX_QUERY_CHARS], "lead_provider": lead_provider, "provider": provider,
        "lead_count": lead_count, "with_emails": with_emails,
    }
    ctx = {"request": request, "providers": PROVIDERS, "form": form}

    if not form["query"]:
        ctx["error"] = "Describe who you want to find."
    elif not lead_key:
        ctx["error"] = "Add your lead database API key under Search settings."
    elif refused := _abuse_check(request, company_fax, provider, api_key):
        ctx["error"] = refused
    else:
        try:
            criteria, rows, csv_text, notes = search_people(
                form["query"], lead_provider, lead_key, provider, api_key,
                count=max(1, min(lead_count, 100)), with_emails=with_emails,
                hunter_key=hunter_key, qev_key=qev_key,
            )
            ctx.update(searched=True, criteria=criteria, rows=rows, csv_text=csv_text,
                       notes=[redact(n, lead_key, api_key, hunter_key, qev_key) for n in notes])
        except DiscoveryError as exc:
            ctx["error"] = redact(str(exc), lead_key, api_key, hunter_key, qev_key)

    return templates.TemplateResponse("find.html", ctx)


@app.post("/generate", response_class=HTMLResponse)
def generate(
    request: Request,
    url: str = Form(""),
    description: str = Form(""),
    provider: str = Form(...),
    api_key: str = Form(""),
    discovery_provider: str = Form("bettercontact"),
    bettercontact_key: str = Form(""),
    apollo_key: str = Form(""),
    rocketreach_key: str = Form(""),
    lead_count: int = Form(10),
    with_emails: bool = Form(False),
    company_fax: str = Form(""),  # honeypot, see security.HONEYPOT_FIELD
):
    url = url.strip()
    description = description.strip()[:MAX_DESCRIPTION_CHARS]
    api_key = api_key.strip()
    bettercontact_key = bettercontact_key.strip()
    apollo_key = apollo_key.strip()
    rocketreach_key = rocketreach_key.strip()
    lead_count = max(1, min(lead_count, 200))
    all_keys = (api_key, bettercontact_key, apollo_key, rocketreach_key)

    def form_error(message: str):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "providers": PROVIDERS, "error": redact(message, *all_keys)},
        )

    if not url and not description:
        return form_error("Enter a company URL or a description.")
    if refused := _abuse_check(request, company_fax, provider, api_key):
        return form_error(refused)

    website_content = ""
    fetch_error = ""
    if url:
        try:
            website_content = fetch_public_website(url)
        except ValueError as exc:
            fetch_error = str(exc)
        except Exception:
            fetch_error = f"Could not read {url}."

    if not website_content and not description:
        return form_error(fetch_error or "Could not read that website — add a description instead.")

    try:
        product_md = call_llm(
            provider, api_key,
            PRODUCT_PROMPT.format(website=website_content or "(none)", description=description or "(none)"),
            PRODUCT_SYSTEM,
        )
        target_md = call_llm(
            provider, api_key,
            TARGET_PROMPT.format(website=website_content or "(none)", description=description or "(none)"),
            TARGET_SYSTEM,
        )
        email_md = call_llm(
            provider, api_key,
            EMAIL_PROMPT.format(product=product_md, target=target_md),
            EMAIL_SYSTEM,
        )
        email_md = scrub_invented_claims(email_md, product_md)
    except LLMError as exc:
        if provider == "groq" and not api_key and " 429" in str(exc):
            return form_error("The free AI model has hit its limit for now. Try again in a few minutes, "
                              "or open \"Use your own AI key\" and add a free key from console.groq.com.")
        return form_error(str(exc))

    leads_output = ""
    leads_error = ""
    leads_header, leads_rows = [], []
    try:
        if discovery_provider == "apollo" and apollo_key:
            leads_output = find_leads_apollo(
                target_md, apollo_key, provider, api_key,
                count=lead_count, with_emails=with_emails,
            )
        elif discovery_provider == "rocketreach" and rocketreach_key:
            leads_output = find_leads_rocketreach(
                target_md, rocketreach_key, provider, api_key,
                count=lead_count, with_emails=with_emails,
            )
        elif discovery_provider == "bettercontact" and bettercontact_key:
            leads_output = find_leads(
                product_md, target_md, bettercontact_key,
                count=lead_count,
                llm_env=_llm_env_for(provider, api_key),
                with_emails=with_emails,
            )
        elif bettercontact_key or apollo_key or rocketreach_key:
            leads_error = (
                f"You picked \"{discovery_provider}\" as the lead-finding provider "
                "but didn't give it a key."
            )
        leads_output = redact(leads_output, *all_keys)
        leads_header, leads_rows = _parse_leads_csv(leads_output)
    except (LeadsError, DiscoveryError) as exc:
        leads_error = redact(str(exc), *all_keys)

    slug = _slug_from(url, description)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "slug": slug,
            "product_md": product_md,
            "target_md": target_md,
            "email_md": email_md,
            "from_description_only": not website_content,
            "leads_output": leads_output,
            "leads_error": leads_error,
            "leads_header": leads_header,
            "leads_rows": leads_rows,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
