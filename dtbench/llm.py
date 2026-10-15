"""Minimal client for OpenAI-compatible chat endpoints (llama.cpp llama-server, Groq, OpenAI ...).

For the experiment in the paper, models run locally with llama.cpp's ``llama-server``
(greedy decoding, temperature 0, fixed seed) and JSON-schema-constrained decoding.
"""
import json
import os
import time
import urllib.request


class LLMClient:
    def __init__(self, base_url="http://127.0.0.1:8080/v1", model="local", api_key=None, timeout=1800):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.timeout = timeout

    def chat(self, messages, schema=None, max_tokens=2500, temperature=0.0, seed=42, grammar=None):
        body = {"model": self.model, "messages": messages, "temperature": temperature,
                "max_tokens": max_tokens, "seed": seed}
        if grammar is not None:                 # explicit GBNF (llama.cpp servers only)
            body["grammar"] = grammar
        elif schema is not None:
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "answer", "schema": schema, "strict": True}}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url + "/chat/completions", data=data,
                                     headers={"Content-Type": "application/json",
                                              **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        choice = out["choices"][0]
        return {
            "text": choice["message"].get("content") or "",
            "finish_reason": choice.get("finish_reason"),
            "usage": out.get("usage", {}),
            "timings": out.get("timings", {}),
            "seconds": round(elapsed, 2),
        }


def parse_json(text):
    """Parse a JSON object from model text (tolerates code fences / leading prose)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    try:
        return json.loads(t), None
    except Exception:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(t[start:end + 1]), None
        except Exception as exc:
            return None, f"invalid JSON: {exc}"
    return None, "no JSON object found"
