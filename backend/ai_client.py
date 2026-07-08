"""Optional real-LLM client (Python stdlib only, via urllib).

Enables a genuine conversational AI mode when an API key is configured.
Provider-agnostic — configured entirely through environment variables:

    MYDOCPLUS_AI_KEY       API key (REQUIRED to enable real AI mode)
    MYDOCPLUS_AI_PROVIDER  gemini (default) | openai | groq
    MYDOCPLUS_AI_MODEL     model name (provider-specific default if unset)

If no key is set, `is_enabled()` returns False and callers transparently fall
back to the built-in rule-based assistant. No third-party packages required.
"""
import json
import os
import urllib.error
import urllib.request

PROVIDER = os.environ.get("MYDOCPLUS_AI_PROVIDER", "gemini").lower()
API_KEY = os.environ.get("MYDOCPLUS_AI_KEY", "").strip()
MODEL = os.environ.get("MYDOCPLUS_AI_MODEL", "").strip()
TIMEOUT = 30

DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
}


def is_enabled():
    """True when a real LLM can be called."""
    return bool(API_KEY)


def _post(url, payload, headers):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def chat(messages, system=None):
    """Send a conversation and return the assistant's reply text.

    messages: [{"role": "user"|"assistant", "content": str}, ...]
    """
    if not API_KEY:
        raise RuntimeError("AI not configured (set MYDOCPLUS_AI_KEY)")
    if PROVIDER == "gemini":
        return _gemini(messages, system)
    if PROVIDER in ("openai", "groq"):
        return _openai_compatible(messages, system)
    raise RuntimeError(f"Unknown AI provider: {PROVIDER}")


def _model():
    return MODEL or DEFAULT_MODELS.get(PROVIDER, "")


def _gemini(messages, system):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{_model()}:generateContent?key={API_KEY}"
    )
    contents = [
        {"role": "user" if m["role"] == "user" else "model",
         "parts": [{"text": m["content"]}]}
        for m in messages
    ]
    payload = {"contents": contents}
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    data = _post(url, payload, {"Content-Type": "application/json"})
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _openai_compatible(messages, system):
    base = "https://api.groq.com/openai/v1" if PROVIDER == "groq" else "https://api.openai.com/v1"
    msgs = ([{"role": "system", "content": system}] if system else [])
    msgs += [
        {"role": "assistant" if m["role"] == "assistant" else "user", "content": m["content"]}
        for m in messages
    ]
    payload = {"model": _model(), "messages": msgs, "temperature": 0.5}
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    data = _post(f"{base}/chat/completions", payload, headers)
    return data["choices"][0]["message"]["content"].strip()
