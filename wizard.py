#!/usr/bin/env python3
"""
B2B Outreach Framework — Setup Wizard
======================================
Guides any user through setup step by step.
No technical knowledge required.
No paid APIs required.
"""

import os, sys, json, subprocess, platform, time, textwrap
from pathlib import Path

# ── Colours (with Windows fallback) ──────────────────────────────────────────
if platform.system() == "Windows":
    os.system("color")  # enable ANSI on Windows 10+

def clr(code, t): return f"\033[{code}m{t}\033[0m"
def green(t):  return clr("92", t)
def yellow(t): return clr("93", t)
def red(t):    return clr("91", t)
def bold(t):   return clr("1",  t)
def dim(t):    return clr("2",  t)
def cyan(t):   return clr("96", t)
def blue(t):   return clr("94", t)

def clear():
    os.system("cls" if platform.system() == "Windows" else "clear")

def pause(msg="Press Enter to continue..."):
    input(f"\n{dim(msg)}")

def header(title: str, step: int = 0, total: int = 0):
    clear()
    print(bold(blue("━" * 54)))
    print(bold(blue(f"  B2B Outreach Framework")))
    if step and total:
        print(dim(f"  Step {step} of {total}"))
    print(bold(blue("━" * 54)))
    print(f"\n  {bold(title)}\n")

def wrap(text: str, indent: int = 2):
    for line in textwrap.wrap(text, width=50):
        print(" " * indent + line)

def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    if default:
        prompt = f"{prompt} [{dim(default)}]"
    prompt = f"\n  {cyan('→')} {prompt}: "
    if secret:
        import getpass
        val = getpass.getpass(prompt)
    else:
        val = input(prompt).strip()
    return val or default

def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    val  = input(f"\n  {cyan('→')} {prompt} {dim(hint)}: ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes")

def success(msg: str):
    print(f"\n  {green('✓')} {msg}")

def warn(msg: str):
    print(f"\n  {yellow('⚠')} {msg}")

def fail(msg: str):
    print(f"\n  {red('✗')} {msg}")

def info(msg: str):
    print(f"\n  {dim('ℹ')} {msg}")

def run_cmd(cmd: list, desc: str = "", capture: bool = True) -> tuple:
    if desc:
        print(dim(f"  Running: {desc}..."), end="", flush=True)
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=120
        )
        if desc:
            if result.returncode == 0:
                print(green(" done"))
            else:
                print(red(" failed"))
        return result.returncode == 0, result.stdout, result.stderr
    except FileNotFoundError:
        if desc:
            print(red(" not found"))
        return False, "", "Command not found"
    except subprocess.TimeoutExpired:
        if desc:
            print(red(" timed out"))
        return False, "", "Timed out"

def save_env(key: str, value: str):
    env_file = Path(".env")
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    lines = [l for l in lines if not l.startswith(f"{key}=")]
    lines.append(f"{key}={value}")
    env_file.write_text("\n".join(lines) + "\n")
    # Ensure .gitignore protects it
    gi = Path(".gitignore")
    content = gi.read_text() if gi.exists() else ""
    if ".env" not in content:
        with open(gi, "a") as f:
            f.write("\n# Environment — NEVER share or commit this file\n.env\n")

def load_env():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ═══════════════════════════════════════════════════════
# STEP 0 — WELCOME
# ═══════════════════════════════════════════════════════
def step_welcome():
    header("Welcome!", 0, 0)
    print("  This wizard sets up your B2B lead generation")
    print("  system in a few minutes.\n")
    print("  What you'll need:")
    print(f"    {green('✓')} A company website (or description)")
    print(f"    {green('✓')} A free BetterContact account (finds emails)")
    print(f"    {green('✓')} A dedicated Gmail (sends cold emails)")
    print(f"    {dim('○')} Optionally: a Claude or OpenAI account\n")
    print(f"  {dim('Everything else is handled automatically.')}\n")
    print(f"  {bold('No paid subscriptions required to get started.')}")
    pause()


