"""LLM clients and how the terminal chooses one (--provider, --model, .env).

    python app.py --server-key --provider ollama                    # local model (OLLAMA_MODEL, default qwen3:8b)
    python app.py --server-key --provider openai --model gpt-5.4    # OpenAI API
    python -m evaluation.eval_answers --split validation --provider ollama --model llama3:8b

Command-line options win over the environment, which wins over .env.
The provider SDKs are imported only when a client is created, so scripts can call apply_llm_args()
before importing gesetzpolyglot.rag (prompts are chosen at import, see prompts.py).

LLM_PROVIDER         = openai (default) | anthropic | ollama
OPENAI_API_KEY       = for openai
LLM_MODEL            = default gpt-5.4-mini (openai) / claude-sonnet-5-5 (anthropic)
LLM_REASONING_EFFORT = low (default) | none | medium | high ; empty = do not send (openai)
OPENAI_BASE_URL      = only for other OpenAI-compatible servers
OLLAMA_MODEL         = default qwen3:8b (ollama)
OLLAMA_URL           = default http://localhost:11434
OLLAMA_NUM_CTX       = context window in tokens, default 16384 (Ollama's own default is too small)
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Protocol

PROVIDERS = ("openai", "anthropic", "ollama")
# per provider: the environment variable that holds its model name, and the default model
MODEL_VAR = {"openai": ("LLM_MODEL", "gpt-5.4-mini"),
             "anthropic": ("LLM_MODEL", "claude-sonnet-5-5"),
             "ollama": ("OLLAMA_MODEL", "qwen3:8b")}


def load_dotenv(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env (in the project root) into os.environ.
    Variables already set in the shell win. No extra dependency needed."""
    path = path or Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.removeprefix("export ").split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key.strip(), val)


