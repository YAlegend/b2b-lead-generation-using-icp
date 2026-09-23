"""
Multi-provider LLM calling for the web app.

Each provider is called with an explicit API key from the request (or the
server's own key for the free default provider) — nothing is read from a
local .env file here, since the web app is multi-tenant.
"""

import os
import requests

# label, needs_key, default_model, help_url
PROVIDERS = {
    "groq": {
        "label": "Groq (free, fast)",
        "needs_key": False,
        "default_model": "llama-3.3-70b-versatile",
        "help_url": "https://console.groq.com/keys",
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "needs_key": True,
        "default_model": "claude-sonnet-5",
        "help_url": "https://console.anthropic.com",
    },
    "openai": {
        "label": "OpenAI",
        "needs_key": True,
        "default_model": "gpt-4o-mini",
        "help_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "label": "Google Gemini",
        "needs_key": True,
        "default_model": "gemini-2.0-flash",
        "help_url": "https://aistudio.google.com/apikey",
    },
    "openrouter": {
        "label": "OpenRouter",
        "needs_key": True,
        "default_model": "nousresearch/hermes-3-llama-3.1-70b",
        "help_url": "https://openrouter.ai/keys",
    },
    "ollama": {
        "label": "Ollama (local — only works when self-hosting this app)",
        "needs_key": False,
        "default_model": "nous-hermes2",
        "help_url": "https://ollama.ai",
    },
}


class LLMError(RuntimeError):
    pass


def _chat_completions(base_url: str, api_key: str, model: str,
                       system: str, prompt: str) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint."""
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
        },
        timeout=120,
    )
    if resp.status_code >= 400:
        raise LLMError(f"{base_url} returned {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def call_llm(provider: str, api_key: str, prompt: str, system: str,
             model: str = "") -> str:
    """Call the chosen provider and return the generated text."""
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown provider: {provider}")

    cfg = PROVIDERS[provider]
    model = model or cfg["default_model"]

    if cfg["needs_key"] and not api_key:
        raise LLMError(f"{cfg['label']} requires an API key.")

    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise LLMError("Server has no GROQ_API_KEY configured and none was provided.")
        return _chat_completions("https://api.groq.com/openai/v1", key, model, system, prompt)

    if provider == "openai":
        return _chat_completions("https://api.openai.com/v1", api_key, model, system, prompt)

    if provider == "openrouter":
        return _chat_completions("https://openrouter.ai/api/v1", api_key, model, system, prompt)

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return _chat_completions(base_url, "ollama", model, system, prompt)

    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc
        return msg.content[0].text

    if provider == "gemini":
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        resp = requests.post(
            url,
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"maxOutputTokens": 4096},
            },
            timeout=120,
        )
        if resp.status_code >= 400:
            raise LLMError(f"Gemini returned {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected Gemini response: {data}") from exc

    raise LLMError(f"Provider not implemented: {provider}")