# ═══════════════════════════════════════════════════════
# STEP 1 — PYTHON CHECK
# ═══════════════════════════════════════════════════════
def step_check_python(total):
    header("Checking your computer", 1, total)
    print("  Checking that Python is installed...\n")

    ok, out, _ = run_cmd([sys.executable, "--version"], "Python")
    if not ok:
        fail("Python is not installed.")
        print("""
  Please install Python first:

  Windows: https://www.python.org/downloads/
           ✓ Tick "Add Python to PATH" during install

  Mac:     https://www.python.org/downloads/
           OR run: brew install python3

  Linux:   sudo apt install python3
        """)
        pause("Press Enter once Python is installed, then re-run this wizard.")
        sys.exit(1)

    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        warn(f"Python {version.major}.{version.minor} found — version 3.9+ recommended.")
        wrap("This may still work, but upgrading Python is recommended.")
    else:
        success(f"Python {version.major}.{version.minor} — perfect")

    # Install pip deps
    print("\n  Installing required packages...\n")
    deps = [
        "anthropic>=0.25.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "fastmcp>=0.1.0"
    ]
    ok, _, err = run_cmd(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade"] + deps,
        "Packages"
    )
    if not ok:
        # Try with break-system-packages
        ok, _, _ = run_cmd(
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--break-system-packages", "--upgrade"] + deps,
            "Packages (system)"
        )
    if ok:
        success("All packages installed")
    else:
        warn("Some packages failed to install — continuing anyway")

    pause()


# ═══════════════════════════════════════════════════════
# STEP 2 — LLM CHOICE (free options first)
# ═══════════════════════════════════════════════════════
def step_choose_llm(total) -> str:
    header("Choose your AI (all free options available)", 2, total)

    print("  The AI reads your company website and writes")
    print("  your outreach files. Choose one:\n")
    print(f"  {bold('1.')} Ollama + Hermes  {green('(Recommended — 100% free, runs on your computer)')}")
    print(f"      No account needed. Works offline.")
    print(f"      Needs: 8GB+ RAM\n")
    print(f"  {bold('2.')} Claude.ai        {green('(Free if you already subscribe)')}")
    print(f"      You generate files in Claude, then")
    print(f"      paste them here. Easiest path.\n")
    print(f"  {bold('3.')} Anthropic API    {yellow('(Free $5 credit — no card needed initially)')}")
    print(f"      console.anthropic.com\n")
    print(f"  {bold('4.')} OpenAI API       {yellow('(Free $5 credit — no card needed initially)')}")
    print(f"      platform.openai.com\n")

    choice = ask("Enter 1, 2, 3, or 4", default="1")

    if choice == "1":
        return _setup_ollama(total)
    elif choice == "2":
        return _setup_claude_manual(total)
    elif choice == "3":
        return _setup_anthropic(total)
    elif choice == "4":
        return _setup_openai(total)
    else:
        warn("Invalid choice — defaulting to Ollama")
        return _setup_ollama(total)


