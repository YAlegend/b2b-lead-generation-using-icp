"""
Direct lead discovery for people without a BetterContact key.

OpenOutreach's own finder hard-requires a BetterContact key for its
discovery step (BetterContact's Lead Finder API is what searches for leads
matching an ICP in that library — see openoutfind/discovery.py). Apollo and
RocketReach can only supplement it for email lookups there, not replace it.

This module bypasses OpenOutreach entirely: it uses the same LLM already
configured for file generation to turn target.md into structured search
criteria, then calls Apollo's or RocketReach's own people-search APIs
directly. Verified against each provider's own API docs (Sept 2026):
  - Apollo:      POST /api/v1/mixed_people/api_search (search, free-ish)
                 POST /api/v1/people/bulk_match       (reveal, costs credits)
  - RocketReach: POST /api/v2/person/search           (search)
                 GET  /api/v2/person/lookup            (reveal, costs credits)
  - People Data Labs: POST /v5/person/search           (search, 100 free/month)

search_people() (the /find page) can then fill in and check emails for
free via emails.py (Hunter + QuickEmailVerification).
"""

from __future__ import annotations

import csv
import io
import json
import re

import requests

from emails import hunter_find_emails, verify_emails
from llm import call_llm, LLMError


class DiscoveryError(RuntimeError):
    pass


CRITERIA_SYSTEM = """You extract structured lead-search criteria from a B2B
target-market document. Output ONLY a JSON object, no markdown fences, no
explanation, matching exactly this shape:

{
  "job_titles": ["..."],
  "industries_or_keywords": ["..."],
  "company_size_ranges": ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"],
  "locations": ["..."]
}

Pick at most 4 job titles, each a short plain title only — no acronyms in
parentheses, no slashes joining alternatives, e.g. "VP Engineering" not
"VP / Director of Engineering (VP Eng)". Pick at most 3 industry or
keyword terms, each 1-2 words. Pick at most 2 company size ranges from
the fixed list above (not the whole list) that best match any
company-size or stage language in the document — default to ["1-10",
"11-50"] if none is stated. Pick locations only if the document names a
specific geography, at most 2, otherwise use an empty list. Keep every
string short. Total response under 500 characters."""


QUERY_SYSTEM = """You turn a plain-English description of the people someone
wants to find (e.g. "VPs of Engineering at SaaS companies in Boston") into
structured lead-search criteria. Output ONLY a JSON object, no markdown
fences, no explanation, matching exactly this shape:

{
  "job_titles": ["..."],
  "industries_or_keywords": ["..."],
  "company_size_ranges": ["1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"],
  "locations": ["..."]
}

Only fill a field from what the request actually says — use an empty list
for anything it doesn't mention (don't guess a company size or location).
At most 4 job titles, each a short plain title, and include close variants
of the one asked for (e.g. "Head of Marketing" also "VP Marketing"). At
most 3 industry or keyword terms, 1-2 words each. Company sizes only from
the fixed list above. At most 2 locations. Total response under 500
characters."""


def _extract_criteria(target_md: str, llm_provider: str, llm_api_key: str,
                      system: str = CRITERIA_SYSTEM) -> dict:
    try:
        raw = call_llm(llm_provider, llm_api_key, target_md, system, max_tokens=600)
    except LLMError as exc:
        raise DiscoveryError(f"Could not analyze target market: {exc}") from exc

    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        criteria = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise DiscoveryError(f"LLM returned non-JSON search criteria: {raw[:200]}") from exc

    criteria.setdefault("job_titles", [])
    criteria.setdefault("industries_or_keywords", [])
    criteria.setdefault("company_size_ranges", ["1-10", "11-50", "51-200"])
    criteria.setdefault("locations", [])
    return criteria


def _rows_to_csv(rows: list[dict]) -> str:
    fields = ["name", "title", "company", "email"]
    if any(r.get("email_status") for r in rows):
        fields.append("email_status")
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({f: row.get(f, "") for f in fields})
    return out.getvalue().strip()


# ── Apollo ───────────────────────────────────────────────────────────────

