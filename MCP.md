# Connecting Any LLM to This Framework

> Clone the repo, point your LLM at it, and say:
> **"Generate leads for https://yourcompany.com"**
> — that's it.

This framework runs as an MCP (Model Context Protocol) server.
Any LLM that supports MCP tools can call it directly.

---

## What the LLM Gets

Four tools it can call in sequence:

| Tool | What it does |
|------|-------------|
| `configure_llm` | Set which LLM generates the files (once only) |
| `generate_outreach_files` | Read website → generate product.md + target.md |
| `setup_openoutreach` | Install OpenOutreach + run wizard |
| `find_leads` | Find leads matching the ICP |

The LLM calls these itself — you just describe what you want in plain language.

---

## Option A — Claude Desktop

1. Clone the repo:
   ```bash
   git clone https://github.com/YOUR_USERNAME/b2b-outreach-framework
   cd b2b-outreach-framework
   pip install -r requirements.txt
   ```

2. Edit `mcp_configs/claude_desktop.json`:
   - Replace `/absolute/path/to/b2b-outreach-framework/` with your actual path
   - Add your API key (Anthropic, OpenAI, Gemini, or leave blank for Ollama)

3. Copy config to Claude Desktop:
   ```bash
   # Mac
   cp mcp_configs/claude_desktop.json \
     ~/Library/Application\ Support/Claude/claude_desktop_config.json

   # Windows
   copy mcp_configs\claude_desktop.json %APPDATA%\Claude\claude_desktop_config.json
   ```

4. Restart Claude Desktop. Then just say:
   ```
   Generate leads for https://yourcompany.com
   ```

---

## Option B — Cursor

1. Clone the repo into your project:
   ```bash
   git clone https://github.com/YOUR_USERNAME/b2b-outreach-framework
   pip install -r b2b-outreach-framework/requirements.txt
   ```

2. Copy the Cursor config:
   ```bash
   mkdir -p .cursor
   cp b2b-outreach-framework/mcp_configs/cursor.json .cursor/mcp.json
   ```

3. Edit `.cursor/mcp.json` — update the path and add your API key.

4. Restart Cursor. In the chat, say:
   ```
   Generate leads for https://yourcompany.com
   ```

---

## Option C — ChatGPT / OpenAI

ChatGPT connects over HTTP, not stdio.

1. Start the HTTP server:
   ```bash
   OPENAI_API_KEY=your-key python3 mcp_server.py --http
   # Server starts at http://localhost:8000
   ```

2. In ChatGPT → Settings → Tools → Add custom tool:
   - URL: `http://localhost:8000`

3. In the chat, say:
   ```
   Use the b2b-outreach-framework tool to generate leads for https://yourcompany.com
   ```

---

## Option D — Gemini

Same as ChatGPT — HTTP mode:

1. Start server:
   ```bash
   GEMINI_API_KEY=your-key python3 mcp_server.py --http
   ```

2. In Gemini Advanced → Extensions → Add tool: `http://localhost:8000`

3. Say:
   ```
   Generate B2B leads for https://yourcompany.com
   ```

---

## Option E — VS Code (GitHub Copilot / Continue)

1. Install the MCP extension for VS Code
2. Add to `.vscode/settings.json`:
   ```json
   {
     "mcp.servers": {
       "b2b-outreach-framework": {
         "command": "python3",
         "args": ["./mcp_server.py"]
       }
     }
   }
   ```
3. Use it in Copilot Chat or Continue.

---

## Option F — Hermes Agent (fully local, $0)

```bash
# Start Ollama with Hermes
ollama pull nous-hermes2
ollama serve

# Start the MCP server pointing at local Hermes
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=nous-hermes2 \
python3 mcp_server.py

# Run Hermes Agent
hermes run "Generate leads for https://yourcompany.com using the b2b-outreach-framework MCP"
```

Zero API cost. Everything runs on your machine.

---

## LLM Configuration

The first time you use the framework, configure your LLM using the
`configure_llm` tool, or set environment variables:

| Provider | Environment variable | Example |
|----------|---------------------|---------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | `sk-ant-...` |
| OpenAI (ChatGPT) | `OPENAI_API_KEY` | `sk-...` |
| Gemini | `GEMINI_API_KEY` | `AIza...` |
| OpenRouter | `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://openrouter.ai/api/v1` | any key |
| Ollama / Hermes | `OPENAI_API_KEY=ollama` + `OPENAI_BASE_URL=http://localhost:11434/v1` | — |
| Any OpenAI-compatible | `OPENAI_API_KEY` + `OPENAI_BASE_URL` | — |

All values are saved to `.env` after first use — you only configure once.

---

## What the LLM Says (Example Conversation)

```
You:    Generate leads for https://acme-consulting.com

LLM:    I'll use the B2B Outreach Framework to do that.
        [calls generate_outreach_files(url="https://acme-consulting.com")]

        ✓ I've read the website. Acme Consulting offers strategy consulting
          for mid-market SaaS companies. I've generated:
          • acme-consulting/product.md
          • acme-consulting/target.md

        [calls setup_openoutreach(slug="acme-consulting")]

        ✓ OpenOutreach is ready. You need to run this once in your terminal
          to add your BetterContact key and Gmail:
          openoutreach init --product-docs acme-consulting/product.md \
                            --target acme-consulting/target.md

You:    Done

LLM:    [calls find_leads(slug="acme-consulting", count=10)]

        ✓ Found 10 leads matching your ICP:
          - Sarah Chen, VP Strategy, Intercom (Series D SaaS)
          - James Park, COO, Loom (mid-market)
          ...

        To find 50 leads and email them:
          openoutreach run 50
```

---

## Troubleshooting

**"Tool not found" in Claude Desktop**
→ Check the path in `claude_desktop_config.json` is the absolute path
  to `mcp_server.py`. Restart Claude Desktop after editing.

**"Connection refused" for HTTP mode**
→ Make sure the server is running (`python3 mcp_server.py --http`)
  and your firewall allows port 8000.

**"No LLM configured"**
→ Set an environment variable or call `configure_llm()` first.

**OpenOutreach wizard doesn't appear**
→ The wizard runs in your terminal, not inside the LLM chat.
  Run `openoutreach init` directly in your terminal after `setup_openoutreach()`.
