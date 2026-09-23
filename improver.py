#!/usr/bin/env python3
"""
B2B Outreach Framework — Self-Improving Quality Loop
=====================================================
Two modes:

  GATE mode   — runs before any emails send. Blocks until files pass
                quality check. Shows every diff and asks approval once.
                Called automatically by run.py.

  WATCH mode  — runs on a schedule after sending. Monitors reply rates,
                rewrites what isn't working, shows diffs, asks approval,
                then carries on by itself. No user interaction needed
                beyond approving changes.

  AUTO mode   — fully autonomous. No approval prompts. Just runs,
                improves, logs everything, keeps going.

Usage:
  python improver.py --slug acme --mode gate       # pre-send quality gate
  python improver.py --slug acme --mode watch      # scheduled loop (every 24h)
  python improver.py --slug acme --mode auto       # fully autonomous
  python improver.py --slug acme --mode watch --interval 12  # every 12h
"""

import os
import sys
import json
import time
import imaplib
import email as email_lib
import argparse
import csv
import difflib
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


# ── Colours ───────────────────────────────────────────────────────────────────
def green(t):  return f"\033[92m{t}\033[0m"
def yellow(t): return f"\033[93m{t}\033[0m"
def red(t):    return f"\033[91m{t}\033[0m"
def bold(t):   return f"\033[1m{t}\033[0m"
def dim(t):    return f"\033[2m{t}\033[0m"
def cyan(t):   return f"\033[96m{t}\033[0m"
def blue(t):   return f"\033[94m{t}\033[0m"


# ── Env / State ───────────────────────────────────────────────────────────────
def load_env():
    for path in [Path(".env"), Path.home() / ".openoutreach" / ".env"]:
        if path.exists():
            for line in path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

def load_state(slug: str) -> dict:
    f = Path(slug) / ".loop_state.json"
    if f.exists():
        return json.loads(f.read_text())
    return {
        "slug": slug, "loop_count": 0,
        "file_quality_passed": False, "file_rewrites": 0,
        "leads_scored": 0, "leads_rejected": 0, "target_rewrites": 0,
        "emails_sent": 0, "replies_total": 0,
        "replies_interested": 0, "replies_wrong_person": 0,
        "reply_rate": 0.0, "positive_rate": 0.0,
        "email_rewrites": 0, "last_run": None,
        "improvements": [], "pending_approval": []
    }

def save_state(slug: str, state: dict):
    state["last_run"] = datetime.now().isoformat()
    state["loop_count"] = state.get("loop_count", 0) + 1
    (Path(slug) / ".loop_state.json").write_text(json.dumps(state, indent=2))


# ── Diff display ──────────────────────────────────────────────────────────────
def show_diff(label: str, before: str, after: str):
    """Show a coloured diff between two versions of a file."""
    print(f"\n{bold(cyan('━━━ CHANGE: ' + label + ' ━━━'))}")
    diff = list(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        n=2
    ))
    if not diff:
        print(dim("  (no changes)"))
        return
    for line in diff[:60]:  # cap at 60 lines for readability
        if line.startswith("+") and not line.startswith("+++"):
            print(green(f"  {line.rstrip()}"))
        elif line.startswith("-") and not line.startswith("---"):
            print(red(f"  {line.rstrip()}"))
        elif line.startswith("@@"):
            print(blue(f"  {line.rstrip()}"))
        else:
            print(dim(f"  {line.rstrip()}"))
    if len(diff) > 60:
        print(dim(f"  ... {len(diff) - 60} more lines"))


def ask_approval(label: str, autonomous: bool) -> bool:
    """Ask for approval or auto-approve in autonomous mode."""
    if autonomous:
        print(green(f"  ✓ Auto-approved: {label}"))
        return True
    print(f"\n{bold(yellow('❓ Approve this change?'))} [{label}]")
    print(dim("   y = apply and continue | n = skip | q = quit"))
    try:
        answer = input("   → ").strip().lower()
        if answer == "q":
            print(yellow("  Stopped by user."))
            sys.exit(0)
        return answer in ("y", "yes", "")
    except (EOFError, KeyboardInterrupt):
        return True  # non-interactive environment — auto-approve


