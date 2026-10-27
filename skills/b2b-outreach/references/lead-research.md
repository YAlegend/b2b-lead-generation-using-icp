# Lead Research Without APIs

How to find real, well-matched B2B leads using only web search and public
pages. This replaces paid databases (Apollo, PDL, RocketReach) and email
finders (Hunter, BetterContact).

## Contents

1. Search patterns (companies, then people)
2. Buying signals worth looking for
3. Finding the email address
4. Per-lead research brief
5. Limits and compliance
6. If the user has to run the searches

---

## 1. Search patterns

Work **company-first**. A list of good-fit companies with a live reason to buy
beats a list of job titles. Replace the words in `{}` with values from
`target.md`.

### Finding companies

```
{vertical keyword} companies {city/country}
"{buying signal keyword}" {vertical keyword} {country}
{vertical keyword} "raised" OR "series a" OR "seed round" {current year}
"we're hiring" "{relevant role}" {vertical keyword}
site:{job board domain} "{relevant role}" {vertical keyword} {city}
"{competitor or adjacent tool}" customers {vertical keyword}
{industry} association members {country}
{industry} conference {current year} exhibitors OR sponsors
```

Useful public sources: company directories of industry associations, trade
show exhibitor lists, startup/accelerator portfolio pages, funding news,
"best X in {city}" listicles, review sites listing vendors in a category, and
job boards (a company hiring for the problem you solve is the strongest
signal there is).

### Finding the person at a company

```
{company name} "{job title}"
{company name} team OR "about us" OR leadership
site:linkedin.com/in "{job title}" "{company name}"
"{company name}" "{job title}" podcast OR interview OR speaker
site:{company domain} "{job title}"
```

- Read the company's own **team / about / leadership** page first.
- Search-result **snippets** of public profiles usually show name + title +
  company — enough. Don't open or log in to LinkedIn to scrape it.
- Small companies (< 20 people): the founder/CEO is usually the buyer.
- If two candidates fit, prefer the one whose role owns the pain in
  `target.md`, not the most senior title.

### Quality bar for a lead

Keep a lead only if all of these are true:
- Company matches a vertical in `target.md` and hits none of its disqualifiers.
- Person's title is one of the target titles or a clear equivalent.
- You can cite a `source_url` for the person's name and role.
- Information is current — prefer sources from the last 12 months; job titles
  older than ~2 years are often stale.

## 2. Buying signals

Record the strongest one in the `signal` column. In rough order of strength:

1. Hiring for a role that the company's product/service replaces or supports
2. Recent funding, acquisition, or new leadership in the relevant function
3. Product launch, new market, new office, or regulatory deadline
4. Public post/talk/interview about the problem you solve
5. Uses a tool your product integrates with or replaces
6. Fits the profile but no current signal (still valid, lower priority)

## 3. Finding the email address

Try in this order and record which one you used in `email_confidence`:

**`published`** — the address appears on a public page: the company's
contact/team page, a press release, a conference listing, a public
GitHub/profile page, or a document the company published.

**`pattern-confirmed`** — you found at least one *named person's* address at
the same domain (press releases and "media contact" sections are good places)
and applied that pattern to your lead. Generic inboxes like info@ or sales@
don't reveal the pattern.

**`guess`** — no pattern found. Use `first@domain` for companies under ~50
people, `first.last@domain` for larger ones. Tell the user these need
verifying before sending (a free checker, or simply send to the confirmed ones
first).

Common patterns, for reference:
`first@`, `first.last@`, `firstlast@`, `flast@`, `f.last@`, `first_last@`.

If there's no address at all, leave `email` blank and still keep the lead —
the user can reach them via a LinkedIn connection request or the company
contact form. Put "contact via LinkedIn" or the contact-page URL in the hook
notes.

## 4. Per-lead research brief

Keep it short; it exists to make Email 1 specific. For each lead note:

```
Company / website:
What they do (1 line):
Stage / size:
Signal (+ source URL):
Likely pain (1 line, tied to target.md):
Hook for Email 1 (1 specific, true, recent fact):
```

The hook goes in `leads.csv`; the rest can live in your notes or a
`research-notes.md` if the user wants it.

## 5. Limits and compliance

- Public sources only. No logging in, no scraping behind logins, no getting
  around paywalls, CAPTCHAs or robots blocks, no buying/using leaked data.
- Business contact details only — never personal phone numbers, home
  addresses or personal email providers (gmail.com etc.) unless that's
  what the person publishes for business.
- Every email draft needs an opt-out line and the sender's real identity.
- EU/UK (GDPR/PECR): B2B cold email to individuals at companies relies on
  legitimate interest — keep it relevant to the person's role, include
  opt-out, and honour opt-outs. Canada (CASL) is stricter; flag Canadian
  leads to the user.
- Pace the search: a few dozen queries per run is fine; don't hammer one site.

## 6. If the user has to run the searches

When you have no web access, give the user a ready-to-paste block:

```
Please run these searches and paste back the top results (titles, snippets and URLs):

1. {query}
2. {query}
...
```

Then extract leads from what they paste, apply the quality bar above, and
fill `leads.csv` the same way. Mark every email as `guess` unless the pasted
text shows it.
