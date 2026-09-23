# MCP Config Files

Pick the file for your LLM tool. Edit two things in each:
- Replace `PATH_TO_REPO` with the full path to where you cloned this repo
- Replace `YOUR_KEY_HERE` with your LLM API key (or see LLM options below)

---

## Desktop Apps (work today, local only)

| File | Tool | Install |
|------|------|---------|
| `claude_desktop.json` | Claude Desktop | claude.ai/download |
| `cursor.json` | Cursor | cursor.sh |
| `windsurf.json` | Windsurf | windsurf.com |
| `vscode_continue.json` | VS Code + Continue | marketplace.visualstudio.com |
| `zed.json` | Zed | zed.dev |
| `hermes_agent.json` | Hermes Agent (local, free) | ollama.ai + github.com/nousresearch/hermes-agent |

## Web LLMs (need HTTP server + public URL)

| File | Tool | Extra step |
|------|------|-----------|
| `http_mode.json` | ChatGPT, Gemini, any web LLM | Run server + ngrok to get public URL |

---

## Where to put the config file

### Claude Desktop
```bash
# Mac
cp claude_desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
copy claude_desktop.json %APPDATA%\Claude\claude_desktop_config.json

# Linux
cp claude_desktop.json ~/.config/Claude/claude_desktop_config.json
```
Restart Claude Desktop. Then say: **"Generate leads for https://yourcompany.com"**

---

### Cursor
```bash
# In your project root
mkdir -p .cursor
cp cursor.json .cursor/mcp.json
```
Restart Cursor. Then say it in chat.

---

### Windsurf
```bash
cp windsurf.json ~/.codeium/windsurf/mcp_config.json
```
Restart Windsurf.

---

### VS Code + Continue
```bash
# In your project root
mkdir -p .vscode
cp vscode_continue.json .vscode/mcp.json
```

---

### Zed
```bash
# Add to your Zed settings.json
# Settings → Open Settings JSON → merge in the contents of zed.json
```

---

### Hermes Agent (local, no API cost)
```bash
# 1. Install Ollama and pull a model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull nous-hermes2

# 2. Start the MCP server using local Hermes
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
OPENAI_MODEL=nous-hermes2 \
python3 ../mcp_server.py

# 3. In Hermes Agent, say:
#    "Generate leads for https://yourcompany.com"
```

---

## LLM API Key Options

Set one of these as your env variable in the config file:

| Provider | Variable | Free tier | Model used |
|----------|---------|-----------|-----------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | $5 credit | claude-sonnet-4-6 |
| OpenAI | `OPENAI_API_KEY` | $5 credit | gpt-4o-mini |
| Hermes (Ollama) | `OPENAI_API_KEY=ollama` + `OPENAI_BASE_URL` | Free (local) | nous-hermes2 |
| OpenRouter | `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://openrouter.ai/api/v1` | Pay per use | any model |
| Gemini | `GEMINI_API_KEY` | Free tier | gemini-1.5-flash |

You can also just run `setup.sh` first — it asks you to pick and saves to `.env`.
