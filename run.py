#!/usr/bin/env python3
"""
B2B Outreach Framework
======================
Provide a company URL or description.
This script generates your outreach files and starts finding leads.

Usage:
  python run.py --url https://yourcompany.com
  python run.py --url https://yourcompany.com --description "We also do X"
  python run.py --description "We sell X to Y, minimum $15k projects"
"""

import os
import sys
import json
import argparse
import subprocess
import textwrap
from pathlib import Path


# ── Colour helpers ────────────────────────────────────────────────────────────
def green(t):  return f"\033[92m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def red(t):    return f"\033[91m{t}\033[0m"
def bold(t):   return f"\033[1m{t}\033[0m"
def dim(t):    return f"\033[2m{t}\033[0m"

def banner():
    print(bold("\n================================================"))
    print(bold("  B2B Outreach Framework"))
    print(bold("================================================\n"))

def step(n, total, msg):
    print(f"\n{bold(f'[{n}/{total}]')} {msg}")


# ── Dependency check ──────────────────────────────────────────────────────────
def check_dependencies():
    missing = []
    for pkg in ["requests", "bs4", "anthropic"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(yellow(f"Installing missing packages: {', '.join(missing)}"))
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "requests", "beautifulsoup4", "anthropic", "-q"])

check_dependencies()

import requests
from bs4 import BeautifulSoup


# ── Web fetch ─────────────────────────────────────────────────────────────────
def fetch_website(url: str) -> str:
    """Fetch and extract readable text from a URL."""
    print(dim(f"  Fetching {url}..."))
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OutreachBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        content = "\n".join(lines)

        # Truncate to ~6000 chars to stay within token limits
        if len(content) > 6000:
            content = content[:6000] + "\n[content truncated]"

        print(green(f"  ✓ Fetched {len(content)} characters from website"))
        return content

    except Exception as e:
        print(yellow(f"  ⚠ Could not fetch website: {e}"))
        print(dim("  Continuing with description only..."))
        return ""


# ── LLM client ────────────────────────────────────────────────────────────────
def get_llm_client():
    """Return the configured LLM caller based on environment variables."""

    # Check for Ollama / local Hermes
    ollama_url = os.getenv("OPENAI_BASE_URL", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if ollama_url and openai_key:
        print(dim(f"  Using OpenAI-compatible endpoint: {ollama_url}"))
        return "openai_compat"

    if anthropic_key:
        print(dim("  Using Anthropic API"))
        return "anthropic"

    # No key found — ask user
    print(yellow("\nNo LLM API key found. Choose one:\n"))
    print("  1. Anthropic API   → console.anthropic.com  (free $5 credit)")
    print("  2. Hermes (local)  → runs via Ollama, $0 cost")
    print("  3. OpenRouter      → openrouter.ai          (pay per token)\n")
    choice = input("Enter 1, 2, or 3: ").strip()

    if choice == "1":
        key = input("Paste your Anthropic API key: ").strip()
        os.environ["ANTHROPIC_API_KEY"] = key
        _save_env("ANTHROPIC_API_KEY", key)
        return "anthropic"

    elif choice == "2":
        print(yellow("\nOllama setup:"))
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Run: ollama pull nous-hermes2")
        print("  3. Ollama starts automatically\n")
        input("Press Enter once Ollama is running with nous-hermes2...")
        os.environ["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
        os.environ["OPENAI_API_KEY"] = "ollama"
        _save_env("OPENAI_BASE_URL", "http://localhost:11434/v1")
        _save_env("OPENAI_API_KEY", "ollama")
        return "openai_compat"

    elif choice == "3":
        key = input("Paste your OpenRouter API key: ").strip()
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        os.environ["OPENAI_API_KEY"] = key
        _save_env("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        _save_env("OPENAI_API_KEY", key)
        return "openai_compat"

    else:
        print(red("Invalid choice. Exiting."))
        sys.exit(1)


def _save_env(key: str, value: str):
    """Append to .env file for future runs."""
    env_file = Path(".env")
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n")


def _load_env():
    """Load .env if it exists."""
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def call_llm(client_type: str, prompt: str, system: str = "") -> str:
    """Call the configured LLM and return the response text."""

    if client_type == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system or "You are a B2B marketing expert. Be specific and thorough.",
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    elif client_type == "openai_compat":
        import requests as req
        base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        api_key  = os.environ.get("OPENAI_API_KEY", "ollama")
        model    = os.environ.get("OPENAI_MODEL", "nous-hermes2")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system or "You are a B2B marketing expert."},
                {"role": "user",   "content": prompt}
            ],
            "max_tokens": 4096
        }
        headers = {"Authorization": f"Bearer {api_key}",
                   "Content-Type": "application/json"}
        resp = req.post(f"{base_url}/chat/completions",
                        json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ── File generators ───────────────────────────────────────────────────────────
PRODUCT_SYSTEM = """You are a B2B marketing expert writing a product description
for use in an AI-powered lead generation tool called OpenOutreach.
Write in first person ("We..."). Be specific, not generic.
Websites often show sample data in product screenshots or demos (example
tasks, fake customers, placeholder dashboards). Ignore it — describe only what
the company itself sells and who it sells to.
Output ONLY the markdown content — no preamble, no explanation."""

PRODUCT_PROMPT = """
Here is information about a company:

WEBSITE CONTENT:
{website}

ADDITIONAL DESCRIPTION FROM USER:
{description}

Write a detailed product.md file for this company with these sections:

# [Company Name] — Product Description

## What We Do
[2-3 paragraphs describing what the company sells, the problem it solves,
and who it helps. Specific and outcome-focused.]

## What We Deliver
[Bullet list of specific services, products, or outcomes]

## Representative Work
[Any client names, case studies, or outcomes mentioned on the website.
Skip this section if none found.]

## Why Clients Choose Us
[3-5 specific differentiators based on what the website says]

## Engagement Size
[State the minimum deal size or price point if visible on the website.
If not found, write: "Contact us to discuss project scope."]

## Who We Are Not a Fit For
[Describe out-of-scope clients or projects based on the company's positioning]
"""

TARGET_SYSTEM = """You are a B2B sales expert writing an Ideal Customer Profile (ICP)
for use in an AI-powered lead generation tool called OpenOutreach.
Be specific about job titles, company types, and buying signals.
Websites often show sample data in product screenshots or demos (example
tasks, fake customers, placeholder dashboards). Ignore it — describe only what
the company itself sells and who it sells to.
Output ONLY the markdown content — no preamble, no explanation."""

TARGET_PROMPT = """
Here is information about a company:

WEBSITE CONTENT:
{website}

ADDITIONAL DESCRIPTION FROM USER:
{description}

Write a detailed target.md file defining who this company should be targeting.
Include 2-4 verticals based on who would realistically buy from them.

# [Company Name] — Target Market Definition

## Who We Are Looking For
[1-2 paragraphs describing the ideal contact — their role, situation, and pain point]

## Vertical 1 — [Name]
**Company type:** ...
**Stage:** ...
**Job titles to target:** ...
**Buying signal keywords:** ...
**What they are NOT:** ...

## Vertical 2 — [Name]
[same structure]

[Add Vertical 3 and 4 only if genuinely distinct and relevant]

## Disqualifying Signals (Global)
[Bullet list of who to never target]

## Geography
[Based on the company's website and apparent market]

## What a Perfect Lead Looks Like
[2-3 sentences in plain language]
"""


def generate_file(client_type, system, prompt_template,
                  website_content, user_description, label):
    print(dim(f"  Generating {label}..."))
    prompt = prompt_template.format(
        website=website_content or "(no website content available)",
        description=user_description or "(none provided)"
    )
    result = call_llm(client_type, prompt, system)
    print(green(f"  ✓ {label} generated ({len(result)} characters)"))
    return result


# ── OpenOutreach runner ───────────────────────────────────────────────────────
def check_openoutreach():
    result = subprocess.run(["openoutreach", "--help"],
                            capture_output=True, text=True)
    return result.returncode == 0


def install_openoutreach():
    print(dim("  Installing OpenOutreach via uv..."))
    # Install uv if needed
    if subprocess.run(["uv", "--version"], capture_output=True).returncode != 0:
        print(dim("  Installing uv first..."))
        subprocess.run(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            shell=True, check=True
        )
        os.environ["PATH"] = f"{Path.home()}/.local/bin:{os.environ['PATH']}"

    subprocess.check_call(["uv", "tool", "install", "openoutreach"])
    print(green("  ✓ OpenOutreach installed"))


def run_openoutreach_init(product_path, target_path):
    print(dim("  Running OpenOutreach setup wizard..."))
    print(dim("  (You will be asked for BetterContact + email credentials)\n"))
    subprocess.run([
        "openoutreach", "init",
        "--product-docs", str(product_path),
        "--target", str(target_path)
    ])


def run_openoutreach_find(n=10, emails=False):
    cmd = ["openoutreach", "find", str(n)]
    if emails:
        cmd.append("emails")
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _load_env()
    banner()

    parser = argparse.ArgumentParser(
        description="Generate B2B outreach files and find leads from a company URL."
    )
    parser.add_argument("--url", help="Company website URL")
    parser.add_argument("--description", help="Additional description of the company")
    parser.add_argument("--slug", help="Folder name for output files (default: auto)")
    parser.add_argument("--skip-leads", action="store_true",
                        help="Generate files only, skip OpenOutreach")
    parser.add_argument("--find", type=int, default=10,
                        help="Number of leads to find (default: 10)")
    args = parser.parse_args()

    # Need at least one input
    if not args.url and not args.description:
        print(red("Error: provide --url and/or --description\n"))
        print("Examples:")
        print("  python run.py --url https://yourcompany.com")
        print("  python run.py --description 'We sell X to Y, min $15k'")
        sys.exit(1)

    total_steps = 6 if not args.skip_leads else 3

    # ── Step 1: Fetch website ──────────────────────────────────────────────
    step(1, total_steps, "Reading company information")
    website_content = ""
    if args.url:
        website_content = fetch_website(args.url)

    if not website_content and not args.description:
        print(red("Could not fetch website and no description provided. Exiting."))
        sys.exit(1)

    # ── Step 2: Configure LLM ─────────────────────────────────────────────
    step(2, total_steps, "Configuring LLM")
    client_type = get_llm_client()

    # ── Step 3: Generate files ────────────────────────────────────────────
    step(3, total_steps, "Generating outreach files")

    # Determine output folder
    if args.slug:
        slug = args.slug
    elif args.url:
        from urllib.parse import urlparse
        domain = urlparse(args.url).netloc.replace("www.", "")
        slug = domain.split(".")[0].lower()
    else:
        slug = "my-company"

    output_dir = Path(slug)
    output_dir.mkdir(exist_ok=True)
    print(dim(f"  Output folder: {output_dir}/"))

    product_content = generate_file(
        client_type, PRODUCT_SYSTEM, PRODUCT_PROMPT,
        website_content, args.description, "product.md"
    )
    product_path = output_dir / "product.md"
    product_path.write_text(product_content)

    target_content = generate_file(
        client_type, TARGET_SYSTEM, TARGET_PROMPT,
        website_content, args.description, "target.md"
    )
    target_path = output_dir / "target.md"
    target_path.write_text(target_content)

    print(green(f"\n  ✓ Files saved to {output_dir}/"))
    print(dim(f"    {output_dir}/product.md"))
    print(dim(f"    {output_dir}/target.md"))

    if args.skip_leads:
        print(green("\n✓ Done. Files generated successfully."))
        print(dim(f"\nTo find leads later:"))
        print(f"  openoutreach init --product-docs {product_path} --target {target_path}")
        print(f"  openoutreach find 10")
        return

    # ── Step 4: Pre-send quality gate ───────────────────────────────────────
    step(4, total_steps, "Running pre-send quality gate")
    print(dim("  Checking files before OpenOutreach is configured...\n"))
    try:
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location(
            "improver",
            Path(__file__).parent / "improver.py"
        )
        improver = importlib.util.load_from_spec(spec)
        spec.loader.exec_module(improver)
        gate_state = improver.load_state(slug)
        gate_state = improver.loop1_file_gate(slug, gate_state, autonomous=False)
        improver.save_state(slug, gate_state)
    except Exception as e:
        print(yellow(f"  ⚠ Gate skipped: {e}"))

    # ── Step 5: Install + configure OpenOutreach ──────────────────────────────
    step(5, total_steps, "Setting up OpenOutreach")

    if not check_openoutreach():
        install_openoutreach()

    print(yellow("\n  You will need two things for lead finding:"))
    print("  • BetterContact API key  → bettercontact.rocks (40 free credits, no card)")
    print("  • A dedicated Gmail      → gmail.com + an app password\n")
    print(dim("  (The wizard below will ask for these)\n"))

    run_openoutreach_init(product_path, target_path)

    # ── Step 5: Find leads ────────────────────────────────────────────────
    step(5, total_steps, f"Finding first {args.find} leads (free test — no credits spent)")
    print(dim("  This searches for leads matching your ICP without buying emails yet.\n"))

    run_openoutreach_find(args.find, emails=False)

    # ── Done ──────────────────────────────────────────────────────────────
    print(bold("\n================================================"))
    print(green("  ✓ All done!"))
    print(bold("================================================\n"))
    print("Next steps:\n")
    print(f"  {bold('Find leads with verified emails')} (uses BetterContact credits):")
    print(f"    openoutreach find 50 emails > {slug}/leads.csv\n")
    print(f"  {bold('Find + email automatically')}:")
    print(f"    openoutreach run 50\n")
    print(f"  {bold('Check status')}:")
    print(f"    openoutreach status\n")
    print(dim(f"  Your outreach files are in: {output_dir}/"))
    print(dim("  Read SETUP.md for the full guide.\n"))


if __name__ == "__main__":
    main()