def add_llm_args(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("LLM")
    g.add_argument("--provider", choices=PROVIDERS, help="overrides LLM_PROVIDER: openai (API), anthropic (API) "
                                                        "or ollama (local)")
    g.add_argument("--model", help="model for the chosen provider, e.g. gpt-5.4-mini or qwen3:8b")


def apply_llm_args(args: argparse.Namespace) -> None:
    """Put --provider / --model into the environment, where llm_from_env() reads them."""
    load_dotenv()
    if getattr(args, "provider", None):
        os.environ["LLM_PROVIDER"] = args.provider
    if getattr(args, "model", None):
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        os.environ[MODEL_VAR.get(provider, ("LLM_MODEL", ""))[0]] = args.model


def model_for(provider: str) -> str:
    var, default = MODEL_VAR[provider]
    return os.environ.get(var) or default


# --------------------------------------------------------------------------
# LLM clients
# --------------------------------------------------------------------------
class LLM(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str, api_key: str | None = None):
        import anthropic
        # without api_key the SDK reads ANTHROPIC_API_KEY from the environment
        self.name, self.client = model, anthropic.Anthropic(**({"api_key": api_key} if api_key else {}))
        self.usage = {"input_tokens": 0, "output_tokens": 0}  # running total, for cost reports

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        r = self.client.messages.create(model=self.name, max_tokens=max_tokens, temperature=0,
                                        system=system, messages=[{"role": "user", "content": user}])
        self.usage["input_tokens"] += r.usage.input_tokens
        self.usage["output_tokens"] += r.usage.output_tokens
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAICompatLLM:
    """OpenAI API (or any compatible server such as Ollama / vLLM).

    GPT-5-family models reject `temperature` and `max_tokens` and spend part of the token
    budget on hidden reasoning. We send the modern parameters and, if the server rejects
    one, drop or rename it once and remember that for later calls.
    """

    def __init__(self, model: str, base_url: str | None = None, reasoning_effort: str | None = None,
                 api_key: str | None = None):
        from openai import OpenAI
        self.name = model
        # without api_key the SDK reads OPENAI_API_KEY from the environment
        self.client = OpenAI(base_url=base_url, **({"api_key": api_key} if api_key else {}))
        self.extra: dict = {"temperature": 0}
        if reasoning_effort:
            self.extra["reasoning_effort"] = reasoning_effort
        self.limit_key = "max_completion_tokens"
        # running total, for cost reports; output includes hidden reasoning tokens
        self.usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        import openai
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        # reasoning tokens count against the limit, so leave headroom
        budget = max_tokens * 4 if "reasoning_effort" in self.extra else max_tokens
        for _ in range(4):
            try:
                r = self.client.chat.completions.create(
                    model=self.name, messages=messages, **{self.limit_key: budget}, **self.extra)
                usage = getattr(r, "usage", None)  # compatible servers may omit it
                if usage:
                    self.usage["input_tokens"] += usage.prompt_tokens or 0
                    self.usage["output_tokens"] += usage.completion_tokens or 0
                    details = getattr(usage, "completion_tokens_details", None)
                    self.usage["reasoning_tokens"] += getattr(details, "reasoning_tokens", 0) or 0
                return r.choices[0].message.content or ""
            except openai.BadRequestError as e:
                msg = str(e)
                if "temperature" in msg and "temperature" in self.extra:
                    self.extra.pop("temperature")
                elif "reasoning_effort" in msg and "reasoning_effort" in self.extra:
                    self.extra.pop("reasoning_effort")
                elif "max_completion_tokens" in msg and self.limit_key == "max_completion_tokens":
                    self.limit_key = "max_tokens"
                else:
                    raise
        raise RuntimeError("OpenAI request kept failing after parameter fallbacks")


class OllamaLLM:
    """A local model served by Ollama, through its native /api/chat endpoint.

    The native API (unlike Ollama's OpenAI-compatible one) lets us set the context window:
    Ollama's default is a few thousand tokens and silently cuts the start of longer prompts,
    which here would be the answer rules. Thinking ("reasoning") models such as qwen3 are asked
    not to think: it is slow and would push the STATUS line out of first position.
    """

    def __init__(self, model: str, url: str = "http://localhost:11434", num_ctx: int = 16384):
        self.name, self.url, self.num_ctx = model, url.rstrip("/"), num_ctx
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def _post(self, payload: dict) -> dict:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code == 404 and "not found" in msg:
                raise SystemExit(f"model '{self.name}' is not in Ollama. Pull it with `ollama pull {self.name}`, "
                                 f"or pick an installed one with --model: {', '.join(self.installed()) or 'none'}") from e
            raise RuntimeError(f"Ollama error {e.code}: {msg}") from e
        except urllib.error.URLError as e:
            raise SystemExit(f"cannot reach Ollama at {self.url} ({e.reason}): is it running? "
                             f"Start it with `ollama serve` or the Ollama app.") from e

    def installed(self) -> list[str]:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=10) as r:
                return [m["name"] for m in json.loads(r.read()).get("models", [])]
        except Exception:
            return []

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        payload = {"model": self.name, "stream": False, "think": False,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                   "options": {"temperature": 0, "num_ctx": self.num_ctx, "num_predict": max_tokens}}
        try:
            out = self._post(payload)
        except RuntimeError as e:
            if "think" not in str(e):
                raise
            payload.pop("think")  # models without thinking support reject the flag
            out = self._post(payload)
        self.usage["input_tokens"] += out.get("prompt_eval_count", 0)
        self.usage["output_tokens"] += out.get("eval_count", 0)
        if out.get("prompt_eval_count", 0) >= self.num_ctx - 8:
            import sys
            print(f"warning: prompt filled the whole context ({self.num_ctx} tokens) and was cut; "
                  f"raise OLLAMA_NUM_CTX", file=sys.stderr)
        text = out.get("message", {}).get("content", "")
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)  # in case a model thinks anyway


