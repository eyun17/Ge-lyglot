"""Run: python test_rag.py   (no API key, no model download)"""
import tempfile

from rag import RAG, detect_lang, parse_queries, parse_status, validate_citations
from test_retrieval import _index


class FakeLLM:
    """Returns a rewrite JSON for the rewrite prompt and a fixed answer otherwise."""
    name = "fake"

    def __init__(self, answer):
        self.answer, self.prompts = answer, []

    def complete(self, system, user, max_tokens=1200):
        self.prompts.append((system, user))
        if "search queries" in system:
            return '```json\n{"queries": ["Studium Beschäftigung Arbeitstagen"]}\n```'
        return self.answer


def test_detect_lang():
    assert detect_lang("유학생도 일할 수 있나요?") == "ko"
    assert detect_lang("Kann ich als Student arbeiten?") == "de"
    assert detect_lang("Darf ich während des Studiums jobben") == "de"
    assert detect_lang("Can students work in Germany?") == "en"
    assert detect_lang("Öğrenciler Almanya'da çalışabilir mi?") == "tr"
    assert detect_lang("Yabancılar dairesine (Ausländerbehörde) bildirmem gerekir mi?") == "tr"
    assert detect_lang("هل يمكن للطلاب العمل في ألمانيا؟") == "ar"
    assert detect_lang("Gli studenti possono lavorare in Germania durante gli studi?") == "it"
    assert detect_lang("Devo comunicarlo all'ufficio stranieri (Ausländerbehörde)?") == "it"


def test_parse_status_and_queries():
    assert parse_status("STATUS: refuse_out_of_scope\n\nDas ist Steuerrecht.") == (
        "refuse_out_of_scope", "Das ist Steuerrecht.")
    assert parse_status("Just text") == ("answer", "Just text")
    assert parse_status("STATUS: weird\n\nText") == ("answer", "Text")
    assert parse_queries('noise {"queries": ["a", " ", "b", "c", "d"]} noise') == ["a", "b", "c"]
    assert parse_queries("not json") == []


def test_validate_citations():
    retrieved = [{"law": "AufenthG", "section": "16b", "absatz": "3"},
                 {"law": "BeschV", "section": "26", "absatz": "1"}]
    text = ("Ja [AufenthG § 16b Abs. 3]. Siehe [AufenthG § 16b] und [BeschV § 26 Absatz 1]. "
            "Falsch: [AufenthG § 16b Abs. 2], [AufenthG § 99]. Doppelt [AufenthG § 16b Abs. 3].")
    valid, invalid = validate_citations(text, retrieved)
    assert valid == ["AufenthG § 16b Abs. 3", "AufenthG § 16b", "BeschV § 26 Abs. 1"]
    assert invalid == ["AufenthG § 16b Abs. 2", "AufenthG § 99"]


def test_answer_end_to_end():
    llm = FakeLLM("STATUS: answer\n\n네, 연간 140일까지 일할 수 있습니다 [AufenthG § 16b Abs. 3]. "
                  "[AufenthG § 77]")
    with tempfile.TemporaryDirectory() as d:
        rag = RAG(_index(d), llm, k=3)
        r = rag.answer("유학생도 일할 수 있나요?", "rewrite")
        r_h = rag.answer("Beschäftigung Arbeitstagen Studium", "hybrid")
    assert r["lang"] == "ko" and r["status"] == "answer" and r["llm_calls"] == 2
    assert r["citations"] == ["AufenthG § 16b Abs. 3"] and r["invalid_citations"] == ["AufenthG § 77"]
    assert r["retrieved"][0]["id"] == "AufenthG-16b-3"  # found via the German rewrite
    assert r["trace"][1] == {"step": "rewrite", "queries": ["Studium Beschäftigung Arbeitstagen"]}
    assert r["footer"].startswith("법령 기준: AufenthG 2026-10-05")
    assert "Korean" in llm.prompts[1][0] and "[AufenthG § 16b Abs. 3]" in llm.prompts[1][1]
    assert r_h["llm_calls"] == 1 and r_h["lang"] == "de" and "German" in llm.prompts[2][0]


def test_openai_param_fallback():
    import httpx
    import openai
    from rag import OpenAICompatLLM

    calls = []

    def bad(msg):
        req = httpx.Request("POST", "http://x")
        return openai.BadRequestError(msg, response=httpx.Response(400, request=req), body=None)

    class FakeCompletions:
        def create(self, **kw):
            calls.append(kw)
            if "temperature" in kw:
                raise bad("Unsupported value: 'temperature' does not support 0 with this model.")
            if "max_completion_tokens" in kw:
                raise bad("Unrecognized request argument supplied: max_completion_tokens")
            msg = type("M", (), {"content": "ok"})()
            return type("R", (), {"choices": [type("C", (), {"message": msg})()]})()

    llm = OpenAICompatLLM.__new__(OpenAICompatLLM)
    llm.name, llm.extra, llm.limit_key = "m", {"temperature": 0, "reasoning_effort": "low"}, "max_completion_tokens"
    llm.usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
    llm.client = type("Cl", (), {"chat": type("Ch", (), {"completions": FakeCompletions()})()})()
    assert llm.complete("s", "u", max_tokens=100) == "ok"
    assert calls[-1]["max_tokens"] == 400 and "temperature" not in calls[-1]
    n = len(calls)
    assert llm.complete("s", "u") == "ok" and len(calls) == n + 1  # fallbacks remembered


def test_load_dotenv():
    import os
    import tempfile
    from pathlib import Path
    from rag import load_dotenv
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / ".env"
        p.write_text('# comment\nTEST_KEY_A="sk-abc"\nexport TEST_KEY_B=plain  # note\nTEST_KEY_C=keep\n\n')
        os.environ["TEST_KEY_C"] = "from-shell"
        load_dotenv(p)
    assert os.environ["TEST_KEY_A"] == "sk-abc" and os.environ["TEST_KEY_B"] == "plain"
    assert os.environ["TEST_KEY_C"] == "from-shell"  # shell wins
    for k in ("TEST_KEY_A", "TEST_KEY_B", "TEST_KEY_C"):
        os.environ.pop(k)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