def apply_change(filepath: Path, new_content: str, label: str,
                 state: dict, loop_name: str, autonomous: bool) -> bool:
    """Show diff, ask approval, apply if approved. Returns True if applied."""
    before = filepath.read_text() if filepath.exists() else ""
    show_diff(label, before, new_content)

    if ask_approval(label, autonomous):
        filepath.write_text(new_content)
        state.setdefault("improvements", []).append({
            "timestamp": datetime.now().isoformat(),
            "loop": loop_name,
            "file": filepath.name,
            "label": label,
            "before_preview": before[:150],
            "after_preview": new_content[:150]
        })
        print(green(f"  ✓ Applied: {label}"))
        return True
    else:
        print(dim(f"  Skipped: {label}"))
        return False


# ── LLM caller ────────────────────────────────────────────────────────────────
def call_llm(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    load_env()
    import requests

    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system or "You are a B2B marketing expert.",
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

    if os.getenv("OPENAI_API_KEY"):
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        resp = requests.post(
            f"{base}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system or "You are a B2B marketing expert."},
                    {"role": "user",   "content": prompt}
                ],
                "max_tokens": max_tokens
            },
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json"
            },
            timeout=120
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    raise ValueError("No LLM configured. Run setup.sh first.")


def parse_json_response(response: str) -> dict:
    clean = response.strip().strip("```json").strip("```").strip()
    return json.loads(clean)


# ══════════════════════════════════════════════════════════════════════════════
# LOOP 1 — FILE QUALITY GATE (runs before any emails send)
# ══════════════════════════════════════════════════════════════════════════════
QUALITY_PROMPT = """
Score this {file_type} file for B2B outreach quality. Be strict.

CONTENT:
{content}

Score each criterion 1 (pass) or 0 (fail):

product.md criteria:
1. Core offering is clear in the first paragraph (not vague)
2. Deliverables are specific items, not generic phrases
3. At least one concrete proof point (client name, stat, or outcome)
4. Differentiators are specific (no "world-class" or "innovative")
5. Minimum deal size or target client size is mentioned
6. Clear statement of who they do NOT work with

target.md criteria:
1. At least 2 clearly distinct verticals
2. Each vertical has specific job titles (not "decision maker")
3. Each vertical has real searchable keywords (not generic)
4. Disqualifiers are specific and actionable
5. Geography is clearly stated
6. "Perfect lead" description is a real person, not abstract

Output ONLY valid JSON:
{{
  "score": <0-6>,
  "passed": <true if score >= 5>,
  "failures": ["list of specific issues"],
  "fix_instructions": "precise instructions to fix failures, or empty if passed"
}}
"""

REWRITE_PROMPT = """
Rewrite this {file_type} to fix these specific issues.
Only fix what's listed. Keep everything else exactly the same.

ISSUES TO FIX:
{issues}

CURRENT FILE:
{content}

Output ONLY the corrected markdown. No preamble.
"""

def loop1_file_gate(slug: str, state: dict,
                    autonomous: bool, max_iter: int = 3) -> bool:
    """
    Quality gate — blocks until files pass or max iterations reached.
    Returns True if gate passed, False if failed after max iterations.
    """
    print(f"\n{bold('━━━ LOOP 1: File Quality Gate ━━━')}")
    print(dim("  Checking files before any emails are sent...\n"))

    output_dir = Path(slug)
    all_passed = True

    for filename in ["product.md", "target.md"]:
        filepath = output_dir / filename
        if not filepath.exists():
            print(yellow(f"  ⚠ {filename} not found — skipping"))
            continue

        file_type = filename.replace(".md", "")
        passed = False

        for i in range(max_iter):
            content = filepath.read_text()
            print(dim(f"  Checking {filename} (attempt {i+1}/{max_iter})..."))

            try:
                result = parse_json_response(call_llm(
                    QUALITY_PROMPT.format(
                        file_type=file_type,
                        content=content[:3000]
                    ),
                    system="B2B outreach quality reviewer. Output only JSON.",
                    max_tokens=400
                ))
            except Exception as e:
                print(yellow(f"  ⚠ Quality check failed: {e}"))
                break

            score   = result.get("score", 0)
            passed  = result.get("passed", False)
            failures = result.get("failures", [])
            fix_instructions = result.get("fix_instructions", "")

            status = green("✓ PASS") if passed else red("✗ FAIL")
            print(f"  {filename}: {score}/6 — {status}")

            if passed:
                state["file_quality_passed"] = True
                break

            if not failures or i == max_iter - 1:
                all_passed = False
                break

            # Generate improved version
            print(dim(f"  Issues: {'; '.join(failures[:3])}"))
            print(dim(f"  Generating fix..."))

            improved = call_llm(
                REWRITE_PROMPT.format(
                    file_type=file_type,
                    issues="\n".join(f"- {f}" for f in failures),
                    content=content
                ),
                system="B2B marketing expert. Fix only what's listed. Output only markdown."
            )

            applied = apply_change(
                filepath, improved,
                f"Fix {filename} (score {score}/6 → target 5/6)",
                state, "Loop 1 — File Quality", autonomous
            )

            if not applied:
                break

            state["file_rewrites"] = state.get("file_rewrites", 0) + 1

        if not passed:
            all_passed = False

    if all_passed:
        print(green("\n  ✓ All files passed quality gate — safe to send"))
    else:
        print(yellow("\n  ⚠ Some files did not reach quality threshold"))
        print(dim("  Emails will still send — review files manually if needed"))

    return all_passed