def _apollo_search(criteria: dict, api_key: str, count: int) -> list[dict]:
    body = {
        "per_page": min(max(count, 1), 100),
        "page": 1,
    }
    if criteria["job_titles"]:
        body["person_titles"] = criteria["job_titles"]
    if criteria["industries_or_keywords"]:
        body["q_keywords"] = " ".join(criteria["industries_or_keywords"][:3])
    if criteria["company_size_ranges"]:
        body["organization_num_employees_ranges"] = criteria["company_size_ranges"]
    if criteria["locations"]:
        body["person_locations"] = criteria["locations"]

    resp = requests.post(
        "https://api.apollo.io/api/v1/mixed_people/api_search",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json=body, timeout=60,
    )
    if resp.status_code >= 400:
        raise DiscoveryError(f"Apollo search returned {resp.status_code}: {resp.text[:300]}")

    people = resp.json().get("people", [])[:count]
    if not people:
        return []

    return [{
        "id": p.get("id", ""),
        "name": f"{p.get('first_name', '')} {p.get('last_name_obfuscated', '')}".strip(),
        "title": p.get("title") or "",
        "company": (p.get("organization") or {}).get("name", ""),
        "domain": (p.get("organization") or {}).get("primary_domain") or "",
        "email": "",
    } for p in people]


def _apollo_reveal(rows: list[dict], api_key: str) -> None:
    """Reveal full name + work email in place, 10 at a time (API batch limit)."""
    for i in range(0, len(rows), 10):
        batch = rows[i:i + 10]
        resp = requests.post(
            "https://api.apollo.io/api/v1/people/bulk_match",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={"details": [{"id": r["id"]} for r in batch]},
            timeout=60,
        )
        if resp.status_code >= 400:
            raise DiscoveryError(f"Apollo enrichment returned {resp.status_code}: {resp.text[:300]}")

        matches = resp.json().get("matches", [])
        for row, match in zip(batch, matches):
            if match.get("email"):
                row["name"] = f"{match.get('first_name', '')} {match.get('last_name', '')}".strip() or row["name"]
                row["email"] = match["email"]
                row["title"] = match.get("title") or row["title"]


def find_leads_apollo(target_md: str, api_key: str, llm_provider: str, llm_api_key: str,
                       count: int = 10, with_emails: bool = False) -> str:
    criteria = _extract_criteria(target_md, llm_provider, llm_api_key)
    rows = _apollo_search(criteria, api_key, count)
    if not rows:
        return ""
    if with_emails:
        _apollo_reveal(rows, api_key)
    return _rows_to_csv(rows)


# ── RocketReach ──────────────────────────────────────────────────────────