def _setup_ollama(total) -> str:
    header("Setting up Ollama (free, local AI)", 2, total)
    print("  Ollama runs an AI on your own computer.")
    print("  Your data never leaves your machine.\n")

    # Check if already installed
    ok, _, _ = run_cmd(["ollama", "--version"])
    if ok:
        success("Ollama is already installed")
    else:
        system = platform.system()
        print(f"  Installing Ollama for {system}...\n")

        if system == "Darwin":  # Mac
            print(f"  {dim('Option A: Download from https://ollama.ai (click Download)')}")
            print(f"  {dim('Option B: Run this in Terminal:')}")
            print(f"    {cyan('brew install ollama')}\n")
            if confirm("Have you installed Ollama?", default=False):
                ok2, _, _ = run_cmd(["ollama", "--version"])
                if not ok2:
                    fail("Ollama not found. Please install from https://ollama.ai")
                    pause()
                    return _fallback_llm(total)
            else:
                info("Opening https://ollama.ai in your browser...")
                try:
                    import webbrowser
                    webbrowser.open("https://ollama.ai")
                except Exception:
                    pass
                pause("Install Ollama, then press Enter to continue.")

        elif system == "Windows":
            info("Opening https://ollama.ai in your browser...")
            try:
                import webbrowser
                webbrowser.open("https://ollama.ai")
            except Exception:
                pass
            print(f"\n  {dim('Download and run the Ollama installer.')}")
            pause("Once Ollama is installed, press Enter.")

        else:  # Linux
            ok2, _, _ = run_cmd(
                ["bash", "-c", "curl -fsSL https://ollama.ai/install.sh | sh"],
                "Installing Ollama"
            )
            if not ok2:
                warn("Auto-install failed. Visit https://ollama.ai to install manually.")
                pause()

    # Pull model
    print("\n  Downloading the AI model (nous-hermes2, ~4GB)...")
    print(f"  {dim('This only happens once. May take a few minutes.')}\n")

    ok, _, _ = run_cmd(["ollama", "list"])
    # Check if hermes already pulled
    ok2, out, _ = run_cmd(["ollama", "list"])
    if ok2 and "hermes" in out.lower():
        success("Hermes model already downloaded")
    else:
        ok3, _, err = run_cmd(
            ["ollama", "pull", "nous-hermes2"],
            "Downloading nous-hermes2",
            capture=False
        )
        if not ok3:
            warn("Could not download model automatically.")
            print(f"\n  Run this in a terminal: {cyan('ollama pull nous-hermes2')}")
            pause("Press Enter once the model downloads.")

    save_env("OPENAI_API_KEY", "ollama")
    save_env("OPENAI_BASE_URL", "http://localhost:11434/v1")
    save_env("OPENAI_MODEL", "nous-hermes2")
    success("Ollama configured — no API costs, ever")
    pause()
    return "ollama"


def _setup_claude_manual(total) -> str:
    header("Using Claude.ai (manual file generation)", 2, total)
    print("  You'll generate the outreach files inside Claude,")
    print("  then save them here. The rest is automatic.\n")
    print(f"  {bold('How it works:')}")
    print("  1. Open claude.ai in your browser")
    print("  2. Paste this message:")
    print()
    print(f"  {cyan('─' * 50)}")
    print(f"  {cyan('Generate B2B outreach files for:')}")
    print(f"  {cyan('[your company URL]')}")
    print(f"  {cyan('')}")
    print(f"  {cyan('Generate: product.md, target.md, positioning.md,')}")
    print(f"  {cyan('email-sequences.md, linkedin.md, discovery-call.md,')}")
    print(f"  {cyan('proposal-template.md, week-by-week.md')}")
    print(f"  {cyan('─' * 50)}")
    print()
    print("  3. Save each file Claude gives you into a folder")
    print(f"     called your-company-name/")
    print("  4. Come back here and press Enter\n")
    print(f"  {dim('Claude will ask what files to generate — just')}")
    print(f"  {dim('copy the message above and paste your URL.')}")

    save_env("LLM_MODE", "manual")
    pause("Press Enter once you've saved the files from Claude.")
    return "manual"


def _setup_anthropic(total) -> str:
    header("Anthropic API (free $5 credit)", 2, total)
    print("  You get $5 free credit — enough for 150+ campaigns.")
    print("  No card required to start.\n")
    print(f"  {bold('Get your free key:')}")
    print("  1. Go to: console.anthropic.com")
    print("  2. Sign up (email only, no card needed)")
    print("  3. Go to API Keys → Create Key")
    print("  4. Copy the key and paste it below\n")
    print(f"  {dim('Your key is saved locally and never shared.')}")

    try:
        import webbrowser
        webbrowser.open("https://console.anthropic.com")
    except Exception:
        pass

    key = ask("Paste your Anthropic API key", secret=True)
    if not key or len(key) < 10:
        warn("Key looks too short. Try again.")
        key = ask("Paste your Anthropic API key", secret=True)

    save_env("ANTHROPIC_API_KEY", key)
    success("Anthropic API key saved securely")
    pause()
    return "anthropic"


