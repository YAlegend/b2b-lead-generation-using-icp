---
name: b2b-outreach
description: >
  Build a complete B2B outreach system for any company from a website URL or a
  short description — positioning, ICP, cold email sequences, LinkedIn copy,
  discovery-call script, proposal template, 6-week plan — then research real
  leads on the public web and write personalised first emails for each one.
  Needs no API keys: the agent does the writing and the web research itself.
  Use whenever someone wants lead generation, cold outreach, an ICP, a sales
  pipeline, prospect lists, cold emails, or a B2B go-to-market plan, or pastes
  a company URL and asks for sales or marketing help — e.g. "set up outreach
  for acme.com", "find me 20 leads for my agency", "who should I be cold
  emailing", "write cold emails for these prospects". Also use it to review
  campaign results and improve the emails and targeting — "nobody is replying
  to my cold emails", "I sent 40 emails, got 2 replies, what should I change".
license: MIT
metadata:
  version: 2.1.0
  hermes:
    tags: [Sales, Outreach, Lead Generation, Cold Email, ICP, B2B]
---

# B2B Outreach

Turn one company URL or description into a ready-to-run outreach system and a
researched lead list. Everything here runs on the agent itself: you write the
files, and you find leads with whatever web search / page-reading ability you
already have. No paid data provider, no LLM API key, no email-finder key.

That constraint shapes the whole skill. Without a contact database you cannot
pull 500 verified emails in a minute, but you *can* find 10–30 genuinely
well-matched people with a real reason to contact each one — which is what
gets replies anyway.

## Pick the mode

Read the request and choose. Ask only if it's genuinely unclear.

| The user wants… | Mode | Do |
|---|---|---|
| A full outreach setup for a company | **Full kit** | Steps 1 → 4 |
| Only leads ("find me prospects for X") | **Leads** | Step 1 (brief only), Step 2 short summary, then Step 4 |
| Emails for people they already have | **Emails** | Step 1 (brief only), then Step 4e for their list |
| A change to a file made earlier | **Refine** | Edit just that file, then Loop 1 on it |
| To review results / "not getting replies" | **Improve** | Loop 3 in `references/improve-loop.md` |

**Returning to a company you've done before?** If `outreach/{slug}/` exists,
read its `learnings.md` first and apply it — that's what makes each run
better than the last.

## What tools you might have

Check what you can actually do before starting, and adapt — don't fail.

- **Can search the web and read pages** (Claude with web tools, Codex with
  browsing, Hermes `web_search`/`web_extract`, a browser tool, `curl`): do
  everything below yourself.
- **Can read pages but not search:** read the company site directly; for
  leads, ask the user to paste search results or a list of target companies,
  then research each company's own site.
- **No web access at all** (a plain chat model): ask the user to paste the
  key parts of their website (home, about, services/pricing, case studies).
  Generate the files. For leads, give them the exact search queries from
  `references/lead-research.md` to run themselves and paste back.
- **Can write files:** save into `outreach/{company-slug}/`. Otherwise print
  each file in full under a `## FILE: name.md` header so it can be copied.
- **Can run Python:** use `scripts/check_files.py` (standard library only)
  for the mechanical checks in the improve loop. Otherwise check by hand.

## Step 1 — Company brief

From the URL (read the home, about, services/product, pricing and case-study
pages) and/or the user's description — the user's description wins any
conflict — fill this in. Only write what you can confirm; put "unknown" rather
than guess, because every later file inherits these facts and an invented
client name or price ends up in an email sent to a real person.

```
COMPANY BRIEF
Company / website:
What they sell:
Who they sell to (as stated):
Proof (named clients, case studies, numbers):
Price signals (ranges, tiers, minimums):
Verticals served:
Geography + spelling (US/UK/…):
Voice (formal, technical, warm, …):
Not a fit for (stated exclusions):
```

