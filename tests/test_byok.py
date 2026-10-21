"""Run: python -m pytest tests/test_byok.py   (no network: clients are only constructed, never called)
The public app uses the user's own API key and must never fall back to the operator's key."""
import pytest

from gesetzpolyglot.llm import GOOGLE_BASE_URL, AnthropicLLM, OpenAICompatLLM, explain_error, make_llm


def test_key_is_required(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-operator")      # even with an operator key in the environment
    for provider in ("openai", "anthropic", "google"):
        with pytest.raises(ValueError):
            make_llm(provider, "", "")
        with pytest.raises(ValueError):
            make_llm(provider, "", "   ")


def test_user_key_wins_over_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-operator")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-operator")
    o = make_llm("openai", "", "sk-user")
    assert isinstance(o, OpenAICompatLLM) and o.client.api_key == "sk-user" and o.name == "gpt-5.4-mini"
    a = make_llm("anthropic", "claude-haiku-5-5", "sk-ant-user")
    assert isinstance(a, AnthropicLLM) and a.client.api_key == "sk-ant-user" and a.name == "claude-haiku-5-5"
    g = make_llm("google", "", "AIza-user")
    assert g.client.api_key == "AIza-user" and str(g.client.base_url) == GOOGLE_BASE_URL


def test_unknown_provider():
    with pytest.raises(ValueError):
        make_llm("mistral", "mistral-large", "x")


def test_errors_never_echo_the_key():
    class AuthenticationError(Exception):
        status_code = 401
    assert "401" in explain_error(AuthenticationError("bad key sk-user-123"), "sk-user-123")
    assert "sk-user-123" not in explain_error(RuntimeError("failed with sk-user-123"), "sk-user-123")


def test_app_asks_for_a_key_before_doing_anything():
    import app
    calls = []
    demo = app.build_ui(lambda *a: calls.append(a), [["x"]], "", "x", byok=True)
    run = next(f.fn for f in demo.fns.values() if getattr(f.fn, "__name__", "") == "run")
    out = run("Can students work?", app.CONDITION_LABELS["dense"], "openai", "gpt-5.4-mini", "")
    assert "API key" in out[0] and calls == []
    run("Can students work?", app.CONDITION_LABELS["dense"], "openai", "gpt-5.4-mini", "sk-user")
    assert calls and calls[0][2] == {"provider": "openai", "model": "gpt-5.4-mini", "api_key": "sk-user"}


def test_default_models():
    from gesetzpolyglot.llm import USER_PROVIDERS
    assert USER_PROVIDERS == {"openai": "gpt-5.4-mini", "anthropic": "claude-haiku-5-5", "google": "gemini-2.5-flash"}
    assert make_llm("anthropic", "", "sk-ant-user").name == "claude-haiku-5-5"


def test_zero_gpu_wiring(monkeypatch):
    """On a ZeroGPU Space the question embedding must run inside @spaces.GPU and the model sit on cuda."""
    import types
    import app

    seen = {}

    def gpu(duration=60):
        def wrap(fn):
            seen["decorated"], seen["duration"] = fn.__name__, duration
            return fn
        return wrap
    monkeypatch.setattr(app, "spaces", types.SimpleNamespace(GPU=gpu))

    class Model:
        def to(self, device):
            seen["device"] = device

    class Embedder:
        m = Model()

        def encode(self, texts):
            return [len(t) for t in texts]

    index = types.SimpleNamespace(embedder=Embedder())
    assert app.use_zero_gpu(index) is True
    assert seen == {"device": "cuda", "decorated": "gpu_encode", "duration": 15}
    assert index.embedder.encode(["abc"]) == [3]                 # still the same embedding, now via the GPU function
    monkeypatch.setattr(app, "spaces", None)
    assert app.use_zero_gpu(types.SimpleNamespace(embedder=Embedder())) is False   # elsewhere: nothing changes


def test_local_model_needs_no_key_and_is_offered_only_locally(monkeypatch):
    import app
    from gesetzpolyglot.llm import OllamaLLM
    m = make_llm("ollama", "llama3:latest", "")
    assert isinstance(m, OllamaLLM) and m.name == "llama3:latest"
    with pytest.raises(ValueError):
        make_llm("ollama", "", "")
    calls = []
    demo = app.build_ui(lambda *a: calls.append(a), [["x"]], "", "x", byok=True, local_models=["llama3:latest"])
    run = next(f.fn for f in demo.fns.values() if getattr(f.fn, "__name__", "") == "run")
    run("Can students work?", app.CONDITION_LABELS["dense"], "ollama", "llama3:latest", "")   # no key needed
    assert calls and calls[0][2]["provider"] == "ollama"
    out = run("Can students work?", app.CONDITION_LABELS["dense"], "openai", "gpt-5.4-mini", "")
    assert "API key" in out[0] and len(calls) == 1                # cloud providers still need a key


def test_local_models_sorted_and_empty_without_ollama(monkeypatch):
    from gesetzpolyglot import llm
    monkeypatch.setattr(llm.OllamaLLM, "installed", lambda self: ["gemma3:latest", "llama3:latest"])
    assert llm.local_models() == ["llama3:latest", "gemma3:latest"]   # a preferred model first
    monkeypatch.setattr(llm.OllamaLLM, "installed", lambda self: [])
    assert llm.local_models() == []
