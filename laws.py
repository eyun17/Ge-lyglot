"""The statutes GesetzPolyglot knows about: the one place to add a law.

Adding a law to the corpus:
    1. add it to LAWS (abbreviation -> gesetze-im-internet.de slug) and to CORPUS
    2. update TOPIC and OUT_OF_SCOPE below if the subject area changes
    3. python gii_parser.py fetch && python gii_parser.py parse && python retrieval.py build --store chroma
Everything else (parser defaults, --law filters, prompts, citation parsing, app text) reads from here.
"""
from __future__ import annotations

# Every law the parser can fetch. Citations to any of these are recognised in answers.
LAWS = {
    "AufenthG": "aufenthg_2004",   # Aufenthaltsgesetz (Residence Act)
    "BeschV": "beschv_2013",       # Beschäftigungsverordnung (Employment Ordinance)
    "AsylG": "asylvfg_1992",       # Asylgesetz (Asylum Act)
    "EStG": "estg",                # Einkommensteuergesetz (Income Tax Act)
    "AO": "ao_1977",               # Abgabenordnung (Fiscal Code)
    "SGB IV": "sgb_4",             # Sozialgesetzbuch IV: common rules of social insurance (minijobs, employer duties)
    "SGB VI": "sgb_6",             # Sozialgesetzbuch VI: statutory pension insurance
    "AufenthV": "aufenthv",        # Aufenthaltsverordnung (Residence Ordinance), not indexed yet
}

# The laws that are indexed and searched.
CORPUS = ["AufenthG", "BeschV", "AsylG", "EStG", "AO", "SGB IV", "SGB VI"]

# What the corpus covers, and nearby areas it does not, as used in prompts and the app.
TOPIC = "residence, employment, asylum, income tax and pension insurance law"
TOPIC_DE = "Aufenthalts-, Beschäftigungs-, Asyl-, Einkommensteuer- und Rentenversicherungsrecht"
OUT_OF_SCOPE = ("health, unemployment and long-term care insurance, VAT, church tax, double taxation treaties, "
                "citizenship, registration, benefits for asylum seekers")


def corpus_names(conj: str = "and") -> str:
    """'AufenthG and BeschV', 'AufenthG, BeschV and AsylG'."""
    *head, last = CORPUS
    return f"{', '.join(head)} {conj} {last}" if head else last
