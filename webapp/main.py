"""
B2B Outreach Framework — Web App

The non-technical front door to the framework: fill in a form, get your
product/ICP/email-sequence files and (optionally) a first batch of leads,
no terminal required.
"""

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
  recipient, not the sender
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
    bettercontact_key: str = Form(""),
    lead_count: int = Form(10),
):
    url = url.strip()
    description = description.strip()
    api_key = api_key.strip()
    bettercontact_key = bettercontact_key.strip()

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
    if bettercontact_key:
        try:
            leads_output = find_leads(
                product_md, target_md, bettercontact_key,
                count=lead_count,
                llm_env=_llm_env_for(provider, api_key),
            )
        except LeadsError as exc:
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
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
