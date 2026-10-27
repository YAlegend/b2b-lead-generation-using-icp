# b2b-outreach skill

One folder that works as a skill in Claude, OpenAI Codex, Hermes Agent and
any other agent that reads the open `SKILL.md` format. Give it a company URL
or description and it produces:

- 8 outreach files: `product.md`, `target.md`, `positioning.md`,
  `email-sequences.md`, `linkedin.md`, `discovery-call.md`,
  `proposal-template.md`, `week-by-week.md`
- `leads.csv`: real people found on the public web, each with a source link,
  a buying signal and an email marked `published`, `pattern-confirmed` or
  `guess`
- `outreach-drafts.md`: a personalised first email for every lead
- A built-in improve loop: checks the files before anything is used, scores
  every lead against your ICP, and after you've sent ~20 emails reviews the
  replies and rewrites the emails or targeting that aren't working. What it
  learns is kept in `learnings.md` so the next run starts smarter.

**No API keys.** The agent you're already using writes the files and does the
web research itself. No Groq/OpenAI/Anthropic API key, no Apollo, PDL, Hunter
or BetterContact. You send the emails yourself from your own inbox.

The trade-off: you get 10–30 carefully researched leads per run instead of
hundreds of unverified ones from a paid database.

## Install

From the repo root:

| Agent | Command | Then say |
|---|---|---|
| Claude Code | `bash skills/install.sh claude` | "Set up outreach for https://acme.com" |
| OpenAI Codex CLI | `bash skills/install.sh codex` | same, or `$b2b-outreach https://acme.com` |
| Hermes Agent | `bash skills/install.sh hermes` | same, or `/b2b-outreach https://acme.com` |
| All of the above | `bash skills/install.sh all` | |

Restart the agent after installing so it picks the skill up.

### Claude.ai / Claude desktop app

1. `bash skills/install.sh zip` → creates `skills/b2b-outreach.zip`
2. Claude → Settings → Capabilities → Skills → Upload skill → pick the zip
3. Make sure web search is on, then paste a company URL.

### ChatGPT (no skill support)

Create a Project (or a custom GPT), upload `SKILL.md` and every file in
`references/` as files, and put this in the instructions:

> Follow SKILL.md exactly for any outreach, lead generation or cold email
> request. Read the reference files it names before writing each output.

Turn on web search for the lead-finding step.

### Cursor, Windsurf, Gemini CLI, Ollama / Open WebUI, anything else

Point the agent at the folder: "Read `skills/b2b-outreach/SKILL.md` and follow
it for https://acme.com". Agents without web access will ask you to paste the
website text and to run the lead searches yourself — it still works, just
with you doing the browsing.

## Folder layout

```
b2b-outreach/
├── SKILL.md                  workflow the agent follows
├── references/
│   ├── lead-research.md      search patterns, email rules, compliance
│   ├── improve-loop.md       quality gate, lead scoring, results review
│   ├── product-template.md   structure for product.md
│   ├── target-template.md    structure for target.md
│   ├── positioning-guide.md
│   ├── email-guide.md        word limits + tone by industry
│   ├── discovery-guide.md
│   ├── proposal-guide.md
│   └── kpi-guide.md          weekly targets + funnel math
└── scripts/
    └── check_files.py        word limits, placeholders, leads.csv (optional, stdlib Python)
```

Edit the files here, then re-run `install.sh` to update installed copies.
