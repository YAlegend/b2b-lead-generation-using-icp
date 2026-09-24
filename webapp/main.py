"""
B2B Outreach Framework — Web App

The non-technical front door to the framework: fill in a form, get your
product/ICP/email-sequence files and (optionally) a first batch of leads,
no terminal required.
"""

import csv
import io
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run import fetch_website, PRODUCT_SYSTEM, PRODUCT_PROMPT, TARGET_SYSTEM, TARGET_PROMPT  # noqa: E402

from llm import call_llm, PROVIDERS, LLMError  # noqa: E402
from leads import find_leads, LeadsError  # noqa: E402
from discovery import find_leads_apollo, find_leads_rocketreach, DiscoveryError  # noqa: E402

app = FastAPI(title="B2B Outreach Framework")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

EMAIL_SYSTEM = """You are a B2B sales copywriter writing a cold email sequence
for use in an AI-powered lead generation tool called OpenOutreach.
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
- First line of Email 1 must reference something specific about the
  recipient, not the sender — use a bracketed placeholder like
  [specific detail about recipient's company] since you don't know them
- Never invent facts: no made-up statistics, results, customer names, or
  events (e.g. "you announced last week"). Only use claims from the
  PRODUCT text above; otherwise use a [placeholder]
- Tone must match the target market's industry (formal for professional
  services, concise/peer-level for tech, etc.)

Output as markdown with this structure:

# Cold Email Sequence

## Email 1 — Day 0
**Subject:** ...

[body]

## Email 2 — Follow-Up (Day 5)
**Subject:** ...

[body]

## Email 3 — Breakup (Day 12)
**Subject:** ...

[body]
"""


def _slug_from(url: str, description: str) -> str:
    if url:
        domain = urlparse(url).netloc.replace("www.", "")
        if domain:
            return domain.split(".")[0].lower()
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
):
    url = url.strip()
    description = description.strip()
    api_key = api_key.strip()
    bettercontact_key = bettercontact_key.strip()
    apollo_key = apollo_key.strip()
    rocketreach_key = rocketreach_key.strip()

    if not url and not description:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "providers": PROVIDERS,
                "error": "Enter a company URL or a description.",
            },
        )

    website_content = ""
    fetch_error = ""
    if url:
        try:
            website_content = fetch_website(url)
        except Exception as exc:
            fetch_error = f"Could not read {url}: {exc}"

    if not website_content and not description:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "providers": PROVIDERS,
                "error": fetch_error or "Could not read that website — add a description instead.",
            },
        )

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
    except LLMError as exc:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "providers": PROVIDERS, "error": str(exc)},
        )

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
        leads_header, leads_rows = _parse_leads_csv(leads_output)
    except (LeadsError, DiscoveryError) as exc:
        leads_error = str(exc)

    slug = _slug_from(url, description)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "slug": slug,
            "product_md": product_md,
            "target_md": target_md,
            "email_md": email_md,
            "leads_output": leads_output,
            "leads_error": leads_error,
            "leads_header": leads_header,
            "leads_rows": leads_rows,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
