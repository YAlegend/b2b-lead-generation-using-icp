"""
Free email finding (Hunter) and verification (QuickEmailVerification) for
lead rows that came back without a usable email — e.g. People Data Labs'
free plan, or any search run without "reveal".

  - Hunter:  GET /v2/email-finder (name + company domain -> email). Credits
             are only charged when an email is found. 429 = monthly quota
             used up, 403 = rate limited.
  - QEV:     GET /v1/verify (email -> valid/invalid/unknown). 100 free per
             day. 402 = out of credits.

Both mutate rows in place and return human-readable notes (quota hit, key
rejected, ...) rather than raising, so a search that found people still
shows them even if email lookup fails partway.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests

WORKERS = 4


class _Stop(Exception):
    """Abort remaining lookups for this provider with a note for the user."""


def _truthy(value) -> bool:
    # QEV returns booleans as the strings "true"/"false".
    return value is True or str(value).lower() == "true"


# ── Hunter ───────────────────────────────────────────────────────────────

def _hunter_one(row: dict, api_key: str) -> None:
    name = row.get("name", "")
    if "*" in name or len(name.split()) < 2:
        return  # obfuscated or partial name (e.g. Apollo preview): nothing to search with
    params = {"full_name": name, "max_duration": 8}
    if row.get("domain"):
        params["domain"] = row["domain"]
    elif row.get("company"):
        params["company"] = row["company"]
    else:
        return

    resp = requests.get("https://api.hunter.io/v2/email-finder",
                        headers={"X-API-KEY": api_key}, params=params, timeout=20)
    if resp.status_code == 401:
        raise _Stop("Hunter rejected the API key.")
    if resp.status_code == 429:
        raise _Stop("Hunter: this month's free email-finder credits are used up.")
    if resp.status_code == 403:
        raise _Stop("Hunter is rate-limiting requests — try again in a minute.")
    if resp.status_code >= 400:
        return  # 400 (bad input for this person) / 451 (opted out): skip just this row

    email = (resp.json().get("data") or {}).get("email")
    if email:
        row["email"] = email


def hunter_find_emails(rows: list[dict], api_key: str) -> list[str]:
    todo = [r for r in rows if not r.get("email")]
    return _run(todo, lambda r: _hunter_one(r, api_key), "Hunter")


# ── QuickEmailVerification ───────────────────────────────────────────────

def _qev_one(row: dict, api_key: str) -> None:
    resp = requests.get("https://api.quickemailverification.com/v1/verify",
                        params={"email": row["email"], "apikey": api_key}, timeout=20)
    if resp.status_code == 401:
        raise _Stop("QuickEmailVerification rejected the API key.")
    if resp.status_code == 402:
        raise _Stop("QuickEmailVerification: today's free credits (100/day) are used up.")
    if resp.status_code == 429:
        raise _Stop("QuickEmailVerification is rate-limiting requests — try again in a minute.")
    if resp.status_code >= 400:
        return

    data = resp.json()
    if not _truthy(data.get("success", True)):
        return
    if data.get("result") == "valid":
        risky = _truthy(data.get("accept_all")) or _truthy(data.get("disposable"))
        row["email_status"] = "risky" if risky or not _truthy(data.get("safe_to_send", True)) else "valid"
    else:
        row["email_status"] = data.get("result") or "unknown"


def verify_emails(rows: list[dict], api_key: str) -> list[str]:
    todo = [r for r in rows if r.get("email")]
    return _run(todo, lambda r: _qev_one(r, api_key), "QuickEmailVerification")


# ── shared ───────────────────────────────────────────────────────────────

def _run(rows: list[dict], fn, provider: str) -> list[str]:
    notes: list[str] = []
    stopped = False

    def guarded(row):
        nonlocal stopped
        if stopped:
            return
        try:
            fn(row)
        except _Stop as exc:
            stopped = True
            if str(exc) not in notes:
                notes.append(str(exc))
        except requests.RequestException:
            if f"Couldn't reach {provider} for some people." not in notes:
                notes.append(f"Couldn't reach {provider} for some people.")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(guarded, rows))
    return notes
