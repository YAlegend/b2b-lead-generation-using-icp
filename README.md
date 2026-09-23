# B2B Outreach Framework

> Give it a company URL. It finds leads and emails them.

No paid subscriptions required. Works with Claude, ChatGPT, Gemini,
or a free local AI. Self-improving — gets better with every campaign.

---

## Start Here

### Windows
Double-click **`START_WINDOWS.bat`**

### Mac
Double-click **`START_MAC.command`**
> First time: right-click → Open (Mac security step, once only)

### Linux
```bash
bash start_linux.sh
```

That's it. The wizard guides you through everything.

---

## What It Does

```
You give it →  company URL  or  a description
                       ↓
          Reads your website
                       ↓
          AI writes your outreach files
                       ↓
          Quality gate checks everything
                       ↓
          Finds matching leads (free test first)
                       ↓
          Sends personalised cold emails
                       ↓
          Monitors replies — improves itself
```

---

## What You Need

| Thing | Where to get it | Cost |
|-------|----------------|------|
| Company website or description | You have this | Free |
| BetterContact account | bettercontact.rocks | Free (40 emails, no card) |
| A dedicated Gmail | gmail.com | Free |
| AI (pick one below) | See options | Free |

### AI Options (all free)

| Option | Cost | How |
|--------|------|-----|
| Ollama + Hermes | Free forever | Runs on your computer — wizard installs it |
| Claude.ai | Free if subscribed | Paste URL into Claude, save the files |
| Anthropic API | Free $5 credit | console.anthropic.com — no card needed |
| OpenAI API | Free $5 credit | platform.openai.com — no card needed |

The wizard asks you to pick one and sets it up automatically.

---

## After Setup — Commands

```bash
# Find 10 leads (free, no email credits used)
openoutreach find 10

# Find 50 leads with verified emails
openoutreach find 50 emails > my-company/leads.csv

# Find + email automatically
openoutreach run 50

# Self-improving watch mode (checks replies every 24h)
python improver.py --slug my-company --mode watch

# Fully autonomous (no prompts, runs forever)
python improver.py --slug my-company --mode auto
```

---

## The Self-Improving Loop

After sending, the framework monitors replies and improves itself:

- **Reply rate < 3%?** → rewrites your email sequence
- **>30% wrong-person replies?** → tightens your target ICP
- **Files not specific enough?** → rewrites before anything sends

Every change shows you a diff and asks approval — or runs fully
autonomously in `--mode auto`.

---

## Connecting to Your LLM App

Use the framework from Claude Desktop, Cursor, Windsurf, VS Code, or Zed:

```bash
python mcp_server.py        # Claude Desktop, Cursor, Windsurf, VS Code, Zed
python mcp_server.py --http # ChatGPT, Gemini (via browser)
```

Config files for each app are in `mcp_configs/`.
See [MCP.md](./MCP.md) for setup instructions.

---

## Security

- Your credentials stay on your computer only
- `.env` is blocked from GitHub by `.gitignore`
- Lead data and reply logs are never committed
- Gmail uses an App Password, not your real password
- Full details in [SECURITY.md](./SECURITY.md)

---

## Files Generated Per Company

```
my-company/
├── product.md          ← What you sell (OpenOutreach input)
├── target.md           ← Who to target (ICP definition)
├── positioning.md      ← 1-sentence statement + variants
├── email-sequences.md  ← Cold email sequence per vertical
├── linkedin.md         ← Headlines + thought leadership posts
├── discovery-call.md   ← 30-min call script
├── proposal-template.md← Scoped proposal
└── week-by-week.md     ← 6-week execution plan
```

---

## License

MIT — use freely, commercially or otherwise.
OpenOutreach is GPLv3 — fine for personal and business use.

## Contributing

Pull requests welcome. Add your company under `examples/` once you've run it.
See [SECURITY.md](./SECURITY.md) for reporting security issues.
