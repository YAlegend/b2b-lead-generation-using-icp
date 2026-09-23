---
name: b2b-outreach-framework
description: >
  Generate a complete B2B outreach system for any company from just a website
  URL and/or a brief description. Use this skill whenever the user wants to:
  generate leads, build a cold outreach system, create a B2B marketing plan,
  set up lead generation, write cold emails, build a sales pipeline, create an
  ICP, run a B2B sprint, or says things like "set up outreach for [company]",
  "build lead gen for [URL]", "create a sales system for my company", "generate
  all the outreach files", or pastes a company URL asking for a marketing or
  sales plan. Always use this skill when a website URL or company details are
  provided alongside any sales, lead, outreach, or marketing intent.
---

# B2B Outreach Framework

Generate a complete, company-specific B2B outreach system from a single input:
a website URL and/or a description of any company in any industry.

---

## What This Skill Produces

One URL or description in → a full set of populated files out:

```
{company-slug}/
├── product.md             ← Description of what the company sells (OpenOutreach ready)
├── target.md              ← ICP definition + verticals (OpenOutreach ready)
├── positioning.md         ← 1-sentence statement + vertical variants
├── email-sequences.md     ← Cold email sequence per vertical
├── linkedin.md            ← Profile headlines + thought leadership posts
├── discovery-call.md      ← 30-min call script + qualifying questions
├── proposal-template.md   ← Scoped proposal with pricing guidance
└── week-by-week.md        ← 6-week execution plan with daily checklists
```

---

## Step 1 — Extract Company Intelligence

**If a URL is provided:** use web_fetch or web_search to read the website.
**If a description is provided:** extract directly from what the user gave.
**If both:** combine them — the user's description takes priority.

Extract only what you can confirm. Do not guess or invent:

```
COMPANY INTELLIGENCE BRIEF
===========================
Company name:
Website:
What they sell (product / service / platform):
Who they sell to (their stated target customer):
Key differentiators or claims:
Pricing signals (ranges, tiers, "enterprise", minimum deal size):
Industries or verticals they serve:
Geography (where they operate or sell):
Notable clients or case studies:
Founding team background (if relevant):
What they are NOT (stated exclusions or out-of-scope):
```

---

## Step 2 — Confirm Before Generating

Show the user a brief summary:

```
Here's what I found about [Company Name]:
- They sell: ...
- To: ...
- Minimum deal / price point: ...
- Key verticals: ...
- Geography: ...

Generating all 8 outreach files now.
Reply to correct anything, or say "go" to continue.
```

Proceed immediately if the user says "go" or gives no correction in the same turn.

---

## Step 3 — Generate All 8 Files

Generate every file below in sequence.
Write each as a **fully populated** markdown file — no placeholders, no blanks.
Every field must contain real, company-specific content from Step 1.

Separate each file with a clear header:
```
---
## FILE: product.md
[full content]

---
## FILE: target.md
[full content]
```

---

### FILE 1: product.md

A detailed description of the company written as input for OpenOutreach.
Structure: read `openoutreach/templates/product-template.md`.

Must include:
- What the company does (2–3 paragraphs, first person)
- What they deliver (bullet list of services or products)
- Representative client work or outcomes (from website if available)
- Why clients choose them
- Minimum engagement size or price point (if known)
- Who they are NOT a fit for

Adapt language to the company's industry. Do not use electronics or hardware
terminology unless the company is in that field.

---

### FILE 2: target.md

Full ICP definition for OpenOutreach.
Structure: read `openoutreach/templates/target-template.md`.

Must include:
- Who the ideal contact is (role, mindset, pain point)
- 2–4 verticals derived from the company's actual customer base, each with:
  - Company type and stage
  - Job titles to target
  - Buying signal keywords
  - What they are NOT (disqualifiers per vertical)
- Global disqualifying signals
- Geography
- Plain-language summary of a perfect lead

Verticals must reflect the company's real industry, not a generic template.

