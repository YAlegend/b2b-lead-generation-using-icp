#!/usr/bin/env python3
"""
B2B Outreach Framework — MCP Server
====================================
Exposes the full outreach pipeline as MCP tools so any LLM
(Claude, ChatGPT, Gemini, Cursor, etc.) can call them directly.

Usage:
  python mcp_server.py          # stdio mode (Claude Desktop, Cursor)
  python mcp_server.py --http   # HTTP mode (web-based LLMs)

Connect from any LLM tool:
  Claude Desktop → claude_desktop_config.json
  Cursor         → .cursor/mcp.json
  ChatGPT        → point at http://localhost:8000
  Any MCP client → stdio or HTTP
"""

import os
import sys
import json
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import fastmcp

# ── Helpers ───────────────────────────────────────────────────────────────────
def _load_env():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def _save_env(key: str, value: str):
    env_file = Path(".env")
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n")

def _fetch_website(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = "\n".join(
            l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()
        )
        return text[:6000]
    except Exception as e:
        return f"Could not fetch website: {e}"

def _call_llm(prompt: str, system: str = "") -> str:
    """Call whatever LLM is configured in the environment."""
    _load_env()

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system or "You are a B2B marketing expert. Be specific and thorough.",
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    # OpenAI / Ollama / OpenRouter / Gemini (OpenAI-compatible)
    if os.getenv("OPENAI_API_KEY"):
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        headers  = {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system or "You are a B2B marketing expert."},
                {"role": "user",   "content": prompt}
            ],
            "max_tokens": 4096
        }
        resp = requests.post(f"{base_url}/chat/completions",
                             json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    # Gemini (native SDK)
    if os.getenv("GEMINI_API_KEY"):
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"{system}\n\n{prompt}")
        return response.text

    raise ValueError(
        "No LLM configured. Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "GEMINI_API_KEY, or OPENAI_API_KEY + OPENAI_BASE_URL for local models."
    )

# ── Prompts ───────────────────────────────────────────────────────────────────
PRODUCT_SYSTEM = (
    "You are a B2B marketing expert writing a product description for an AI "
    "lead generation tool. Write in first person. Be specific. "
    "Output ONLY the markdown content."
)

PRODUCT_PROMPT = """
Generate a product.md file for this company.

WEBSITE CONTENT:
{website}

USER DESCRIPTION:
{description}

Structure:
# [Company Name] — Product Description
## What We Do
## What We Deliver
## Representative Work
## Why Clients Choose Us
## Engagement Size
## Who We Are Not a Fit For
"""

TARGET_SYSTEM = (
    "You are a B2B sales expert writing an Ideal Customer Profile for an AI "
    "lead generation tool. Be specific about titles, company types, and signals. "
    "Output ONLY the markdown content."
)

TARGET_PROMPT = """
Generate a target.md file for this company's outreach campaign.

WEBSITE CONTENT:
{website}

USER DESCRIPTION:
{description}

Structure:
# [Company Name] — Target Market Definition
## Who We Are Looking For
## Vertical 1 — [Name]
## Vertical 2 — [Name]
[Vertical 3 and 4 only if clearly distinct]
## Disqualifying Signals (Global)
## Geography
## What a Perfect Lead Looks Like
"""

# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = fastmcp.FastMCP(
    name="b2b-outreach-framework",
    instructions=(
        "B2B Outreach Framework: generate outreach files and find leads "
        "for any company. Start with generate_outreach_files(), then "
        "setup_openoutreach(), then find_leads()."
    )
)


@mcp.tool()
def generate_outreach_files(
    url: str = "",
    description: str = "",
    slug: str = ""
) -> str:
    """
    Step 1: Read a company website and/or description, then generate
    product.md and target.md files ready for OpenOutreach.

    Args:
        url:         Company website URL (optional but recommended)
        description: Extra context about the company (optional)
        slug:        Output folder name. Auto-derived from URL if not set.

    Returns:
        Summary of generated files and their paths.
    """
    if not url and not description:
        return "Error: provide at least one of url or description."

    # Fetch website
    website_content = _fetch_website(url) if url else ""

    # Determine slug
    if not slug:
        if url:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            slug = domain.split(".")[0].lower()
        else:
            slug = "my-company"

    output_dir = Path(slug)
    output_dir.mkdir(exist_ok=True)

    ctx = {
        "website": website_content or "(no website content)",
        "description": description or "(none)"
    }

    # Generate product.md
    product_md = _call_llm(PRODUCT_PROMPT.format(**ctx), PRODUCT_SYSTEM)
    (output_dir / "product.md").write_text(product_md)

    # Generate target.md
    target_md = _call_llm(TARGET_PROMPT.format(**ctx), TARGET_SYSTEM)
    (output_dir / "target.md").write_text(target_md)

    return (
        f"✓ Files generated in '{slug}/':\n"
        f"  • {slug}/product.md  ({len(product_md)} chars)\n"
        f"  • {slug}/target.md   ({len(target_md)} chars)\n\n"
        f"Next: call setup_openoutreach(slug='{slug}') to configure lead finding."
    )


