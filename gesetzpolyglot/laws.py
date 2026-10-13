"""The statutes GesetzPolyglot knows about: the one place to add a law.

Adding a law to the corpus:
    1. add it to LAWS (abbreviation -> gesetze-im-internet.de slug) and to CORPUS
    2. update TOPIC and OUT_OF_SCOPE below if the subject area changes
    3. python -m gesetzpolyglot.gii_parser fetch && python -m gesetzpolyglot.gii_parser parse &&
       python -m gesetzpolyglot.retrieval build --store chroma
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
    "SGB V": "sgb_5",              # Sozialgesetzbuch V: statutory health insurance
    "VVG": "vvg_2008",             # Versicherungsvertragsgesetz: duty to hold health insurance (§ 193)
    "FreizügG/EU": "freiz_gg_eu_2004",  # Freizügigkeitsgesetz/EU: residence of EU citizens
    "BMG": "bmg",                  # Bundesmeldegesetz: registering an address (Anmeldung)
    "StAG": "stag",                # Staatsangehörigkeitsgesetz: citizenship and naturalisation
    "KSVG": "ksvg",                # Künstlersozialversicherungsgesetz: social insurance for artists and publicists
    "AufenthV": "aufenthv",        # Aufenthaltsverordnung (Residence Ordinance): visas, visa-free entry
}

# Full titles, shown in the app's source list.
TITLES = {
    "AufenthG": ("Aufenthaltsgesetz", "Residence Act"),
    "AufenthV": ("Aufenthaltsverordnung", "Residence Ordinance"),
    "BeschV": ("Beschäftigungsverordnung", "Employment Ordinance"),
    "AsylG": ("Asylgesetz", "Asylum Act"),
    "FreizügG/EU": ("Freizügigkeitsgesetz/EU", "Freedom of Movement Act/EU"),
    "StAG": ("Staatsangehörigkeitsgesetz", "Nationality Act"),
    "BMG": ("Bundesmeldegesetz", "Federal Registration Act"),
    "EStG": ("Einkommensteuergesetz", "Income Tax Act"),
    "AO": ("Abgabenordnung", "Fiscal Code"),
    "SGB IV": ("Sozialgesetzbuch Viertes Buch", "Social Code IV: common rules of social insurance"),
    "SGB VI": ("Sozialgesetzbuch Sechstes Buch", "Social Code VI: pension insurance"),
    "SGB V": ("Sozialgesetzbuch Fünftes Buch", "Social Code V: health insurance"),
    "VVG": ("Versicherungsvertragsgesetz", "Insurance Contract Act"),
    "KSVG": ("Künstlersozialversicherungsgesetz", "Artists' Social Insurance Act"),
}
assert set(TITLES) == set(LAWS), "every law needs a title"

# The laws that are indexed and searched.
CORPUS = ["AufenthG", "AufenthV", "BeschV", "AsylG", "FreizügG/EU", "StAG", "BMG",
          "EStG", "AO", "SGB IV", "SGB VI", "SGB V", "VVG", "KSVG"]

# What the corpus covers, and nearby areas it does not, as used in prompts and the app.
TOPIC = ("residence, EU free movement, employment, asylum, citizenship, registration, income tax, "
         "pension, health and artists' social insurance law")
TOPIC_DE = ("Aufenthalts-, Freizügigkeits-, Beschäftigungs-, Asyl-, Staatsangehörigkeits-, Melde-, Einkommensteuer-, "
            "Renten-, Kranken- und Künstlersozialversicherungsrecht")
OUT_OF_SCOPE = ("unemployment and long-term care insurance, VAT, church tax, the broadcasting fee (Rundfunkbeitrag), "
                "double taxation treaties, benefits for asylum seekers")


def corpus_names(conj: str = "and") -> str:
    """'AufenthG and BeschV', 'AufenthG, BeschV and AsylG'."""
    *head, last = CORPUS
    return f"{', '.join(head)} {conj} {last}" if head else last
