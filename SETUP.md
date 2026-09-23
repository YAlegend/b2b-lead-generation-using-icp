# Setup Guide — From Files to Leads

> You have your generated files. This guide takes you from there to
> finding leads and sending cold emails, step by step.

---

## What You Need

| Thing | Where to get it | Cost |
|-------|----------------|------|
| Python (3.9+) | Already installed on most machines | Free |
| `uv` (package manager) | One command below | Free |
| OpenOutreach | Installed via `uv` | Free (open source) |
| BetterContact account | bettercontact.rocks | Free (40 credits, no card) |
| Anthropic API key | console.anthropic.com | Free ($5 credit on signup) |
| A sending Gmail | gmail.com | Free |

---

## Step 1 — Get Your Generated Files

In Claude, say:

```
Run the B2B outreach framework for https://yourcompany.com
```

Claude generates all 8 files in the chat. You need **two of them** for
OpenOutreach to find leads:

- `product.md` — what your company sells
- `target.md` — who you're targeting

Copy each file's content and save them locally:

```bash
mkdir -p ~/outreach/my-company
cd ~/outreach/my-company

# Create product.md — paste the content Claude gave you
nano product.md

# Create target.md — paste the content Claude gave you
nano target.md
```

Or if you prefer a code editor:
```bash
code ~/outreach/my-company    # VS Code
```

---

## Step 2 — Install OpenOutreach

```bash
# Install uv (Python package manager — one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart your terminal, then install OpenOutreach
uv tool install openoutreach

# Verify it works
openoutreach --help
```

---

## Step 3 — Get Your API Keys (Free)

### A. BetterContact (finds email addresses)
1. Go to **bettercontact.rocks** and sign up free
2. You get 40 credits — each credit = one verified work email
3. Searching for people is free (unlimited) — you only spend a credit when
   OpenOutreach buys a verified email address
4. Copy your API key from the dashboard

### B. Anthropic API (the AI brain inside OpenOutreach)
1. Go to **console.anthropic.com** — this is separate from claude.ai
2. Sign up (takes 2 minutes)
3. You get **$5 free credit** — enough for 150–500 leads
4. Go to API Keys → Create Key → copy it

> **Want $0 instead?** Use Hermes locally — see [AGENTS.md](./AGENTS.md)
> for the Ollama setup. Skip the Anthropic API key entirely.

### C. Sending Gmail (sends your cold emails)
1. Create a **dedicated Gmail** for outreach — e.g. `yourname-outreach@gmail.com`
   Do NOT use your main inbox
2. Enable 2-Factor Authentication on that Gmail
3. Go to **Google Account → Security → App Passwords**
4. Create an app password called "OpenOutreach"
5. Copy the 16-character password it gives you

---

## Step 4 — Run OpenOutreach Setup

```bash
cd ~/outreach/my-company

openoutreach init \
  --product-docs product.md \
  --target target.md
```

The wizard asks for:
- Your Anthropic API key (or OpenAI-compatible endpoint)
- Your BetterContact API key
- Your Gmail address
- Your Gmail app password (the 16-character one, not your login password)

It saves everything to `~/.openoutreach` — you only do this once.

---

## Step 5 — Find Your First Leads (Free Test)

This searches for leads matching your ICP but spends no credits:

```bash
openoutreach find 10
```

You'll see a list of people with their name, company, title, and a
`reason` column explaining why the AI thinks they're a fit.

If the leads look wrong, go back to Claude and say:
```
The leads from target.md are coming back as [describe the problem].
Please refine the target.md to be more specific about [what's wrong].
```

Then update your `target.md` and re-run.

---

## Step 6 — Find Leads With Email Addresses

Once the leads look right, fetch verified email addresses.
Each email costs 1 BetterContact credit:

```bash
# Find 10 leads with verified emails — saves to a CSV
openoutreach find 10 emails > leads-batch1.csv

# View what you got
cat leads-batch1.csv
```

The CSV columns are:
```
email, first_name, last_name, company, title, website, linkedin_url, reason, lead_id
```

The `reason` column is important — it tells you exactly why each person
was picked. Read it before sending anything.

---

## Step 7 — Send Cold Emails

OpenOutreach writes and sends the email from your Gmail:

```bash
# Find 50 leads and email them automatically
openoutreach run 50
```

Or find first, review, then send:

```bash
# Step 1: Find only (no sending)
openoutreach find 50 emails > leads.csv

# Step 2: Review leads.csv — remove anyone who doesn't look right

# Step 3: Send to what's stored
openoutreach send
```

OpenOutreach handles:
- Writing a personalised email per lead (based on your product.md)
- Sending within safe daily limits (won't trigger spam filters)
- Pacing sends across the day

---

## Step 8 — Track Replies in HubSpot (Free)

1. Sign up at **hubspot.com** — free CRM, no card needed
2. Create a pipeline called "Outreach Sprint"
3. Stages: `Contacted → Replied → Call Booked → Proposal Sent → Closed`
4. When someone replies to your email, add them as a contact and move
   them to the right stage
5. Book calls via **Calendly** (calendly.com — free tier)

---

## Step 9 — Scale Up

Once you've confirmed the leads and emails are working:

```bash
# Run 150 leads across the full 6-week sprint
openoutreach run 150
```

Use the `week-by-week.md` file Claude generated to guide your daily actions.

---

## Quick Reference — All Commands

```bash
openoutreach init                        # First-time setup (run once)
openoutreach find 10                     # Find leads — no credits spent
openoutreach find 50 emails > leads.csv  # Find leads with emails (uses credits)
openoutreach send                        # Send to all stored leads
openoutreach run 50                      # Find + email in one command
openoutreach status                      # See what's configured and how many leads found
```

---

## Troubleshooting

**"Leads don't match my ICP"**
→ Go back to Claude, paste your `target.md`, describe what's wrong,
  ask Claude to refine it, then re-run `openoutreach init --target target.md`

**"Open rate is under 20%"**
→ Your subject lines or sending domain may be flagged. Check email-guide.md
  for subject line rules. Make sure you're using a dedicated Gmail.

**"No one is replying"**
→ Check email-sequences.md — the emails Claude generated should be under
  120 words, personalised, and end with a soft CTA. If they read like
  templates, ask Claude to rewrite them with more specificity.

**"I've run out of BetterContact credits"**
→ Top up at bettercontact.rocks — paid plans start at a low per-credit rate.
  Or supplement with Apollo.io free tier (50 verified emails/month free).

**"I want to use Hermes instead of the Anthropic API"**
→ See [AGENTS.md](./AGENTS.md) — full Ollama + Hermes setup guide.
