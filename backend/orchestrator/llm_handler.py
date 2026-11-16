"""LLM provider layer for AgentFlow (target-column choice).

Switch provider with environment variables; no code change needed:
  AGENTFLOW_LLM            none (default) | ollama | gemini
  AGENTFLOW_OLLAMA_URL     default http://localhost:11434
  AGENTFLOW_OLLAMA_MODEL   default llama3.2:3b
  AGENTFLOW_GEMINI_MODEL   default gemini-2.0-flash   (also needs GOOGLE_API_KEY)
  AGENTFLOW_LLM_TIMEOUT    seconds, default 90

Standard library only, so there is nothing extra to install.
Privacy: only column names, types, counts and up to 3 example values per shortlisted
column are sent. With Ollama nothing leaves your machine.
"""
import json
import os
import re
import time
import urllib.request

TIMEOUT_S = int(os.getenv("AGENTFLOW_LLM_TIMEOUT", "90"))


def provider_name():
    return os.getenv("AGENTFLOW_LLM", "none").strip().lower()


def model_name():
    p = provider_name()
    if p == "ollama":
        return os.getenv("AGENTFLOW_OLLAMA_MODEL", "llama3.2:3b")
    if p == "gemini":
        return os.getenv("AGENTFLOW_GEMINI_MODEL", "gemini-2.0-flash")
    return ""


def llm_enabled():
    return provider_name() in ("ollama", "gemini")


def _post_json(url, payload, headers=None):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _generate(prompt):
    p = provider_name()
    if p == "ollama":
        base = os.getenv("AGENTFLOW_OLLAMA_URL", "http://localhost:11434").rstrip("/")
        data = _post_json(f"{base}/api/chat", {
            "model": model_name(), "stream": False, "format": "json",
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}],
        })
        return data["message"]["content"]
    if p == "gemini":
        key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model_name()}:generateContent")
        data = _post_json(url, {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }, headers={"x-goog-api-key": key})
        return data["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("No LLM provider configured")


def _parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("The model did not return JSON")
        return json.loads(m.group(0))


def build_prompt(statement, columns):
    lines = [f"- {c['name']} | {c['kind']} | {c['unique']} distinct values | "
             f"examples: {', '.join(c['samples'])}" for c in columns]
    return (
        "You help choose the TARGET column for a machine-learning task: the column the "
        "user wants to predict.\n\n"
        f"Problem statement: {statement}\n\n"
        "Candidate columns (name | type | distinct values | examples):\n"
        + "\n".join(lines) + "\n\n"
        "Rules:\n"
        "- Choose exactly ONE column from the candidate list above.\n"
        "- Never invent a column name.\n"
        "- The target is the outcome the user wants to predict, not an input that "
        "describes the case.\n"
        'Reply with JSON only: {"recommended": "<column>", "alternatives": ["<column>"], '
        '"reason": "<one short sentence>", "confidence": <number from 0 to 1>}'
    )


def ask_for_target(statement, columns):
    t0 = time.time()
    out = _parse_json(_generate(build_prompt(statement, columns)))
    out["latency_s"] = round(time.time() - t0, 1)
    return out