# ══════════════════════════════════════════════════════════════════════════════
# LOOP 2 — LEAD SCORING (runs after find, before send)
# ══════════════════════════════════════════════════════════════════════════════
SCORE_PROMPT = """
Score this B2B lead against the ICP. Output ONLY valid JSON.

ICP summary:
{icp_summary}

Lead:
- Name: {name}
- Title: {title}
- Company: {company}
- Reason flagged: {reason}

Score 1-10:
  9-10 = perfect fit
  7-8  = strong fit
  5-6  = borderline
  1-4  = reject

Output ONLY: {{"score": <1-10>, "verdict": "keep|borderline|reject", "why": "<one sentence>"}}
"""

ICP_TIGHTEN_PROMPT = """
Too many leads are being rejected. Tighten the ICP to prevent these misfires.

Rejected leads (sample):
{rejected}

Rejection reasons:
{reasons}

Current target.md:
{target_md}

Rewrite target.md to add specificity that would exclude these misfires.
Only add to existing verticals — do not remove anything.
Output ONLY the improved target.md markdown.
"""

def loop2_lead_scoring(slug: str, state: dict,
                       autonomous: bool, threshold: int = 6) -> dict:
    print(f"\n{bold('━━━ LOOP 2: Lead Scoring ━━━')}")

    output_dir = Path(slug)
    csv_files  = list(output_dir.glob("leads*.csv"))

    if not csv_files:
        print(yellow("  ⚠ No leads CSV found. Run: openoutreach find 50 emails"))
        return state

    target_path = output_dir / "target.md"
    target_md   = target_path.read_text() if target_path.exists() else ""
    # Use first 1000 chars as ICP summary for scoring prompts
    icp_summary = target_md[:1000]

    leads_file = sorted(csv_files)[-1]  # most recent
    print(dim(f"  Scoring leads from {leads_file.name}..."))

    with open(leads_file, newline="", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    if not leads:
        print(yellow("  ⚠ CSV is empty"))
        return state

    kept = []
    rejected = []
    rejection_reasons = []
    sample_size = min(len(leads), 50)  # score up to 50 to manage cost

    for i, lead in enumerate(leads[:sample_size]):
        name    = f"{lead.get('first_name','')} {lead.get('last_name','')}".strip()
        title   = lead.get("title", "?")
        company = lead.get("company", "?")
        reason  = lead.get("reason", "")

        print(dim(f"  Scoring {i+1}/{sample_size}: {name} @ {company}..."), end="\r")

        try:
            result = parse_json_response(call_llm(
                SCORE_PROMPT.format(
                    icp_summary=icp_summary,
                    name=name, title=title,
                    company=company, reason=reason
                ),
                system="B2B lead scorer. Output only JSON.",
                max_tokens=100
            ))
            score   = result.get("score", 5)
            verdict = result.get("verdict", "borderline")
            why     = result.get("why", "")
        except Exception:
            score = 5; verdict = "borderline"; why = "scoring error"

        lead["_score"]   = score
        lead["_verdict"] = verdict
        lead["_why"]     = why

        if score >= threshold:
            kept.append(lead)
        else:
            rejected.append(lead)
            rejection_reasons.append(
                f"{title} @ {company} (score {score}): {why}"
            )

    print()  # clear \r line

    total      = len(kept) + len(rejected)
    reject_pct = (len(rejected) / total * 100) if total > 0 else 0

    print(f"  Scored {total} leads")
    print(green(f"  ✓ Kept: {len(kept)} ({100 - reject_pct:.0f}%)"))
    if rejected:
        print(yellow(f"  ✗ Rejected: {len(rejected)} ({reject_pct:.0f}%)"))

    state["leads_scored"]   = state.get("leads_scored", 0) + total
    state["leads_rejected"] = state.get("leads_rejected", 0) + len(rejected)

    # Save quality leads
    if kept:
        out_file = output_dir / "leads_quality.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = list(leads[0].keys()) + ["_score", "_verdict", "_why"]
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(kept)
        print(green(f"  ✓ Saved {len(kept)} quality leads → leads_quality.csv"))
        print(dim(f"    Use this file with: openoutreach send (after importing)"))

    # Tighten ICP if >30% rejected
    if reject_pct > 30 and rejected and target_path.exists():
        print(yellow(f"\n  {reject_pct:.0f}% rejection rate — tightening ICP..."))

        improved = call_llm(
            ICP_TIGHTEN_PROMPT.format(
                rejected="\n".join(
                    f"- {l.get('first_name','')} {l.get('last_name','')}, "
                    f"{l.get('title','')}, {l.get('company','')}"
                    for l in rejected[:8]
                ),
                reasons="\n".join(f"- {r}" for r in rejection_reasons[:8]),
                target_md=target_md
            ),
            system="B2B ICP specialist. Tighten to reduce misfires. Output only markdown."
        )

        applied = apply_change(
            target_path, improved,
            f"Tighten ICP ({reject_pct:.0f}% leads rejected)",
            state, "Loop 2 — Lead Scoring", autonomous
        )
        if applied:
            state["target_rewrites"] = state.get("target_rewrites", 0) + 1

    return state


# ══════════════════════════════════════════════════════════════════════════════
# LOOP 3 — REPLY MONITOR (runs on schedule, autonomous)
# ══════════════════════════════════════════════════════════════════════════════
CLASSIFY_PROMPT = """
Classify this cold outreach reply. Output ONLY valid JSON.

Reply:
{body}

Output ONLY:
{{
  "classification": "interested|not_now|wrong_person|unsubscribe|bounce|other",
  "sentiment": "positive|neutral|negative",
  "summary": "<one sentence>",
  "action": "<what to do next, one sentence>"
}}
"""

EMAIL_FIX_PROMPT = """
The current cold email sequence has a {reply_rate:.1f}% reply rate (target: 5%+).
Rewrite it to improve performance based on the signals below.

Current sequence:
{sequence}

Signals:
- Reply rate: {reply_rate:.1f}%
- Wrong person rate: {wrong_pct:.0f}%
- Patterns from replies: {patterns}

Rules (non-negotiable):
- Email 1: ≤120 words, personalised hook, one soft CTA
- Email 2: ≤80 words, adds one piece of value, one CTA
- Email 3 (breakup): ≤60 words, leaves door open, warm sign-off

Output ONLY the improved email-sequences.md content.
"""

ICP_REFINE_FROM_REPLIES_PROMPT = """
{wrong_pct:.0f}% of replies said we contacted the wrong person.
Refine target.md to prevent this.

Wrong-person replies:
{wrong_people}

Current target.md:
{target_md}

Add specificity to exclude these profiles. Do not remove existing verticals.
Output ONLY the improved target.md content.
"""

def _get_gmail_creds() -> tuple:
    load_env()
    # Try ~/.openoutreach config first
    oo_config = Path.home() / ".openoutreach" / "config.json"
    if oo_config.exists():
        try:
            cfg = json.loads(oo_config.read_text())
            return cfg.get("email_address",""), cfg.get("email_password","")
        except Exception:
            pass
    return os.getenv("GMAIL_ADDRESS",""), os.getenv("GMAIL_APP_PASSWORD","")

def loop3_reply_monitor(slug: str, state: dict, autonomous: bool) -> dict:
    print(f"\n{bold('━━━ LOOP 3: Reply Monitor ━━━')}")

    gmail_user, gmail_pass = _get_gmail_creds()
    if not gmail_user or not gmail_pass:
        print(yellow("  ⚠ Gmail credentials not found."))
        print(dim("  Add GMAIL_ADDRESS and GMAIL_APP_PASSWORD to .env"))
        return state

    print(dim(f"  Connecting to Gmail ({gmail_user})..."))

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_pass)
        mail.select("inbox")
        since = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
        _, nums = mail.search(None, f'(SINCE {since} NOT FROM "{gmail_user}")')
        msg_nums = nums[0].split()[-30:]  # last 30 emails
    except Exception as e:
        print(yellow(f"  ⚠ Could not connect to Gmail: {e}"))
        return state

    classified = []
    print(dim(f"  Classifying {len(msg_nums)} emails..."))

    for num in msg_nums:
        try:
            _, data = mail.fetch(num, "(RFC822)")
            msg = email_lib.message_from_bytes(data[0][1])
            sender  = msg.get("From", "")
            subject = msg.get("Subject", "")
            body    = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8","ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8","ignore")

            if not body.strip():
                continue

            result = parse_json_response(call_llm(
                CLASSIFY_PROMPT.format(body=body[:400]),
                system="Sales email classifier. Output only JSON.",
                max_tokens=150
            ))
            classified.append({
                "sender": sender, "subject": subject,
                **result
            })
        except Exception:
            continue

    mail.logout()

    if not classified:
        print(dim("  No new replies in the last 7 days."))
        return state

    # Tally
    counts = {}
    for r in classified:
        c = r.get("classification","other")
        counts[c] = counts.get(c, 0) + 1

    icons = {"interested":"🟢","not_now":"🟡","wrong_person":"🔴",
             "unsubscribe":"⛔","bounce":"❌","other":"⚪"}
    print(f"\n  {len(classified)} replies classified:")
    for cls, cnt in counts.items():
        print(f"    {icons.get(cls,'⚪')} {cls}: {cnt}")

    # Update metrics
    emails_sent  = max(state.get("emails_sent", 1), 1)
    interested   = counts.get("interested", 0)
    wrong_person = counts.get("wrong_person", 0)
    total        = len(classified)

    state["replies_total"]       = state.get("replies_total",0) + total
    state["replies_interested"]  = state.get("replies_interested",0) + interested
    state["replies_wrong_person"]= state.get("replies_wrong_person",0) + wrong_person
    state["reply_rate"]          = state["replies_total"] / emails_sent * 100
    state["positive_rate"]       = state["replies_interested"] / emails_sent * 100

    reply_rate = state["reply_rate"]
    wrong_pct  = (wrong_person / total * 100) if total > 0 else 0

    print(f"\n  Reply rate:    {reply_rate:.1f}%  (target ≥5%)")
    print(f"  Positive rate: {state['positive_rate']:.1f}%")

    # Save log
    log_file = Path(slug) / "replies_log.json"
    existing = json.loads(log_file.read_text()) if log_file.exists() else []
    existing.extend(classified)
    log_file.write_text(json.dumps(existing, indent=2))

    output_dir = Path(slug)

    # Rewrite emails if reply rate too low
    email_file = output_dir / "email-sequences.md"
    if reply_rate < 3.0 and emails_sent >= 20 and email_file.exists():
        print(yellow(f"\n  Reply rate {reply_rate:.1f}% < 3% threshold — improving emails..."))
        patterns = "; ".join(
            r.get("summary","") for r in classified
            if r.get("classification") in ("not_now","wrong_person")
        )[:300]
        improved = call_llm(
            EMAIL_FIX_PROMPT.format(
                reply_rate=reply_rate,
                sequence=email_file.read_text()[:2000],
                wrong_pct=wrong_pct,
                patterns=patterns or "none identified"
            ),
            system="Cold email copywriter. Improve reply rate. Output only markdown."
        )
        applied = apply_change(
            email_file, improved,
            f"Improve email sequences (reply rate {reply_rate:.1f}%)",
            state, "Loop 3 — Reply Monitor", autonomous
        )
        if applied:
            state["email_rewrites"] = state.get("email_rewrites",0) + 1

    # Refine ICP if too many wrong-person replies
    target_file = output_dir / "target.md"
    if wrong_pct > 30 and target_file.exists():
        print(yellow(f"\n  {wrong_pct:.0f}% wrong-person replies — refining ICP..."))
        wrong_people = "\n".join(
            f"- {r.get('sender','')}: {r.get('summary','')}"
            for r in classified if r.get("classification") == "wrong_person"
        )[:500]
        improved = call_llm(
            ICP_REFINE_FROM_REPLIES_PROMPT.format(
                wrong_pct=wrong_pct,
                wrong_people=wrong_people,
                target_md=target_file.read_text()[:2000]
            ),
            system="B2B ICP specialist. Output only markdown."
        )
        applied = apply_change(
            target_file, improved,
            f"Refine ICP ({wrong_pct:.0f}% wrong-person replies)",
            state, "Loop 3 — Reply Monitor", autonomous
        )
        if applied:
            state["target_rewrites"] = state.get("target_rewrites",0) + 1

    return state


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def print_dashboard(slug: str, state: dict):
    print(f"\n{bold(blue('━━━ CAMPAIGN DASHBOARD: ' + slug.upper() + ' ━━━'))}")
    print(f"  Loops run:          {state.get('loop_count', 0)}")
    print(f"  File quality:       {'✓ Passed' if state.get('file_quality_passed') else '— Not checked'}")
    print(f"  File rewrites:      {state.get('file_rewrites', 0)}")
    print(f"  Leads scored:       {state.get('leads_scored', 0)}")
    print(f"  Leads rejected:     {state.get('leads_rejected', 0)}")
    print(f"  ICP refinements:    {state.get('target_rewrites', 0)}")
    print(f"  Emails sent:        {state.get('emails_sent', 0)}")
    print(f"  Total replies:      {state.get('replies_total', 0)}")
    print(f"  Reply rate:         {state.get('reply_rate', 0):.1f}%")
    print(f"  Positive rate:      {state.get('positive_rate', 0):.1f}%")
    print(f"  Email rewrites:     {state.get('email_rewrites', 0)}")

    improvements = state.get("improvements", [])
    if improvements:
        print(f"\n  {bold('Improvements made')} ({len(improvements)} total):")
        for imp in improvements[-5:]:
            ts = imp.get("timestamp","")[:16].replace("T"," ")
            print(f"    {dim(ts)} {cyan(imp.get('loop',''))} → {imp.get('label','')}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
def run_gate(slug: str, autonomous: bool):
    """Pre-send gate: quality check + lead scoring. Called by run.py."""
    print(bold(f"\n🔒 Pre-send quality gate for: {slug}"))
    state = load_state(slug)
    state = loop1_file_gate(slug, state, autonomous)
    state = loop2_lead_scoring(slug, state, autonomous)
    save_state(slug, state)
    print_dashboard(slug, state)
    return state

def run_watch(slug: str, autonomous: bool, interval_hours: int = 24):
    """Watch mode: runs reply monitor on a schedule. Runs indefinitely."""
    print(bold(f"\n👁  Watching campaign: {slug}"))
    print(dim(f"   Reply monitor runs every {interval_hours}h"))
    print(dim(f"   Mode: {'autonomous (no prompts)' if autonomous else 'approval required'}"))
    print(dim("   Press Ctrl+C to stop\n"))

    while True:
        try:
            state = load_state(slug)
            state = loop3_reply_monitor(slug, state, autonomous)
            save_state(slug, state)
            print_dashboard(slug, state)

            next_run = datetime.now() + timedelta(hours=interval_hours)
            print(dim(f"  Next run: {next_run.strftime('%Y-%m-%d %H:%M')}"))
            print(dim("  (Ctrl+C to stop)\n"))
            time.sleep(interval_hours * 3600)

        except KeyboardInterrupt:
            print(yellow("\n\nStopped."))
            break

def run_once(slug: str, autonomous: bool):
    """Run all three loops once."""
    state = load_state(slug)
    state = loop1_file_gate(slug, state, autonomous)
    state = loop2_lead_scoring(slug, state, autonomous)
    state = loop3_reply_monitor(slug, state, autonomous)
    save_state(slug, state)
    print_dashboard(slug, state)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Self-improving quality loop for B2B outreach campaigns"
    )
    parser.add_argument("--slug",     required=True, help="Company folder name")
    parser.add_argument("--mode",     choices=["gate","watch","auto","once"],
                        default="once",
                        help="gate=pre-send check | watch=scheduled | auto=no prompts | once=all loops")
    parser.add_argument("--interval", type=int, default=24,
                        help="Hours between watch runs (default: 24)")
    args = parser.parse_args()

    output_dir = Path(args.slug)
    if not output_dir.exists():
        print(red(f"Error: folder '{args.slug}/' not found."))
        print(dim("Run: python run.py --url https://yourcompany.com first."))
        sys.exit(1)

    autonomous = args.mode == "auto"

    if args.mode == "gate":
        run_gate(args.slug, autonomous=False)
    elif args.mode == "watch":
        run_watch(args.slug, autonomous=False, interval_hours=args.interval)
    elif args.mode == "auto":
        run_watch(args.slug, autonomous=True, interval_hours=args.interval)
    else:
        run_once(args.slug, autonomous=False)


if __name__ == "__main__":
    main()
