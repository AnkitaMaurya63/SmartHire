"""Tiny LLM client for Groq and Gemini (both expose an OpenAI-compatible chat endpoint).

Set GROQ_API_KEY or GEMINI_API_KEY in a .env file. Without a key, SmartHire still works:
agents fall back to rule-based behaviour and the UI says so.
"""
import json
import os
import re

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

PROVIDERS = {
    "groq": {"env": "GROQ_API_KEY", "base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"},
    "gemini": {"env": "GEMINI_API_KEY", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "model": "gemini-2.5-flash"},
}


class LLMError(RuntimeError):
    pass


def _provider():
    pref = os.getenv("LLM_PROVIDER", "").lower()
    order = [pref] if pref in PROVIDERS else list(PROVIDERS)
    for name in order:
        key = os.getenv(PROVIDERS[name]["env"])
        if key:
            return name, key
    return None, None


def is_enabled() -> bool:
    return _provider()[0] is not None


def info():
    name, _ = _provider()
    if not name:
        return None
    return {"provider": name, "model": os.getenv("LLM_MODEL") or PROVIDERS[name]["model"]}


def chat(system: str, user: str, json_mode: bool = False, temperature: float = 0.3, max_tokens: int = 1500) -> str:
    name, key = _provider()
    if not name:
        raise LLMError("No LLM API key configured")
    cfg = PROVIDERS[name]
    body = {"model": os.getenv("LLM_MODEL") or cfg["model"], "temperature": temperature, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode and name == "groq":
        body["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(f"{cfg['base']}/chat/completions", headers={"Authorization": f"Bearer {key}"},
                          json=body, timeout=45)
    except requests.RequestException as exc:
        raise LLMError(f"Could not reach {name}: {exc}") from exc
    if r.status_code != 200:
        raise LLMError(f"{name} API error {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError("Unexpected response from the LLM API") from exc


def chat_json(system: str, user: str, **kw):
    """Ask for JSON and parse it robustly (handles code fences and extra prose)."""
    text = chat(system, user, json_mode=True, **kw).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}|\[.*\]", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("The LLM did not return valid JSON")