# ---- the user's own key (the public app) -------------------------------------------------------------
# Providers a user can pick in the app, with the default model (the user can type another one). Google's
# Gemini models are reached through Google's OpenAI-compatible endpoint, so no extra SDK is needed.
# Ollama is not offered: a server cannot reach a model on the user's machine.
USER_PROVIDERS = {"openai": "gpt-5.4-mini", "anthropic": "claude-haiku-5-5", "google": "gemini-2.5-flash"}
PROVIDER_LABELS = {"openai": "OpenAI", "anthropic": "Claude (Anthropic)", "google": "Google Gemini",
                   "ollama": "Local model (Ollama, no key)"}
# A local model works only when the app runs on the same computer as Ollama, so the app offers it only then.
LOCAL_PROVIDER = "ollama"
PREFERRED_LOCAL_MODELS = ("qwen3:8b", "llama3:8b", "llama3:latest")
GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
KEY_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")


def local_models() -> list[str]:
    """Models installed in a running Ollama on this computer (empty if Ollama is not running), best first."""
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    installed = OllamaLLM("", url).installed()
    return sorted(installed, key=lambda m: (m not in PREFERRED_LOCAL_MODELS, installed.index(m)))


def make_llm(provider: str, model: str, api_key: str) -> LLM:
    """An LLM client for exactly this key. Never falls back to a key in the environment: an empty key is an
    error, so the public app cannot spend the operator's credit by accident. A local Ollama model needs no key."""
    if provider == LOCAL_PROVIDER:
        if not (model or "").strip():
            raise ValueError("no model given")
        return OllamaLLM(model.strip(), os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                         int(os.environ.get("OLLAMA_NUM_CTX", "16384")))
    api_key = (api_key or "").strip()
    if not api_key:
        raise ValueError("no API key given")
    model = (model or "").strip() or USER_PROVIDERS.get(provider, "")
    if not model:
        raise ValueError("no model given")
    if provider == "anthropic":
        return AnthropicLLM(model, api_key=api_key)
    if provider == "openai":
        return OpenAICompatLLM(model, None, os.environ.get("LLM_REASONING_EFFORT", "low") or None, api_key=api_key)
    if provider == "google":
        return OpenAICompatLLM(model, GOOGLE_BASE_URL, None, api_key=api_key)
    raise ValueError(f"unknown provider: {provider} ({', '.join(USER_PROVIDERS)})")


def explain_error(e: Exception, api_key: str = "") -> str:
    """A readable reason for a failed provider call, with the key never echoed back."""
    name, msg = type(e).__name__, str(e)
    if api_key:
        msg = msg.replace(api_key.strip(), "***")
    code = getattr(e, "status_code", None)
    if code == 401 or "AuthenticationError" in name:
        return "The provider rejected the API key (401). Check that it is correct and active."
    if code == 429 or "RateLimitError" in name:
        return "The provider refused the request (429): no credit left, or too many requests. Check your account."
    if code == 404 or "NotFoundError" in name:
        return "The provider does not know this model (404). Check the model name."
    if code == 403 or "PermissionDenied" in name:
        return "The key has no access to this model (403)."
    if "APIConnectionError" in name or "ConnectError" in name:
        return "Could not reach the provider. Check your connection."
    return f"{name}: {msg[:300]}"


def llm_from_env() -> LLM:
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_BASE_URL"):
            raise SystemExit("OPENAI_API_KEY is not set: put it in the .env file (see .env.example), "
                             "or run a local model with --provider ollama")
        return OpenAICompatLLM(model_for("openai"), os.environ.get("OPENAI_BASE_URL"),
                               os.environ.get("LLM_REASONING_EFFORT", "low") or None)
    if provider == "anthropic":
        return AnthropicLLM(model_for("anthropic"))
    if provider == "ollama":
        return OllamaLLM(model_for("ollama"), os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                         int(os.environ.get("OLLAMA_NUM_CTX", "16384")))
    raise SystemExit(f"unknown LLM_PROVIDER: {provider} (openai, anthropic or ollama)")


class CountingLLM:
    """Wraps an LLM to count calls per question (reported as a metric)."""

    def __init__(self, inner: LLM):
        self.inner, self.name, self.calls = inner, inner.name, 0

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        self.calls += 1
        return self.inner.complete(system, user, max_tokens)