If a page comes back nearly empty (a menu, a cookie banner, "enable
JavaScript"), the site is probably built in JavaScript and your fetch got the
shell, not the text. Before giving up, try in this order:

1. A browser tool, if you have one — it runs the JavaScript.
2. `https://r.jina.ai/{full URL}` — a free reader that returns the rendered
   page as text, no key needed.
3. The raw HTML's `<title>`, meta description and `og:` tags, plus
   `/sitemap.xml` for page names worth reading.
4. Search results for the company name (their LinkedIn page, directory
   listings, press) — mark anything from these as third-party.

If none of these give you real content, say so and ask the user to paste or
describe — don't fill the gaps from imagination.

## Step 2 — Confirm

Show a 5-line summary (sells / to / price point / verticals / geography) and
say you're continuing. If the user is present and corrects anything, use the
correction. If they said "just do it" or you're running unattended, proceed.

## Step 3 — Generate the files (Full kit)

Write all eight. Each must be fully populated with this company's real
content — no `[INSERT X]`. If a fact is truly unknown (e.g. price), write the
section around what *is* known and add one line saying what the user should
fill in; that's honest and still usable.

Read the matching reference before writing each file — they hold the
structure and the word limits:

| File | Read first | Must contain |
|---|---|---|
| `product.md` | `references/product-template.md` | What they do (first person), deliverables, representative work, why chosen, engagement size, not-a-fit |
| `target.md` | `references/target-template.md` | Ideal contact; 2–4 verticals from their real customer base, each with company type, stage, job titles, buying-signal keywords, disqualifiers; global disqualifiers; geography; one-paragraph perfect lead |
| `positioning.md` | `references/positioning-guide.md` | 1-sentence statement, one variant per vertical, LinkedIn About first 2 lines, tagline ≤ 8 words |
| `email-sequences.md` | `references/email-guide.md` | For the top 2 verticals: Email 1 (≤120 words), Email 2 day 5 (≤80), Email 3 day 12 (≤60), each with subject |
| `linkedin.md` | — | 3 headline variants, About (100–150 words), 2 posts of 300–400 words (a buyer pain point; an outcome story) |
| `discovery-call.md` | `references/discovery-guide.md` | 30-min structure, opener for this buyer, 6 BANT questions in their language, positioning moves, 2 "not ready yet" responses, close |
| `proposal-template.md` | `references/proposal-guide.md` | Exec summary, scope in their service language, timeline, pricing matching their deal size, payment schedule, next steps |
| `week-by-week.md` | `references/kpi-guide.md` | 6-week table, Week 1 day-by-day checklist, weekly KPIs, free tool stack, funnel math sized to their price point |

Things that make these good rather than generic:

- **Industry fit.** Vocabulary, tone and examples come from this company's
  field. The reference files contain examples from other industries; they are
  illustrations, never content to reuse.
- **Pricing language.** If they say "from $5k/month", say that. Size the
  funnel math in `week-by-week.md` to their actual deal size.
- **Geography.** Spelling, currency and regions follow the company.
- **No filler.** Skip "world-class", "innovative solutions", "cutting-edge".
- **Free tool stack** for the plan: their own email inbox, a spreadsheet or
  HubSpot free as CRM, Calendly free, LinkedIn free, and this skill for lead
  research. Paid tools only as optional upgrades.

### Quality gate

Before moving on, run **Loop 1** from `references/improve-loop.md`: the
mechanical checks (word counts, placeholders, filler) and the 6-point scores
for `product.md`, `target.md` and `email-sequences.md`. Fix only what failed,
at most 2 rounds. Lead search is only as good as `target.md`, so this is worth
the minute it takes.

## Step 4 — Find leads and draft first emails

This is the part that normally needs Apollo/Hunter API keys. Here you do it
by researching the public web. **Read `references/lead-research.md` before
starting** — it has the search patterns, email-pattern rules and the
compliance limits.

**4a. Turn `target.md` into searches.** For each vertical, pick 2–4 job
titles, the buying-signal keywords and the geography, and build queries from
the patterns in the reference.

**4b. Find companies, then people.** Work company-first: find organisations
that match a vertical and show a buying signal (hiring for a relevant role,
recent funding, a launch, expansion), then find the right person at each one
on the company's own team page, press releases, conference speaker lists,
podcast guest pages, or search-result snippets of public profiles. Aim for
10 leads unless the user asked for a number; more than ~30 in one go
usually means quality drops.

**4c. Email address.** Use, in order: an address the person or company
publishes; the company's visible address pattern applied to the name; a
common-pattern guess. Label which one it is in `email_confidence` —
`published`, `pattern-confirmed`, or `guess`. Never present a guess as
verified; a wrong address burns the sender's domain reputation.

**4d. Score.** Run **Loop 2** from `references/improve-loop.md`: score each
lead 1–10 against `target.md`, drop the rejects, and if more than 30% were
rejected, tighten `target.md` and search once more. Draft emails only for
leads that survive.

**4e. Personalise.** For each lead, write the hook (the specific, true,
recent thing you found) and a first email following `email-guide.md` that
opens with that hook. The hook must come from a source you actually read —
if you found nothing specific, say so and use the vertical's pain point
instead of inventing one.

**4f. Save.**

- `leads.csv` with these columns (sorted by score):
  `name,title,company,website,email,email_confidence,vertical,signal,hook,source_url,score,score_reason`
- `outreach-drafts.md`: one `## {name} — {company}` section per lead with
  `To:`, `Subject:` and the body — ready to paste into their inbox.
- Re-run the mechanical check on the drafts, then start `learnings.md`
  with what this run found (format in `improve-loop.md`).

**Sending is the user's job.** Don't send email on their behalf unless they
explicitly ask *and* you already have a mail tool they connected; even then,
create drafts and let them review. Cold email from a fresh inbox should start
at 10–20 a day (see `kpi-guide.md`).

## Step 5 — Wrap up

Give a short summary: where the files are, how many leads and how many have
`published`/`pattern-confirmed` emails vs guesses, and the three best leads
with why. Then offer: more leads for a specific vertical, rewrite a file in a
different tone, add a vertical, or follow-up emails (Email 2/3) for the leads.

Tell the user how the loop continues: once they've sent ~20 emails, come back
with "review my outreach" (paste replies, or let you read them if a mail tool
is connected) and you'll rewrite what isn't working. Offer to set this up as a
weekly scheduled task if their agent supports one.

## Rules that protect the user

- Invent nothing that will be sent to a real person: clients, numbers,
  quotes, mutual connections, or "I saw your post" when you didn't.
- Only use business contact information people or companies published
  themselves. Don't log in to LinkedIn or other sites, scrape behind logins,
  or bypass paywalls/robots blocks — search results and public pages only.
- Every drafted email includes a simple opt-out line ("Not relevant? Just
  reply and I won't follow up.") — CAN-SPAM, GDPR/PECR and CASL expect it.
- For EU/UK leads, note in the wrap-up that cold B2B email there needs a
  legitimate-interest basis and should target role-based relevance.
- `examples/` content (if present nearby) is reference only — never copy it.
