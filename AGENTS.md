# Agent & LLM Compatibility Guide

This framework works with any LLM or agent that can read markdown and call
a web browser. This file explains how to use it with each major option.

---

## Compatibility Matrix

| Tool | Generates .md files | Runs OpenOutreach LLM | Cost |
|------|--------------------|-----------------------|------|
| Claude (claude.ai) | ✅ Paste SKILL.md prompts | ❌ Separate Anthropic API | Subscription |
| Claude Code | ✅ Native skill install | ❌ Separate Anthropic API | Subscription |
| Hermes Agent | ✅ Read SKILL.md as task | ✅ Use Hermes locally | Free |
| Cursor / Windsurf | ✅ Add as project rule | ❌ Separate API | IDE subscription |
| OpenAI / GPT-4 | ✅ Paste prompts | ✅ OpenAI API key | API cost |
| Ollama (local) | ✅ Via Open WebUI | ✅ Local = $0 | Free |
| Any OpenAI-compatible | ✅ Via prompts | ✅ Point at endpoint | Varies |

---

## Option 1 — Claude (Recommended)

### Claude.ai (web/app — no install needed)

Paste this into any Claude conversation:

```
I want to generate a complete B2B outreach system.
Company URL: [URL]
Additional context: [optional]

Please follow the B2B Outreach Framework:
1. Fetch the company website and extract their product, ICP, and positioning signals
2. Generate all 8 files: product.md, target.md, positioning.md,
   email-sequences.md, linkedin.md, discovery-call.md,
   proposal-template.md, and week-by-week.md
3. Make every file fully populated — no placeholders
```

### Claude Code (skill install)

```bash
mkdir -p ~/.claude/skills/b2b-outreach-framework
cp SKILL.md ~/.claude/skills/b2b-outreach-framework/SKILL.md
cp -r framework/ ~/.claude/skills/b2b-outreach-framework/
cp -r openoutreach/ ~/.claude/skills/b2b-outreach-framework/
```

Then just say in Claude Code:
```
Run the B2B outreach framework for https://yourcompany.com
```

---

## Option 2 — Hermes Agent (Fully Free, Fully Local)

Hermes Agent is an open-source autonomous agent framework by Nous Research.
Model-agnostic — works with Hermes, Claude, GPT-4, or any OpenAI-compatible endpoint.

### Install Hermes Agent

```bash
# Install Ollama (local LLM runtime)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull Hermes model (pick based on your GPU VRAM)
ollama pull nous-hermes2          # 7B — runs on 8GB VRAM
ollama pull hermes3:70b           # 70B — needs 48GB VRAM
# OR use OpenRouter for hosted Hermes (pay per token, no GPU needed)

# Install Hermes Agent
pip install hermes-agent          # or: uv tool install hermes-agent

# OR clone and run
git clone https://github.com/nousresearch/hermes-agent
cd hermes-agent && pip install -e .
```

### Point Hermes Agent at this skill

```bash
# Copy SKILL.md into Hermes Agent's skills folder
cp SKILL.md ~/.hermes/skills/b2b-outreach-framework.md

# Run the framework
hermes run "Generate B2B outreach files for https://yourcompany.com"
```

Hermes Agent reads the SKILL.md instructions, browses the company website,
and generates all 8 files autonomously.

### Use Hermes as the OpenOutreach LLM (free, local inference)

```bash
# Start Ollama (runs in background)
ollama serve

# Set OpenOutreach to use local Hermes instead of Anthropic/OpenAI
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama   # dummy value required by OpenOutreach

# Run OpenOutreach normally — it now uses local Hermes
openoutreach init --product-docs product.md --target target.md
openoutreach find 10 emails > leads.csv
```

No API cost. No data leaves your machine.

### Use Hermes via OpenRouter (if you don't have a GPU)

```bash
# Sign up at openrouter.ai — Hermes 3 70B costs ~$0.30/M tokens
# For 150 leads, total cost ≈ $0.10–0.30

export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=your-openrouter-key
# OpenOutreach works with any OpenAI-compatible endpoint
```

---

## Option 3 — Cursor / Windsurf

Add the SKILL.md as a project rule:

```bash
# In your project root
mkdir -p .cursor/rules
cp SKILL.md .cursor/rules/b2b-outreach-framework.md
```

Then in Cursor chat:
```
@b2b-outreach-framework generate outreach files for https://yourcompany.com
```

---

## Option 4 — Any LLM (Manual Prompts)

If you're using ChatGPT, Gemini, Mistral, or any other LLM:

1. Open `SKILL.md` and copy the **Step 3 — Generate All Files** section
2. Paste it into your LLM with:
   ```
   Company URL: [URL]
   Company description: [optional]
   Please follow these instructions and generate all 8 files.
   ```
3. The LLM follows the same generation logic

The skill is written in plain markdown — it works with any sufficiently capable LLM.

---

## APIs: What's Actually Required

### To generate the .md files
| Need | Required? | Free option |
|------|----------|------------|
| Web browsing (to read company URL) | Recommended | Claude has it built in. Hermes Agent has it. |
| LLM | Yes | Hermes local (free) or Claude (subscription) |
| Any external API | No | Nothing else needed |

### To run OpenOutreach (lead finding + emailing)
| Need | Required? | Free option |
|------|----------|------------|
| LLM API | Yes | Hermes via Ollama ($0) or Anthropic API ($3 free credit) |
| BetterContact API | Yes | Free signup — 40 credits, no card |
| Gmail SMTP | Yes | Free Gmail account + app password |
| Sending tool | No (built in) | OpenOutreach sends natively |

### Total cost to run the full system
| Stack | Cost |
|-------|------|
| Claude.ai + Anthropic API + BetterContact free | ~$3 one-time (API free credit) |
| Hermes local + BetterContact free | **$0** |
| Hermes via OpenRouter + BetterContact free | ~$0.30 for 150 leads |

---

## Recommended Stack for Public Users

**If you have a GPU (8GB+ VRAM):**
```
Hermes Agent (skill runner) + Hermes local (OpenOutreach LLM) + BetterContact free + Gmail
= $0 total
```

**If you don't have a GPU:**
```
Claude.ai (skill runner) + Anthropic API free $5 credit (OpenOutreach LLM) + BetterContact free + Gmail
= $0 for the first sprint
```

**If you want maximum automation:**
```
Hermes Agent + OpenRouter Hermes 70B + BetterContact paid + Instantly.ai
= ~$50/month, fully automated
```
