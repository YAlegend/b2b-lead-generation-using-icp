#!/usr/bin/env python3
"""Mechanical quality checks for a b2b-outreach output folder.

Usage: python3 check_files.py outreach/acme-corp

Checks what a model is bad at eyeballing: email word counts (a [Hook] field
counts as the ~20-word sentence it becomes), subject length,
leftover placeholders, banned filler phrases, opt-out lines, and leads.csv
columns/values. Standard library only. Exit code 1 if anything fails.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

EMAIL_LIMITS = {1: 120, 2: 80, 3: 60}
SUBJECT_MAX_WORDS = 8
HOOK_WORDS = 20  # a [Hook] merge field becomes one full sentence when filled in
LEAD_COLUMNS = ["name", "title", "company", "website", "email", "email_confidence",
                "vertical", "signal", "hook", "source_url"]
CONFIDENCE_VALUES = {"published", "pattern-confirmed", "guess", ""}
GENERATED_FILES = ["product.md", "target.md", "positioning.md", "email-sequences.md",
                   "linkedin.md", "discovery-call.md", "proposal-template.md",
                   "week-by-week.md", "outreach-drafts.md"]

PLACEHOLDER = re.compile(
    r"\[(?:insert|company|name|your|client|x|todo|tbd)[^\]]*\]|\{\{?[a-z_ ]+\}?\}|\bTBD\b|\bXXX\b|lorem ipsum",
    re.IGNORECASE)
BANNED = ["world-class", "cutting-edge", "innovative solutions", "synergy",
          "i hope this email finds you well", "i wanted to reach out", "best-in-class"]
OPT_OUT = re.compile(r"not relevant|unsubscribe|won't follow up|opt out|reply .*stop|let me know if .*not", re.IGNORECASE)

HEADING = re.compile(r"^#{1,6}\s+(.*)$")
EMAIL_HEADING = re.compile(r"\bemail\s*([123])\b", re.IGNORECASE)
SUBJECT = re.compile(r"^\**subject\**\s*:\**\s*(.+)$", re.IGNORECASE)
META_LINE = re.compile(r"^\**(subject|to|day|send|timing|cc)\**\s*:", re.IGNORECASE)


HOOK_FIELD = re.compile(r"\[[^\]]*hook[^\]]*\]", re.IGNORECASE)


def words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][\w'’.-]*", text))


def body_words(text: str) -> int:
    """Word count after filling in: each [Hook] field counts as a sentence."""
    hooks = len(HOOK_FIELD.findall(text))
    return words(HOOK_FIELD.sub(" ", text)) + hooks * HOOK_WORDS


def sections(md: str):
    """Yield (heading, body_lines) for each markdown heading."""
    heading, body = None, []
    for line in md.splitlines():
        m = HEADING.match(line)
        if m:
            if heading is not None:
                yield heading, body
            heading, body = m.group(1).strip(), []
        else:
            body.append(line)
    if heading is not None:
        yield heading, body


def email_body(lines: list[str]) -> tuple[str | None, str, bool]:
    """Return (subject, body, has_opt_out). The opt-out line isn't counted
    toward the word limit — it's required boilerplate, not copy."""
    subject, kept, opt_out = None, [], False
    for line in lines:
        s = line.strip()
        m = SUBJECT.match(s)
        if m:
            subject = m.group(1).strip().strip("*")
            continue
        if META_LINE.match(s) or s.startswith(("---", "```", ">")):
            continue
        if OPT_OUT.search(s):
            opt_out = True
            continue
        kept.append(s)
    return subject, " ".join(kept), opt_out