@mcp.tool()
def setup_openoutreach(slug: str) -> str:
    """
    Step 2: Install OpenOutreach and run the setup wizard using the
    generated product.md and target.md for the given company slug.

    Args:
        slug: The company folder name from generate_outreach_files()

    Returns:
        Setup status and next steps.
    """
    output_dir = Path(slug)
    product_path = output_dir / "product.md"
    target_path  = output_dir / "target.md"

    if not product_path.exists() or not target_path.exists():
        return (
            f"Error: '{slug}/product.md' or '{slug}/target.md' not found.\n"
            f"Run generate_outreach_files() first."
        )

    # Install OpenOutreach if needed
    if subprocess.run(["openoutreach", "--help"],
                      capture_output=True).returncode != 0:
        try:
            subprocess.check_call(["uv", "tool", "install", "openoutreach"])
        except Exception as e:
            return f"Error installing OpenOutreach: {e}\nInstall manually: uv tool install openoutreach"

    return (
        f"✓ OpenOutreach is ready.\n\n"
        f"Run this command in your terminal to complete setup:\n\n"
        f"  openoutreach init --product-docs {product_path} --target {target_path}\n\n"
        f"The wizard will ask for:\n"
        f"  1. LLM API key (Anthropic / OpenAI / any compatible)\n"
        f"  2. BetterContact key — bettercontact.rocks (40 free credits)\n"
        f"  3. Sending Gmail address\n"
        f"  4. Gmail app password (Google Account → Security → App Passwords)\n\n"
        f"After setup, call find_leads(slug='{slug}') or run 'openoutreach run 50'."
    )


@mcp.tool()
def find_leads(slug: str, count: int = 10, with_emails: bool = False) -> str:
    """
    Step 3: Find leads matching the ICP defined in target.md.

    Args:
        slug:        Company folder name from generate_outreach_files()
        count:       Number of leads to find (default 10)
        with_emails: If True, buy verified email addresses (uses BetterContact credits).
                     If False, find leads only — free, no credits spent.

    Returns:
        Lead results or instructions to run the command.
    """
    cmd = ["openoutreach", "find", str(count)]
    if with_emails:
        cmd.append("emails")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if "not configured" in result.stderr.lower() or "wizard" in result.stderr.lower():
            return (
                f"OpenOutreach is not configured yet.\n"
                f"Run setup_openoutreach(slug='{slug}') first, then complete the wizard in your terminal."
            )
        return f"Error: {result.stderr}\n\nRun in terminal: {' '.join(cmd)}"

    output = result.stdout or result.stderr
    return (
        f"✓ Lead search complete.\n\n"
        f"{output}\n\n"
        f"To find more leads with emails:\n"
        f"  openoutreach find 50 emails > {slug}/leads.csv\n\n"
        f"To find and email automatically:\n"
        f"  openoutreach run 50"
    )