def _setup_openai(total) -> str:
    header("OpenAI API (free $5 credit)", 2, total)
    print("  You get $5 free credit — enough for 150+ campaigns.")
    print("  No card required to start.\n")
    print(f"  {bold('Get your free key:')}")
    print("  1. Go to: platform.openai.com")
    print("  2. Sign up and go to API Keys")
    print("  3. Create a new key and copy it\n")
    print(f"  {dim('Your key is saved locally and never shared.')}")

    try:
        import webbrowser
        webbrowser.open("https://platform.openai.com/api-keys")
    except Exception:
        pass

    key = ask("Paste your OpenAI API key", secret=True)
    if not key or len(key) < 10:
        warn("Key looks too short. Try again.")
        key = ask("Paste your OpenAI API key", secret=True)

    save_env("OPENAI_API_KEY", key)
    save_env("OPENAI_MODEL", "gpt-4o-mini")
    success("OpenAI API key saved securely")
    pause()
    return "openai"


def _fallback_llm(total) -> str:
    warn("Falling back to manual Claude mode.")
    return _setup_claude_manual(total)


# ═══════════════════════════════════════════════════════
# STEP 3 — COMPANY INFO
# ═══════════════════════════════════════════════════════
def step_company_info(llm_mode: str, total) -> str:
    header("Your company", 3, total)

    if llm_mode == "manual":
        print("  What folder did you save the Claude files in?")
        print(f"  {dim('Example: labtronics or acme-corp')}\n")
        slug = ask("Folder name").lower().replace(" ", "-")
        if not Path(slug).exists():
            fail(f"Folder '{slug}/' not found.")
            wrap("Make sure you saved the files Claude gave you into a folder with that name.")
            pause()
            return step_company_info(llm_mode, total)
        save_env("COMPANY_SLUG", slug)
        return slug

    print("  Enter your company website URL.")
    print(f"  {dim('Example: https://labtronicsdesign.co.uk')}\n")
    print(f"  {dim('No website? Just describe your company below.')}\n")

    url  = ask("Company website URL (or leave blank)")
    desc = ""
    if not url:
        print("\n  Describe your company in a sentence or two.")
        print(f"  {dim('Example: We build custom IoT hardware for funded startups, min £15k projects.')}\n")
        desc = ask("Company description")

    if not url and not desc:
        warn("Please provide a URL or description.")
        return step_company_info(llm_mode, total)

    # Derive slug
    slug = ""
    if url:
        from urllib.parse import urlparse
        domain = urlparse(url if "://" in url else f"https://{url}").netloc
        slug = domain.replace("www.", "").split(".")[0].lower()
    if not slug and desc:
        slug = desc.split()[0].lower()[:20]
    slug = slug or "my-company"

    slug = ask("Folder name for your files", default=slug).lower().replace(" ", "-")
    Path(slug).mkdir(exist_ok=True)

    save_env("COMPANY_URL",   url)
    save_env("COMPANY_DESC",  desc)
    save_env("COMPANY_SLUG",  slug)

    success(f"Company info saved — files will go in '{slug}/'")
    pause()
    return slug


# ═══════════════════════════════════════════════════════
# STEP 4 — BETTTERCONTACT (email finder, free)
# ═══════════════════════════════════════════════════════
def step_bettercontact(total):
    header("Email finder — BetterContact (free)", 4, total)
    print("  BetterContact finds verified email addresses")
    print("  for your prospects. Free to start — 40 emails,")
    print("  no credit card required.\n")
    print(f"  {bold('Get your free account:')}")
    print("  1. Go to: bettercontact.rocks")
    print("  2. Sign up — email only, no card")
    print("  3. Copy your API key from the dashboard")
    print("  4. Paste it below\n")
    print(f"  {dim('This key is saved on your computer only.')}")
    print(f"  {dim('It is never sent to GitHub or shared anywhere.')}")

    try:
        import webbrowser
        webbrowser.open("https://bettercontact.rocks")
    except Exception:
        pass

    key = ask("Paste your BetterContact API key", secret=True)
    if not key or len(key) < 5:
        warn("Key looks too short — double check the dashboard.")
        key = ask("Paste your BetterContact API key", secret=True)

    save_env("BETTERCONTACT_API_KEY", key)
    success("BetterContact key saved securely")

    info("You have 40 free credits. Each credit = one verified email address.")
    info("Searching for people is always free — only buying an email costs a credit.")
    pause()


