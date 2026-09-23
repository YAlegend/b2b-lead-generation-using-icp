# Security

## What Is Stored and Where

| Data | Where | Shared? |
|------|-------|---------|
| API keys | `.env` file on your computer | Never — local only |
| Gmail app password | `.env` file on your computer | Never — local only |
| Company files | `your-slug/` folder | Only if you share the folder |
| Lead CSVs | `your-slug/leads*.csv` | Never committed to GitHub |
| Reply logs | `your-slug/replies_log.json` | Never committed to GitHub |
| Campaign state | `your-slug/.loop_state.json` | Never committed to GitHub |

## What `.gitignore` Blocks

The `.gitignore` file prevents these from ever being committed:
- `.env` (your credentials)
- `*.csv` files (lead data)
- `replies_log.json` (email content)
- `.loop_state.json` (campaign metrics)

**Check before pushing:** Run `git status` and confirm none of the above appear.

## Your Gmail

We use an **App Password** — not your real Gmail password.

- An App Password is a separate 16-character code
- It only works for the specific app you created it for
- You can revoke it anytime at myaccount.google.com/apppasswords
- Even if someone found it, they cannot access your full Gmail account

**Always use a dedicated outreach Gmail** — not your main inbox.
This protects your personal email reputation from spam filters.

## API Keys

- Stored in `.env` on your computer only
- Never logged, never printed to screen after entry
- Never sent to GitHub (blocked by `.gitignore`)
- If you accidentally expose a key: revoke it immediately
  - Anthropic: console.anthropic.com → API Keys → Delete
  - OpenAI: platform.openai.com → API Keys → Delete
  - BetterContact: dashboard → API Keys → Revoke

## BetterContact Data

BetterContact is a licensed B2B data provider.
The leads it returns are business contact data — no personal/private data.
Review their privacy policy at bettercontact.rocks/privacy.

## Cold Email Compliance

You are responsible for complying with:
- **GDPR** (if emailing EU contacts): include unsubscribe link
- **CAN-SPAM** (if emailing US contacts): include physical address + unsubscribe
- **CASL** (if emailing Canadian contacts): requires implied or express consent

OpenOutreach handles unsubscribe requests automatically.
For GDPR compliance, add a one-line unsubscribe footer to your emails.

## Reporting Security Issues

If you find a security issue in this framework, please open a private
GitHub security advisory rather than a public issue.