def _rocketreach_search(criteria: dict, api_key: str, count: int) -> list[dict]:
    query = {}
    if criteria["job_titles"]:
        query["current_title"] = criteria["job_titles"]
    if criteria["industries_or_keywords"]:
        query["company_industry"] = criteria["industries_or_keywords"]
    if criteria["company_size_ranges"]:
        query["company_size"] = criteria["company_size_ranges"]
    if criteria["locations"]:
        query["location"] = criteria["locations"]

    resp = requests.post(
        "https://api.rocketreach.co/api/v2/person/search",
        headers={"Api-Key": api_key, "Content-Type": "application/json"},
        json={"query": query, "page_size": min(max(count, 1), 100), "start": 1},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise DiscoveryError(f"RocketReach search returned {resp.status_code}: {resp.text[:300]}")

    people = resp.json().get("profiles", resp.json().get("people", []))[:count]
    return [{
        "id": p.get("id", ""),
        "name": p.get("name", ""),
        "title": p.get("current_title") or "",
        "company": p.get("current_employer") or "",
        "domain": p.get("current_employer_domain") or "",
        "email": "",
    } for p in people]


def _rocketreach_reveal(rows: list[dict], api_key: str) -> None:
    for row in rows:
        if not row["id"]:
            continue
        resp = requests.get(
            "https://api.rocketreach.co/api/v2/person/lookup",
            headers={"Api-Key": api_key},
            params={"id": row["id"]}, timeout=30,
        )
        if resp.status_code >= 400:
            continue
        emails = resp.json().get("emails") or []
        if emails:
            row["email"] = emails[0].get("email", "") if isinstance(emails[0], dict) else emails[0]


def find_leads_rocketreach(target_md: str, api_key: str, llm_provider: str, llm_api_key: str,
                            count: int = 10, with_emails: bool = False) -> str:
    criteria = _extract_criteria(target_md, llm_provider, llm_api_key)
    rows = _rocketreach_search(criteria, api_key, count)
    if not rows:
        return ""
    if with_emails:
        _rocketreach_reveal(rows, api_key)
    return _rows_to_csv(rows)


# ── People Data Labs ─────────────────────────────────────────────────────
# POST /v5/person/search takes an Elasticsearch query; 1 credit per record
# returned (free plan: 100/month). No matches comes back as a 404, not an
# empty list. Free plans return contact fields as true/false flags, so
# emails only appear on paid plans — there's no separate reveal call.

def _pdl_search(criteria: dict, api_key: str, count: int) -> list[dict]:
    must = []
    if criteria["job_titles"]:
        must.append({"bool": {"should": [{"match_phrase": {"job_title": t.lower()}}
                                         for t in criteria["job_titles"]]}})
    if criteria["company_size_ranges"]:
        must.append({"terms": {"job_company_size": criteria["company_size_ranges"]}})
    if criteria["locations"]:
        must.append({"bool": {"should": [{"match": {"location_name": {"query": loc.lower(), "operator": "and"}}}
                                         for loc in criteria["locations"]]}})
    # Industry wording from the LLM ("fintech") rarely matches PDL's fixed
    # industry names ("financial services"), so it ranks results rather
    # than filtering them out.
    should = [{"match": {"job_company_industry": k.lower()}} for k in criteria["industries_or_keywords"]]

    resp = requests.post(
        "https://api.peopledatalabs.com/v5/person/search",
        headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
        json={"query": {"bool": {"must": must, "should": should}},
              "size": min(max(count, 1), 100), "titlecase": True},
        timeout=60,
    )
    if resp.status_code == 404:
        return []
    if resp.status_code == 402:
        raise DiscoveryError("People Data Labs: you've used this month's free credits (100/month).")
    if resp.status_code >= 400:
        raise DiscoveryError(f"People Data Labs search returned {resp.status_code}: {resp.text[:300]}")

    return [{
        "id": p.get("id", ""),
        "name": p.get("full_name") or "",
        "title": p.get("job_title") or "",
        "company": p.get("job_company_name") or "",
        "domain": p.get("job_company_website") or "",
        "email": p["work_email"] if isinstance(p.get("work_email"), str) else "",
    } for p in resp.json().get("data", [])[:count]]


def _pdl_reveal(rows: list[dict], api_key: str) -> None:
    """Nothing to do: emails already come back in search results on paid plans."""


# ── Free-text search (the /find page) ────────────────────────────────────

SEARCHERS = {
    "apollo": (_apollo_search, _apollo_reveal),
    "rocketreach": (_rocketreach_search, _rocketreach_reveal),
    "pdl": (_pdl_search, _pdl_reveal),
}


def search_people(query: str, provider: str, api_key: str, llm_provider: str,
                  llm_api_key: str, count: int = 10, with_emails: bool = False,
                  hunter_key: str = "", qev_key: str = "") -> tuple[dict, list[dict], str, list[str]]:
    """Search from a plain-English request. Returns (criteria, rows, csv, notes).

    Optional free extras, run after the provider's own reveal: Hunter finds
    emails for rows still missing one, then QuickEmailVerification checks
    every email. Their problems (quota used up, bad key) come back as notes
    so the people found are still shown.
    """
    if provider not in SEARCHERS:
        raise DiscoveryError(f"Unknown lead provider: {provider}")
    search, reveal = SEARCHERS[provider]
    criteria = _extract_criteria(query, llm_provider, llm_api_key, QUERY_SYSTEM)
    if not any(criteria.values()):
        raise DiscoveryError("Couldn't pick out any job titles, industries, sizes or locations "
                             "from that search — try naming a role, e.g. \"Heads of Sales at fintech startups\".")
    try:
        rows = search(criteria, api_key, count)
        if rows and with_emails:
            reveal(rows, api_key)
    except requests.RequestException as exc:
        raise DiscoveryError(f"Could not reach {provider}: {exc}") from exc

    notes: list[str] = []
    if rows and hunter_key:
        notes += hunter_find_emails(rows, hunter_key)
    if rows and qev_key:
        notes += verify_emails(rows, qev_key)
    return criteria, rows, _rows_to_csv(rows) if rows else "", notes