# ═══════════════════════════════════════════════════════
# STEP 5 — GMAIL SETUP (secure)
# ═══════════════════════════════════════════════════════
def step_gmail(total):
    header("Sending Gmail setup", 5, total)
    print("  OpenOutreach sends cold emails from your Gmail.")
    print("  We use an App Password — NOT your real password.")
    print("  This is safer: you can revoke it anytime.\n")
    print(f"  {bold('Important: use a DEDICATED Gmail for outreach.')}")
    wrap("Using your main inbox risks it being marked as spam. Create a new Gmail account just for this.")
    print()

    ok = confirm("Do you have a dedicated outreach Gmail ready?", default=False)
    if not ok:
        info("Opening Gmail to create a new account...")
        try:
            import webbrowser
            webbrowser.open("https://accounts.google.com/signup")
        except Exception:
            pass
        print(f"\n  {dim('Create a Gmail like: yourname.outreach@gmail.com')}")
        pause("Press Enter once you have a dedicated Gmail ready.")

    gmail = ask("Your outreach Gmail address")
    if "@" not in gmail:
        gmail = gmail + "@gmail.com"

    print(f"\n  {bold('Now create an App Password:')}")
    print("  1. Go to: myaccount.google.com/security")
    print("  2. Turn on 2-Step Verification (if not already on)")
    print("  3. Search for 'App Passwords' in the search bar")
    print("  4. Create a new one — name it 'Outreach'")
    print("  5. Copy the 16-character password it gives you\n")
    print(f"  {dim('This is NOT your Gmail login password.')}")
    print(f"  {dim('It looks like: abcd efgh ijkl mnop')}\n")

    try:
        import webbrowser
        webbrowser.open("https://myaccount.google.com/apppasswords")
    except Exception:
        pass

    app_pass = ask("Paste your 16-character App Password", secret=True)
    # Remove spaces (Google shows it with spaces)
    app_pass = app_pass.replace(" ", "")

    if len(app_pass) not in (16, 17):
        warn(f"App Password should be 16 characters — you entered {len(app_pass)}.")
        warn("Remove any spaces. Check you copied the right thing.")
        app_pass = ask("Try again — paste your App Password", secret=True)
        app_pass = app_pass.replace(" ", "")

    save_env("GMAIL_ADDRESS",      gmail)
    save_env("GMAIL_APP_PASSWORD", app_pass)
    success("Gmail configured securely")
    info("Your real Gmail password is never used or stored.")
    pause()


