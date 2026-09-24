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
"""

from __future__ import annotations

import csv
import io
import json
import re

import requests

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

Pick 2-6 job titles that appear across the document's verticals. Pick 2-5
industry or keyword terms. Pick company size ranges (from the fixed list
above) that best match any company-size or stage language in the document —
default to a broad spread like ["1-10","11-50","51-200"] if none is stated.
Pick locations only if the document names a specific geography; otherwise
use an empty list. If the document gives no usable signal for a field, use
a sensible generic default rather than an empty array (except locations)."""


def _extract_criteria(target_md: str, llm_provider: str, llm_api_key: str) -> dict:
    try:
        raw = call_llm(llm_provider, llm_api_key, target_md, CRITERIA_SYSTEM)
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
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["name", "title", "company", "email"])
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "name": row.get("name", ""),
            "title": row.get("title", ""),
            "company": row.get("company", ""),
            "email": row.get("email", ""),
        })
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