@mcp.tool()
def get_status() -> str:
    """
    Check OpenOutreach configuration and lead pipeline status.

    Returns:
        Current status: what's configured, how many leads found, next steps.
    """
    result = subprocess.run(
        ["openoutreach", "status"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return (
            "OpenOutreach is not set up yet.\n\n"
            "Start with:\n"
            "  1. generate_outreach_files(url='https://yourcompany.com')\n"
            "  2. setup_openoutreach(slug='your-company')\n"
            "  3. find_leads(slug='your-company')"
        )
    return result.stdout or result.stderr


@mcp.tool()
def configure_llm(
    provider: str,
    api_key: str,
    model: str = "",
    base_url: str = ""
) -> str:
    """
    Configure which LLM to use for generating outreach files.
    Only needed once — saved to .env for all future runs.

    Args:
        provider: One of: anthropic, openai, gemini, ollama, openrouter, or any
        api_key:  Your API key for the provider
        model:    Model name (optional — uses a sensible default per provider)
        base_url: Custom base URL (for Ollama, OpenRouter, or any OpenAI-compatible)

    Returns:
        Confirmation of what was saved.
    """
    provider = provider.lower()

    defaults = {
        "anthropic":  ("ANTHROPIC_API_KEY",  None,                           "claude-sonnet-4-6"),
        "openai":     ("OPENAI_API_KEY",      "https://api.openai.com/v1",    "gpt-4o-mini"),
        "gemini":     ("GEMINI_API_KEY",      None,                           "gemini-1.5-flash"),
        "openrouter": ("OPENAI_API_KEY",      "https://openrouter.ai/api/v1", "nousresearch/hermes-3-llama-3.1-70b"),
        "ollama":     ("OPENAI_API_KEY",      "http://localhost:11434/v1",    "nous-hermes2"),
    }

    if provider in defaults:
        key_name, default_url, default_model = defaults[provider]
        _save_env(key_name, api_key)
        if default_url:
            _save_env("OPENAI_BASE_URL", base_url or default_url)
        if model or default_model:
            _save_env("OPENAI_MODEL", model or default_model)
    else:
        # Generic OpenAI-compatible
        _save_env("OPENAI_API_KEY", api_key)
        if base_url:
            _save_env("OPENAI_BASE_URL", base_url)
        if model:
            _save_env("OPENAI_MODEL", model)

    _load_env()
    return (
        f"✓ LLM configured: {provider}\n"
        f"  Model: {model or (defaults.get(provider, ('','',''))[2]) or 'default'}\n"
        f"  Saved to .env — you won't need to do this again.\n\n"
        f"Now call generate_outreach_files(url='https://yourcompany.com')"
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _load_env()

    if "--http" in sys.argv:
        # HTTP mode — for web-based LLMs and remote connections
        port = int(os.getenv("PORT", "8000"))
        print(f"Starting B2B Outreach MCP server on http://localhost:{port}")
        print("Connect any MCP-compatible LLM to this address.")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        # stdio mode — for Claude Desktop, Cursor, VS Code, etc.
        mcp.run(transport="stdio")


# ── Quality Loop Tools ────────────────────────────────────────────────────────

@mcp.tool()
def run_quality_gate(slug: str) -> str:
    """
    Run the pre-send quality gate for a campaign:
    Loop 1: Check + improve product.md and target.md (blocks until pass)
    Loop 2: Score leads, reject weak ones, tighten ICP if >30% rejected
    Shows a diff for every change and asks approval before writing.
    Call this BEFORE running find_leads() or sending any emails.
    Args:
        slug: Company folder name
    """
    result = subprocess.run(
        ["python3", "improver.py", "--slug", slug, "--mode", "gate"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    return result.stdout or result.stderr


@mcp.tool()
def start_watch(slug: str, interval_hours: int = 24) -> str:
    """
    Start the scheduled reply monitor for a campaign.
    Runs Loop 3 every N hours: reads Gmail, classifies replies,
    rewrites emails if reply rate is low, refines ICP if wrong-person
    rate is high. Shows diffs and asks approval before each change.
    Runs until stopped — best used as a background process.
    Args:
        slug:           Company folder name
        interval_hours: Hours between checks (default 24)
    """
    result = subprocess.run(
        ["python3", "improver.py", "--slug", slug,
         "--mode", "watch", "--interval", str(interval_hours)],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    return result.stdout or result.stderr


@mcp.tool()
def start_auto(slug: str, interval_hours: int = 24) -> str:
    """
    Fully autonomous mode — runs all loops on a schedule with no
    approval prompts. Improves files, scores leads, monitors replies,
    rewrites emails and ICP automatically. Logs everything to
    .loop_state.json. Use this for hands-off campaigns.
    Args:
        slug:           Company folder name
        interval_hours: Hours between runs (default 24)
    """
    result = subprocess.run(
        ["python3", "improver.py", "--slug", slug,
         "--mode", "auto", "--interval", str(interval_hours)],
        capture_output=True, text=True, cwd=str(Path(__file__).parent)
    )
    return result.stdout or result.stderr


@mcp.tool()
def get_campaign_status(slug: str) -> str:
    """
    Show the current campaign dashboard: reply rate, positive rate,
    how many improvements have been made, and what changed.
    Args:
        slug: Company folder name
    """
    state_file = Path(slug) / ".loop_state.json"
    if not state_file.exists():
        return (
            f"No campaign data found for '{slug}'.\n"
            f"Run run_quality_gate(slug='{slug}') first."
        )
    state = json.loads(state_file.read_text())
    lines = [
        f"Campaign: {slug}",
        f"Loops run: {state.get('loop_count', 0)}",
        f"Last run:  {state.get('last_run', 'never')[:16].replace('T',' ')}",
        "",
        f"Files:    quality {'passed ✓' if state.get('file_quality_passed') else 'not checked'}  |  rewrites: {state.get('file_rewrites',0)}",
        f"Leads:    scored {state.get('leads_scored',0)}  |  rejected {state.get('leads_rejected',0)}  |  ICP refinements: {state.get('target_rewrites',0)}",
        f"Emails:   sent {state.get('emails_sent',0)}  |  reply rate {state.get('reply_rate',0):.1f}%  |  positive {state.get('positive_rate',0):.1f}%",
        f"Rewrites: emails {state.get('email_rewrites',0)}  |  ICP {state.get('target_rewrites',0)}",
        "",
    ]
    improvements = state.get("improvements", [])
    if improvements:
        lines.append(f"Improvements ({len(improvements)} total):")
        for imp in improvements[-5:]:
            ts = imp.get("timestamp","")[:16].replace("T"," ")
            lines.append(f"  [{ts}] {imp.get('loop','')} → {imp.get('label','')}")
    return "\n".join(lines)