# ═══════════════════════════════════════════════════════
# STEP 6 — INSTALL OPENOUTREACH
# ═══════════════════════════════════════════════════════
def step_install_openoutreach(total):
    header("Installing OpenOutreach", 6, total)
    print("  OpenOutreach is the tool that finds leads")
    print("  and sends your cold emails.\n")
    print("  Installing now — this may take a minute...\n")

    # Check uv
    ok, _, _ = run_cmd(["uv", "--version"])
    if not ok:
        print(dim("  Installing uv package manager..."))
        system = platform.system()
        if system == "Windows":
            ok2, _, _ = run_cmd(
                ["powershell", "-Command",
                 "irm https://astral.sh/uv/install.ps1 | iex"],
                "Installing uv"
            )
        else:
            ok2, _, _ = run_cmd(
                ["bash", "-c",
                 "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                "Installing uv"
            )
        if ok2:
            # Add to PATH for this session
            local_bin = str(Path.home() / ".local" / "bin")
            os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH","")
        else:
            warn("Could not install uv automatically.")
            print(f"\n  Please run this in a terminal:")
            print(f"  {cyan('curl -LsSf https://astral.sh/uv/install.sh | sh')}")
            pause("Press Enter once uv is installed.")

    # Install OpenOutreach
    ok, _, err = run_cmd(["uv", "tool", "install", "openoutreach"], "OpenOutreach")
    if not ok:
        # Try pip fallback
        ok2, _, _ = run_cmd(
            [sys.executable, "-m", "pip", "install",
             "openoutreach", "--break-system-packages", "-q"],
            "OpenOutreach (pip)"
        )
        if not ok2:
            fail("Could not install OpenOutreach automatically.")
            print(f"\n  Run this in a terminal: {cyan('uv tool install openoutreach')}")
            pause("Press Enter once installed.")
        else:
            success("OpenOutreach installed via pip")
    else:
        success("OpenOutreach installed")

    pause()


# ═══════════════════════════════════════════════════════
# STEP 7 — GENERATE FILES (if not manual mode)
# ═══════════════════════════════════════════════════════
def step_generate_files(slug: str, llm_mode: str, total):
    if llm_mode == "manual":
        return  # Files already saved by user

    header("Generating your outreach files", 7, total)
    load_env()

    url  = os.getenv("COMPANY_URL", "")
    desc = os.getenv("COMPANY_DESC", "")

    print(f"  Analysing your company and writing all files...")
    print(f"  {dim('This takes about 30–60 seconds.')}\n")

    # Start Ollama if needed
    if llm_mode == "ollama":
        ok, _, _ = run_cmd(["ollama", "list"])
        if not ok:
            run_cmd(["ollama", "serve"], "Starting Ollama")
            time.sleep(3)

    cmd = [sys.executable, "run.py", "--skip-leads", "--slug", slug]
    if url:
        cmd += ["--url", url]
    if desc:
        cmd += ["--description", desc]

    ok, out, err = run_cmd(cmd, "Generating files", capture=False)
    if ok:
        success("All outreach files generated")
    else:
        warn("File generation had issues — check files in " + slug + "/")

    pause()


# ═══════════════════════════════════════════════════════
# STEP 8 — CONFIGURE OPENOUTREACH
# ═══════════════════════════════════════════════════════
def step_configure_openoutreach(slug: str, total):
    header("Connecting everything together", 8, total)
    load_env()

    product = Path(slug) / "product.md"
    target  = Path(slug) / "target.md"

    if not product.exists() or not target.exists():
        fail(f"Files not found in '{slug}/'")
        wrap("Make sure you saved product.md and target.md from Claude into that folder.")
        pause()
        return

    print("  Setting up OpenOutreach with your files...\n")
    print(f"  {dim('This connects your company description and target')}")
    print(f"  {dim('market to the lead-finding system.')}\n")

    # Build openoutreach env vars
    llm_key  = (os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("OPENAI_API_KEY") or "ollama")
    bc_key   = os.getenv("BETTERCONTACT_API_KEY", "")
    gmail    = os.getenv("GMAIL_ADDRESS", "")
    app_pass = os.getenv("GMAIL_APP_PASSWORD", "")

    env = {
        **os.environ,
        "OPENOUTFIND_BETTERCONTACT_API_KEY": bc_key,
        "OUTSEND_SMTP_HOST":     "smtp.gmail.com",
        "OUTSEND_SMTP_PORT":     "587",
        "OUTSEND_SMTP_USER":     gmail,
        "OUTSEND_SMTP_PASSWORD": app_pass,
        "OUTSEND_FROM_ADDRESS":  gmail,
    }

    if os.getenv("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
    elif os.getenv("OPENAI_API_KEY"):
        env["OPENAI_API_KEY"]    = os.getenv("OPENAI_API_KEY")
        env["OPENAI_BASE_URL"]   = os.getenv("OPENAI_BASE_URL","")

    result = subprocess.run(
        ["openoutreach", "init",
         "--product-docs", str(product),
         "--target", str(target)],
        env=env,
        timeout=120
    )

    if result.returncode == 0:
        success("OpenOutreach configured")
    else:
        warn("OpenOutreach setup may need manual input.")
        info("If prompted, paste your BetterContact key and Gmail details.")
        ok = confirm("Did the setup complete?", default=True)

    pause()


# ═══════════════════════════════════════════════════════
# STEP 9 — FIND FIRST LEADS
# ═══════════════════════════════════════════════════════
def step_find_leads(slug: str, total):
    header("Finding your first leads", 9, total)
    print("  Finding 10 leads matching your ICP.")
    print(f"  {dim('This is a free test — no email credits used.')}\n")

    result = subprocess.run(
        ["openoutreach", "find", "10"],
        timeout=120
    )

    if result.returncode == 0:
        success("Lead search complete")
        print()
        print(f"  {bold('Next steps:')}")
        print()
        print(f"  {cyan('Find 50 leads with emails')} (uses BetterContact credits):")
        print(f"    openoutreach find 50 emails > {slug}/leads.csv")
        print()
        print(f"  {cyan('Find + email automatically')}:")
        print(f"    openoutreach run 50")
        print()
        print(f"  {cyan('Run quality + improvement loop')}:")
        print(f"    python improver.py --slug {slug} --mode watch")
        print()
        print(f"  {cyan('Fully autonomous mode')} (no prompts):")
        print(f"    python improver.py --slug {slug} --mode auto")
    else:
        warn("Lead search encountered an issue.")
        info("Try running: openoutreach status")

    pause()


# ═══════════════════════════════════════════════════════
# STEP 10 — DONE
# ═══════════════════════════════════════════════════════
def step_done(slug: str):
    header("You're all set! 🎉", 0, 0)
    print(f"  Your campaign is ready: {bold(cyan(slug + '/'))}\n")
    print(f"  {bold('Files generated:')}")
    output_dir = Path(slug)
    for f in sorted(output_dir.glob("*.md")):
        print(f"    {green('✓')} {f.name}")
    print()
    print(f"  {bold('Security reminder:')}")
    print(f"  {dim('Your .env file contains your credentials.')}")
    print(f"  {dim('It is in .gitignore — never commit it to GitHub.')}")
    print(f"  {dim('Never share it with anyone.')}")
    print()
    print(f"  {bold('Run commands (copy these):')}")
    print()
    print(f"  Find leads (free test):     {cyan('openoutreach find 10')}")
    print(f"  Find + buy emails:          {cyan(f'openoutreach find 50 emails > {slug}/leads.csv')}")
    print(f"  Find + email automatically: {cyan('openoutreach run 50')}")
    print(f"  Self-improving watch mode:  {cyan(f'python improver.py --slug {slug} --mode watch')}")
    print(f"  Fully autonomous:           {cyan(f'python improver.py --slug {slug} --mode auto')}")
    print()
    print(f"  {dim('Read SETUP.md for detailed guidance.')}")
    print()
    input("  Press Enter to close.\n")



# ═══════════════════════════════════════════════════════
# STEP 6b — CONNECT TO LLM APP (MCP)
# ═══════════════════════════════════════════════════════

def step_connect_llm_app(total):
    header("Connect to your AI app", "6b", total)
    print("  Once connected, open your app and type:")
    print("  Generate leads for https://yourcompany.com")
    print("  No terminal needed after this.\n")

    want = confirm("Connect an AI desktop app now?", default=True)
    if not want:
        info("Skipped. Re-run wizard anytime to add this.")
        pause()
        return

    apps = [
        ("Claude Desktop", "claude.ai/download"),
        ("Cursor",         "cursor.sh"),
        ("Windsurf",       "windsurf.com"),
        ("VS Code",        "with Continue extension"),
        ("Zed",            "zed.dev"),
    ]
    print()
    for i, (name, url) in enumerate(apps, 1):
        print(f"  {bold(str(i))}. {name}  {dim(url)}")
    print(f"  {bold('6')}. Skip\n")

    choice = ask("Enter 1-6", default="1")
    if choice not in ("1","2","3","4","5"):
        pause()
        return

    server_path = str(Path(__file__).parent.resolve() / "mcp_server.py")
    load_env()
    env_key = "ANTHROPIC_API_KEY" if os.getenv("ANTHROPIC_API_KEY") else "OPENAI_API_KEY"
    env_val = os.getenv(env_key, "ollama")
    system  = platform.system()

    app_name = apps[int(choice)-1][0]

    # Config paths per app per OS
    if choice == "1":
        paths = {
            "Darwin":  Path.home()/"Library/Application Support/Claude/claude_desktop_config.json",
            "Windows": Path(os.environ.get("APPDATA",""))/"Claude/claude_desktop_config.json",
            "Linux":   Path.home()/".config/Claude/claude_desktop_config.json",
        }
        config_path = paths.get(system, paths["Linux"])
        config = {"mcpServers": {"b2b-outreach-framework": {
            "command": sys.executable, "args": [server_path], "env": {env_key: env_val}
        }}}
        merge_key = "mcpServers"

    elif choice == "2":
        config_path = Path.home()/".cursor/mcp.json"
        config = {"mcpServers": {"b2b-outreach-framework": {
            "command": sys.executable, "args": [server_path], "env": {env_key: env_val}
        }}}
        merge_key = "mcpServers"

    elif choice == "3":
        config_path = Path.home()/".codeium/windsurf/mcp_config.json"
        config = {"mcpServers": {"b2b-outreach-framework": {
            "command": sys.executable, "args": [server_path], "env": {env_key: env_val}
        }}}
        merge_key = "mcpServers"

    elif choice == "4":
        config_path = Path.home()/".continue/config.json"
        config = {"mcpServers": [{"name": "b2b-outreach-framework",
            "command": sys.executable, "args": [server_path], "env": {env_key: env_val}
        }]}
        merge_key = "mcpServers"

    else:  # Zed
        paths = {
            "Darwin":  Path.home()/"Library/Application Support/Zed/settings.json",
            "Windows": Path(os.environ.get("APPDATA",""))/"Zed/settings.json",
            "Linux":   Path.home()/".config/zed/settings.json",
        }
        config_path = paths.get(system, paths["Linux"])
        config = {"context_servers": {"b2b-outreach-framework": {
            "command": {"path": sys.executable, "args": [server_path], "env": {env_key: env_val}}
        }}}
        merge_key = "context_servers"

    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text())
            if choice == "4":
                existing.setdefault("mcpServers", [])
                existing["mcpServers"] = [
                    s for s in existing["mcpServers"]
                    if s.get("name") != "b2b-outreach-framework"
                ]
                existing["mcpServers"].extend(config["mcpServers"])
            else:
                existing.setdefault(merge_key, {}).update(config.get(merge_key, {}))
            config_path.write_text(json.dumps(existing, indent=2))
            success("Added to existing " + app_name + " config")
        except Exception:
            backup = config_path.with_suffix(".bak.json")
            config_path.rename(backup)
            config_path.write_text(json.dumps(config, indent=2))
            success("Config written (backup saved as " + backup.name + ")")
    else:
        config_path.write_text(json.dumps(config, indent=2))
        success(app_name + " config written")

    print()
    print("  " + dim("Saved to: " + str(config_path)))
    print()
    print("  " + bold(yellow("Now restart " + app_name + ".")))
    print()
    print("  Then open it and say:")
    print("  " + cyan("Generate leads for https://yourcompany.com"))
    pause()


def main():
    TOTAL_STEPS = 10

    try:
        step_welcome()
        step_check_python(TOTAL_STEPS)
        llm_mode = step_choose_llm(TOTAL_STEPS)
        slug     = step_company_info(llm_mode, TOTAL_STEPS)
        step_bettercontact(TOTAL_STEPS)
        step_gmail(TOTAL_STEPS)
        step_install_openoutreach(TOTAL_STEPS)
        step_connect_llm_app(TOTAL_STEPS)
        step_generate_files(slug, llm_mode, TOTAL_STEPS)
        step_configure_openoutreach(slug, TOTAL_STEPS)
        step_find_leads(slug, TOTAL_STEPS)
        step_done(slug)

    except KeyboardInterrupt:
        print(yellow("\n\n  Wizard cancelled. Run again anytime: python wizard.py"))
        sys.exit(0)
    except Exception as e:
        print(red(f"\n\n  Something went wrong: {e}"))
        print(dim("  Run python wizard.py again to retry."))
        sys.exit(1)


if __name__ == "__main__":
    main()