---

### FILE 3: positioning.md

Read `framework/phase1-define/positioning-guide.md` for the formula.

Must include:
- Primary 1-sentence positioning statement (who / what / outcome)
- 2–3 vertical-specific variants
- LinkedIn About section (first 2 lines visible before "see more")
- Tagline (8 words or fewer)

All copy must match the company's actual voice and industry. Avoid generic
phrases like "world-class", "innovative solutions", or "cutting-edge".

---

### FILE 4: email-sequences.md

Read `framework/phase4-outreach/email-guide.md` for tone and structure rules.

For the top 2 verticals, generate:
- Email 1: Initial cold outreach (subject + body, under 120 words)
- Email 2: Follow-up day 5 (adds value, under 80 words)
- Email 3: Final "breakup" email day 12 (under 60 words)

All emails must:
- Open with a personalisation hook specific to that vertical's buyer
- Reference the company's real service or product
- Address the vertical's actual pain point
- End with a soft CTA (20-min call, not "buy now")
- Match the tone appropriate for the industry (see email-guide.md)

---

### FILE 5: linkedin.md

Must include:
- 3 LinkedIn headline variants for the BD / founder / sales profile
- LinkedIn About section (100–150 words)
- 2 thought leadership post drafts (300–400 words each):
  - Post 1: A pain point the target buyer faces (educational, no hard sell)
  - Post 2: A result or outcome story (can be anonymised)

Tone and vocabulary must match the company's industry.

---

### FILE 6: discovery-call.md

Must include:
- 30-minute call structure with time splits
- Opening / icebreaker tailored to the buyer persona
- 6 qualifying questions covering budget, authority, need, and timeline
- How to position the company's services based on what the prospect says
- 2 ways to handle "we're not ready yet"
- Closing line to secure the next step

Questions must be tailored to the company's actual buyers, not generic.

---

### FILE 7: proposal-template.md

Must include:
- Executive summary (fill-in structure with the company's service language)
- Scope of work (phases or deliverables matching what the company sells)
- Timeline structure
- Pricing section with guidance matching the company's deal size signals
- Payment schedule recommendation
- Next steps / signature block

Do not include services the company does not offer.

---

### FILE 8: week-by-week.md

Read `framework/phase7-track/kpi-guide.md` for metric targets.

Must include:
- 6-week table: goal, daily actions, Claude prompts to use each week
- Detailed Day-by-day checklist for Week 1
- KPI targets per week
- Recommended free tool stack (OpenOutreach + Gmail + Apollo free + HubSpot free + Calendly)
- The funnel math showing how outreach volume leads to revenue target

Revenue target and deal size must reflect the company's actual price point.

---

## Step 4 — Save Files Locally

After generating, give the user these commands:

```bash
# Replace SLUG with the company name (e.g. acme-corp, brightwave)
SLUG="your-company-slug"
mkdir -p ~/outreach/$SLUG
cd ~/outreach/$SLUG

# Save each generated file into this folder, then:
openoutreach init --product-docs product.md --target target.md
```

---

## Step 5 — Offer Next Actions

After generating all files, offer:

1. **Run OpenOutreach** — help install and run `openoutreach find 10`
2. **Refine a file** — rewrite any file in a different tone or for a new vertical
3. **Add a vertical** — generate emails + ICP for an additional vertical
4. **Build a one-pager** — capability deck or HTML landing page outline

---

## Strict Rules

- Never leave a placeholder like `[INSERT X]` — generate real content or ask for the missing detail
- Never use electronics, hardware, or any other industry-specific language unless that is the company's actual industry
- Match the company's pricing language exactly — if they say "$5k/month", use that framing
- All emails must be under the word limits — no exceptions
- Geography must be reflected in ICP, tone, and spelling (e.g. UK spelling for UK companies)
- If the website is inaccessible, ask the user to paste the key sections or describe the company
- The examples/labtronics/ folder is a reference only — never copy its content into a new company's files