def check_emails(path: Path, fails: list[str]) -> int:
    count = 0
    for heading, lines in sections(path.read_text()):
        m = EMAIL_HEADING.search(heading)
        if not m:
            continue
        n = int(m.group(1))
        subject, body, _ = email_body(lines)
        if not body.strip():
            continue
        count += 1
        wc = body_words(body)
        if wc > EMAIL_LIMITS[n]:
            fails.append(f"{path.name}: '{heading}' is {wc} words (limit {EMAIL_LIMITS[n]})")
        if subject and words(subject) > SUBJECT_MAX_WORDS:
            fails.append(f"{path.name}: '{heading}' subject is {words(subject)} words (limit {SUBJECT_MAX_WORDS})")
    if count == 0:
        fails.append(f"{path.name}: no sections headed 'Email 1/2/3' found — can't check word limits")
    return count


def check_drafts(path: Path, fails: list[str]) -> int:
    """outreach-drafts.md: one section per lead, each a first email (≤120 words)."""
    count = 0
    for heading, lines in sections(path.read_text()):
        subject, body, opt_out = email_body(lines)
        if not subject:
            continue  # not an email section
        count += 1
        wc = body_words(body)
        if wc > EMAIL_LIMITS[1]:
            fails.append(f"{path.name}: draft '{heading}' is {wc} words (limit {EMAIL_LIMITS[1]})")
        if words(subject) > SUBJECT_MAX_WORDS:
            fails.append(f"{path.name}: draft '{heading}' subject is {words(subject)} words (limit {SUBJECT_MAX_WORDS})")
        if not opt_out:
            fails.append(f"{path.name}: draft '{heading}' has no opt-out line")
    return count


def check_leads(path: Path, fails: list[str]) -> int:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        missing = [c for c in LEAD_COLUMNS if c not in cols]
        if missing:
            fails.append(f"leads.csv: missing columns {missing}")
        rows = list(reader)
    seen = set()
    for i, row in enumerate(rows, start=2):
        who = row.get("name") or f"row {i}"
        conf = (row.get("email_confidence") or "").strip()
        if conf not in CONFIDENCE_VALUES:
            fails.append(f"leads.csv: {who} has email_confidence '{conf}' (use published / pattern-confirmed / guess)")
        if row.get("email") and not conf:
            fails.append(f"leads.csv: {who} has an email but no email_confidence")
        if not (row.get("source_url") or "").startswith("http"):
            fails.append(f"leads.csv: {who} has no source_url")
        key = ((row.get("name") or "").lower(), (row.get("company") or "").lower())
        if key in seen:
            fails.append(f"leads.csv: duplicate lead {who} @ {row.get('company')}")
        seen.add(key)
    return len(rows)


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if len(sys.argv) != 2 or sys.argv[1].startswith("-"):
        print(__doc__.strip().splitlines()[2])
        return 2
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return 2

    fails: list[str] = []
    notes: list[str] = []

    for name in GENERATED_FILES:
        path = folder / name
        if not path.exists():
            continue
        text = path.read_text()
        for m in PLACEHOLDER.finditer(text):
            fails.append(f"{name}: placeholder left in: '{m.group(0)}'")
        low = text.lower()
        for phrase in BANNED:
            if phrase in low:
                fails.append(f"{name}: filler phrase '{phrase}'")

    if (folder / "email-sequences.md").exists():
        notes.append(f"{check_emails(folder / 'email-sequences.md', fails)} sequence emails checked")
    if (folder / "outreach-drafts.md").exists():
        notes.append(f"{check_drafts(folder / 'outreach-drafts.md', fails)} drafts checked")
    if (folder / "leads.csv").exists():
        notes.append(f"{check_leads(folder / 'leads.csv', fails)} leads checked")

    present = [n for n in GENERATED_FILES[:8] if (folder / n).exists()]
    if present and len(present) < 8:
        notes.append("missing: " + ", ".join(n for n in GENERATED_FILES[:8] if n not in present))

    for n in notes:
        print(f"· {n}")
    if fails:
        print(f"\nFAIL — {len(fails)} issue(s):")
        for f in fails:
            print(f"  ✗ {f}")
        return 1
    print("\nPASS — all mechanical checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
