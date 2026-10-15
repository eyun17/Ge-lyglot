"""The concept graph: everyday words in the five question languages -> the statute sections they are about.

Dense retrieval misses questions whose words never appear in the statutes ("get my taxes back" is
Veranlagung, EStG § 46; "Anmeldung" is BMG § 17). Each CONCEPT lists aliases per language and the
sections that answer it. COUNTRY_GROUPS map nationalities to the provisions that single them out
(EU/EEA/Swiss citizens, the states privileged by AufenthV § 41 and BeschV § 26, the Western Balkans).
A concept may add sections only when a country group is also named ("with_group"), e.g. a spouse of an
EU citizen falls under FreizügG/EU § 3, not under family reunification in the Residence Act.

How aliases match (kg.py): lowercase; an alias containing Latin letters must start a word ("ital" matches
"Italian", not "capital"); Korean and Arabic aliases match anywhere, because particles and prefixes attach
to the word (بالبطاقة الزرقاء, 블루카드를).

Written from the statutes' structure and common questions of foreigners, not from single evaluation
questions; the evaluation set was known while writing it, so improvements on it may be optimistic.
"""
from __future__ import annotations

# id: {"ko"/"en"/"de"/"ar"/"it": [aliases], "sections": [...], "with_group": {group: [sections]}}
CONCEPTS: dict[str, dict] = {
    # ---- residence titles and work -------------------------------------------------------------
    "blue_card": {
        "ko": ["블루카드"], "en": ["blue card"], "de": ["blaue karte", "blauen karte"],
        "ar": ["البطاقة الزرقاء"], "it": ["carta blu"],
        "sections": ["AufenthG § 18g", "AufenthG § 18c Abs. 2"]},
    "settlement_permit": {
        "ko": ["영주권", "정주허가", "정착허가"], "en": ["permanent residence", "settlement permit", "permanent settlement"],
        "de": ["niederlassungserlaubnis", "unbefristete aufenthaltserlaubnis", "daueraufenthalt"],
        "ar": ["الإقامة الدائمة", "إقامة دائمة"], "it": ["soggiorno permanente", "permesso di domicilio"],
        "sections": ["AufenthG § 9 Abs. 2", "AufenthG § 18c"]},
    "skilled_work": {
        "ko": ["취업 비자", "취업비자", "취업 체류허가", "전문인력"],
        "en": ["work visa", "work residence permit", "skilled worker", "skilled-worker", "employment residence permit"],
        "de": ["arbeitsvisum", "aufenthaltserlaubnis zur beschäftigung", "fachkraft"],
        "ar": ["تأشيرة عمل", "فيزا شغل", "إقامة عمل", "إقامة لغرض العمل", "العمالة الماهرة"],
        "it": ["visto di lavoro", "permesso di soggiorno per lavoro", "lavoratori qualificati"],
        "sections": ["AufenthG § 18a", "AufenthG § 18b", "AufenthG § 18 Abs. 2"]},
    "opportunity_card": {
        "ko": ["찬스카르테", "기회카드"], "en": ["opportunity card"], "de": ["chancenkarte"],
        "ar": ["بطاقة الفرص"], "it": ["carta delle opportunità"],
        "sections": ["AufenthG § 20a", "AufenthG § 20b"]},
    "job_search": {
        "ko": ["취준", "구직", "일자리를 찾", "일자리를 구하"],
        "en": ["look for a job", "looking for a job", "job-seeker", "job seeker", "find a job"],
        "de": ["arbeitsplatzsuche", "stellensuche", "eine stelle suche"],
        "ar": ["البحث عن عمل", "البحث عن شغل", "لاقي شغل"], "it": ["cercare lavoro", "cerco lavoro"],
        "sections": ["AufenthG § 20"]},
    "studying": {
        "ko": ["유학생", "재학 중", "공부하면서"], "en": ["student", "while they study", "while i study"],
        "de": ["studierende", "studium", "student"], "ar": ["طالب", "طلاب"], "it": ["student", "studi"],
        "sections": ["AufenthG § 16b"]},
    "ausbildung": {
        "ko": ["아우스빌둥"], "en": ["ausbildung"], "de": ["ausbildung"], "ar": ["أوسبيلدونغ", "الأوسبيلدونغ"],
        "it": ["ausbildung"],
        "sections": ["AufenthG § 16a"]},
    "recognition": {
        "ko": ["인정됐", "인정된 자격", "부분만 인정", "일부만 인정"], "en": ["recognised", "recognized", "recognition"],
        "de": ["anerkannt", "anerkennung"], "ar": ["معترف", "اعتراف", "انعترف"], "it": ["riconosciut"],
        "sections": ["AufenthG § 16d"]},
    "work_experience": {
        "ko": ["실무 경력", "경력만"], "en": ["work experience", "practical experience", "practical work experience"],
        "de": ["berufserfahrung"], "ar": ["خبرة عملية", "خبرة بشغل"], "it": ["esperienza pratica", "esperienza lavorativa"],
        "sections": ["AufenthG § 19c Abs. 2", "BeschV § 6"]},
    "au_pair": {
        "ko": ["오페어"], "en": ["au pair"], "de": ["au-pair", "au pair"], "ar": ["أوبير"], "it": ["au pair"],
        "sections": ["BeschV § 12"]},
    "seasonal_work": {
        "ko": ["계절 일자리", "계절 근로", "수확"], "en": ["seasonal", "harvest"], "de": ["saisonarbeit", "saison", "ernte"],
        "ar": ["موسمي", "قطاف", "حصاد"], "it": ["stagional", "raccolta"],
        "sections": ["BeschV § 15a"]},
    "intra_company_transfer": {
        "ko": ["파견", "지사로", "본사"], "en": ["transferred", "head office", "branch"],
        "de": ["entsandt", "entsendung", "zentrale eines"], "ar": ["فرع الشركة", "المقر الرئيسي", "نقلوني", "نُقلت"],
        "it": ["trasferit", "sede centrale", "filiale"],
        "sections": ["AufenthG § 19", "AufenthG § 19a", "AufenthG § 19b"],
        "with_group": {"eu": ["FreizügG/EU § 2 Abs. 2"]}},
    "freelance": {
        "ko": ["프리랜서"], "en": ["freelance"], "de": ["freiberuf", "freelancer"], "ar": ["فريلانسر", "العمل الحر"],
        "it": ["freelance", "libero professionista"],
        "sections": ["AufenthG § 21 Abs. 5", "AO § 138 Abs. 1", "EStG § 18"]},
    "fast_track": {
        "ko": ["앞당길", "빨리 데려"], "en": ["speed up", "quickly"], "de": ["beschleunig"],
        "ar": ["تسريع", "تسرّع", "بسرعة"], "it": ["accelerare", "rapidamente"],
        "sections": ["AufenthG § 81a"]},
    "employment_agency": {
        "ko": ["연방고용청", "고용 동의"], "en": ["federal employment agency"], "de": ["bundesagentur für arbeit"],
        "ar": ["الوكالة الاتحادية للعمل", "وكالة العمل الاتحادية"], "it": ["agenzia federale per il lavoro"],
        "sections": ["AufenthG § 39", "BeschV § 36"]},
    "job_ends": {
        "ko": ["그만두", "퇴사", "해고"], "en": ["quit my job", "leave my job", "laid off"],
        "de": ["kündige", "gekündigt"], "ar": ["تركت الشغل", "تركت وظيفتي", "طردوني", "فُصلت"],
        "it": ["lascio il mio", "licenziat"],
        "sections": ["AufenthG § 82 Abs. 6"]},
    "permit_refused": {
        "ko": ["거절될", "거절했", "거절당"], "en": ["refused", "rejected"], "de": ["abgelehnt"],
        "ar": ["رفض", "يرفضو"], "it": ["rifiutat"],
        "sections": ["AufenthG § 40", "AufenthG § 19f", "AufenthG § 5"]},
    # ---- entry and short stays -------------------------------------------------------------------
    "visa": {
        "ko": ["비자가 필요", "입국"], "en": ["need a visa", "enter germany"], "de": ["brauche ich ein visum", "einreise"],
        "ar": ["أحتاج إلى تأشيرة", "بحتاج فيزا", "دخول ألمانيا"], "it": ["bisogno di un visto", "entrare in germania"],
        "sections": ["AufenthG § 4 Abs. 1", "AufenthG § 6 Abs. 3", "AufenthV § 15"]},
    "visa_free_stay": {
        "ko": ["무비자", "비자 없이"], "en": ["visa-free", "without a visa"], "de": ["visumfrei", "ohne visum"],
        "ar": ["بلا فيزا", "دون تأشيرة", "بدون فيزا"], "it": ["senza visto"],
        "sections": ["AufenthV § 15", "AufenthV § 41 Abs. 1", "AufenthV § 41 Abs. 3"]},
    "change_status_in_germany": {
        "ko": ["비자를 바꿀", "체류허가로 바꿀", "워킹 홀리데이"], "en": ["change my visa", "switch to", "working holiday"],
        "de": ["visum wechseln", "wechseln", "working-holiday"], "ar": ["غيّر الفيزا", "تغيير تأشيرتي", "working holiday"],
        "it": ["cambiare il visto", "passare a", "working holiday"],
        "sections": ["AufenthV § 39", "AufenthV § 41 Abs. 1"]},
    # ---- registration, EU citizens, family, citizenship ------------------------------------------
    "registration": {
        "ko": ["안멜둥", "주민등록", "전입신고"], "en": ["anmeldung", "register my address"],
        "de": ["anmeld", "wohnsitz"], "ar": ["تسجيل السكن", "سجّل السكن", "يسجّلوا السكن"], "it": ["anmeldung"],
        "sections": ["BMG § 17 Abs. 1"]},
    "deregistration": {
        "ko": ["압멜둥", "전출신고"], "en": ["abmeldung", "deregister"], "de": ["abmeld"],
        "ar": ["إلغاء تسجيل السكن", "الغي تسجيل السكن"], "it": ["abmeldung"],
        "sections": ["BMG § 17 Abs. 2"]},
    "eu_citizens": {
        "ko": ["eu 시민", "eu시민", "eu 국가"], "en": ["eu citizen", "eu or non-eu", "eu-citizen"],
        "de": ["eu-bürger", "unionsbürger"], "ar": ["مواطني الاتحاد الأوروبي", "مواطنين الاتحاد الأوروبي", "من الاتحاد الأوروبي"],
        "it": ["cittadini ue", "cittadini dell'ue"],
        "sections": ["FreizügG/EU § 2 Abs. 2", "FreizügG/EU § 2a Abs. 1", "AufenthG § 1 Abs. 2"]},
    "family": {
        "ko": ["배우자", "가족"], "en": ["spouse", "family"], "de": ["ehepartner", "familie", "ehegatte"],
        "ar": ["زوجي", "زوجتي", "مرتي", "جوزي", "عائلت"], "it": ["coniuge", "famiglia", "familiar"],
        "sections": ["AufenthG § 27", "AufenthG § 30"],
        "with_group": {"eu": ["FreizügG/EU § 3 Abs. 1", "FreizügG/EU § 5 Abs. 1"]}},
    "citizenship": {
        "ko": ["독일 국적", "시민권", "귀화"], "en": ["german citizenship", "naturalis", "naturaliz"],
        "de": ["deutsche staatsangehörigkeit", "einbürger", "eingebürgert"], "ar": ["الجنسية الألمانية"],
        "it": ["cittadinanza tedesca"],
        "sections": ["StAG § 10 Abs. 1"]},
    # ---- tax --------------------------------------------------------------------------------------
    "tax_liability": {
        "ko": ["세금을 내야", "납세"], "en": ["pay tax"], "de": ["steuern zahlen"],
        "ar": ["دفع الضرائب", "ادفع ضرايب"], "it": ["pagare le tasse"],
        "sections": ["EStG § 1 Abs. 1", "AO § 9"]},
    "tax_return_refund": {
        "ko": ["돌려받", "세금 신고", "세금신고"], "en": ["tax return", "get back the taxes", "taxes i paid"],
        "de": ["steuererklärung", "zurückbekommen"], "ar": ["استرداد الضرائب", "رجّعها", "إقرار ضريبي", "تصريح ضريبي"],
        "it": ["dichiarazione dei redditi", "riavere le tasse"],
        "sections": ["EStG § 46 Abs. 2", "AO § 149 Abs. 2"],
        "with_concept": {"pension": ["SGB VI § 210 Abs. 1"]}},
    "pension": {
        "ko": ["연금"], "en": ["pension"], "de": ["rentenversicherung", "rente"], "ar": ["التقاعد"],
        "it": ["pensionistic", "pension"],
        "sections": ["SGB VI § 1"]},
    "minijob": {
        "ko": ["미니잡"], "en": ["minijob", "mini job"], "de": ["minijob"], "ar": ["الميني جوب"], "it": ["minijob"],
        "sections": ["SGB IV § 8 Abs. 1", "EStG § 40a Abs. 2"]},
    "student_jobs": {
        "ko": ["베르크스튜던트", "히비"], "en": ["werkstudent", "hiwi"], "de": ["werkstudent", "hiwi"],
        "ar": ["werkstudent", "hiwi"], "it": ["werkstudent", "hiwi"],
        "sections": ["SGB VI § 1", "SGB VI § 6 Abs. 1b"]},
    "kindergeld": {
        "ko": ["킨더겔트", "아동수당"], "en": ["kindergeld", "child benefit"], "de": ["kindergeld"],
        "ar": ["الكيندرغيلد"], "it": ["kindergeld"],
        "sections": ["EStG § 62"]},
    "joint_taxation": {
        "ko": ["합산 과세"], "en": ["taxed jointly", "joint taxation"], "de": ["zusammen veranlagt", "zusammenveranlagung"],
        "ar": ["التقييم الضريبي المشترك", "تقييم ضريبي مشترك"], "it": ["tassati congiuntamente"],
        "sections": ["EStG § 26 Abs. 1", "EStG § 1a Abs. 1"]},
    "tax_id": {
        "ko": ["택스 아이디", "세금 번호"], "en": ["tax id", "steuer-id"], "de": ["steuer-id", "identifikationsnummer"],
        "ar": ["الرقم الضريبي"], "it": ["steuer-id", "codice fiscale"],
        "sections": ["AO § 139b"]},
    "foreign_income": {
        "ko": ["두 나라", "소득이 있는데"], "en": ["both countries", "income in"], "de": ["beiden ländern", "einkommen in"],
        "ar": ["البلدين", "دخل في", "دخل ب"], "it": ["entrambi i paesi", "redditi anche"],
        "sections": ["EStG § 34c Abs. 1"]},
    "tax_objection": {
        "ko": ["이의를 제기", "이의 제기"], "en": ["object", "objection"], "de": ["einspruch"],
        "ar": ["الاعتراض", "اعترض"], "it": ["opposizione"],
        "sections": ["AO § 347 Abs. 1", "AO § 355 Abs. 1"]},
    "tax_amount": {
        "ko": ["세금이 정확히", "세금이 얼마"], "en": ["how much tax"], "de": ["wie viel steuern"],
        "ar": ["كم ستكون الضريبة", "ادفع ضرايب"], "it": ["quante tasse"],
        "sections": ["EStG § 32a Abs. 1"]},
    # ---- social insurance -------------------------------------------------------------------------
    "health_insurance": {
        "ko": ["건강보험", "의료보험", "공보험"], "en": ["health insurance"], "de": ["krankenversicher"],
        "ar": ["التأمين الصحي", "تأمين صحي"], "it": ["assicurazione sanitaria"],
        "sections": ["SGB V § 5 Abs. 1", "VVG § 193 Abs. 3"]},
    "social_insurance": {
        "ko": ["사회보험"], "en": ["social insurance"], "de": ["sozialversicherung"],
        "ar": ["التأمين الاجتماعي", "التأمينات الاجتماعية"], "it": ["contributi previdenziali", "previdenza sociale"],
        "sections": ["SGB IV § 2", "SGB IV § 3"]},
    "artists_insurance": {
        "ko": ["예술인사회보험", "예술인"], "en": ["artists' social insurance", "artist"], "de": ["künstlersozial", "künstler"],
        "ar": ["للفنانين", "الفنانين"], "it": ["per artisti", "artisti"],
        "sections": ["KSVG § 1"]},
}

# Nationalities named in the statutes. Aliases are country names and demonyms (stems where possible).
COUNTRY_GROUPS: dict[str, dict] = {
    # EU, EEA and Switzerland: Freedom of Movement Act instead of the Residence Act
    "eu": {
        "sections": ["FreizügG/EU § 2 Abs. 2", "FreizügG/EU § 2a Abs. 1", "AufenthG § 1 Abs. 2"],
        "countries": {
            "AT": ["오스트리아", "austria", "österreich", "نمسا"], "BE": ["벨기에", "belgi", "belg", "بلجيك"],
            "BG": ["불가리아", "bulgar", "بلغار"], "HR": ["크로아티아", "croat", "kroat", "croa", "كروات"],
            "CY": ["키프로스", "cypr", "zypr", "cipr", "قبرص"], "CZ": ["체코", "czech", "tschech", "ceco", "ceca", "التشيك"],
            "DK": ["덴마크", "denmark", "danish", "dänemark", "dänisch", "danimarca", "danese", "دنمارك"],
            "EE": ["에스토니아", "estonia", "estland", "estnisch", "estone", "إستوني"],
            "FI": ["핀란드", "finland", "finnish", "finnland", "finnisch", "finlandes", "فنلند"],
            "FR": ["프랑스", "france", "french", "frankreich", "französ", "franzose", "francia", "frances", "فرنس"],
            "GR": ["그리스", "greece", "greek", "griechen", "grecia", "greco", "greca", "يونان"],
            "HU": ["헝가리", "hungar", "ungarn", "ungarisch", "ungher", "هنغار", "مجري"],
            "IE": ["아일랜드", "ireland", "irish", "irland", "irisch", "irlandes", "أيرلند", "إيرلند"],
            "IT": ["이탈리아", "ital", "إيطالي", "ايطالي"],
            "LV": ["라트비아", "latvia", "lettland", "letton", "لاتفي"],
            "LT": ["리투아니아", "lithuania", "litauen", "lituan", "ليتوان"],
            "LU": ["룩셈부르크", "luxembourg", "luxemburg", "lussemburg", "لوكسمبورغ"],
            "MT": ["몰타", "malta", "maltes", "مالط"],
            "NL": ["네덜란드", "netherlands", "dutch", "niederlande", "niederländ", "paesi bassi", "olandes", "olanda", "هولند"],
            "PL": ["폴란드", "poland", "polish", "polen", "polnisch", "polonia", "polacc", "بولند"],
            "PT": ["포르투갈", "portug", "portog", "برتغال"],
            "RO": ["루마니아", "romania", "rumän", "romen", "روماني"],
            "SK": ["슬로바키아", "slovak", "slowak", "slovacc", "سلوفاك"],
            "SI": ["슬로베니아", "sloven", "slowen", "سلوفيني"],
            "ES": ["스페인", "spain", "spanish", "spanien", "spanier", "spanisch", "spagn", "إسبان", "اسبان"],
            "SE": ["스웨덴", "swed", "schwed", "svezi", "sved", "سويد"],
            "IS": ["아이슬란드", "iceland", "islanda", "isländ", "آيسلند"],
            "LI": ["리히텐슈타인", "liechtenstein", "ليختنشتاين"],
            "NO": ["노르웨이", "norw", "norweg", "norveg", "نرويج"],
            "CH": ["스위스", "swiss", "switzerland", "schweiz", "svizzer", "سويسر"],
        }},
    # AufenthV § 41 Abs. 1 / BeschV § 26 Abs. 1: may get a residence title inside Germany, privileged employment
    "privileged": {
        "sections": ["AufenthV § 41 Abs. 1", "AufenthV § 41 Abs. 3", "BeschV § 26 Abs. 1"],
        "countries": {
            "AU": ["호주", "오스트레일리아", "australi", "austral", "أسترال", "استرال"],
            "IL": ["이스라엘", "israel", "إسرائيل"], "JP": ["일본", "japan", "giappon", "يابان"],
            "CA": ["캐나다", "canad", "kanad", "كند"],
            "KR": ["한국", "south korea", "korean", "südkorea", "koreaner", "corea", "corean", "كوري"],
            "NZ": ["뉴질랜드", "new zealand", "neuseeland", "nuova zelanda", "نيوزيلند"],
            "GB": ["영국", "british", "united kingdom", "britain", "vereinigtes königreich", "brit", "regno unito", "britann", "بريطان"],
            "US": ["미국", "americ", "usa", "united states", "us-amerikan", "amerikan", "vereinigte staaten", "أمريك", "أميرك", "امريك"],
        }},
    # AufenthV § 41 Abs. 2: the same, but without employment
    "privileged_no_work": {
        "sections": ["AufenthV § 41 Abs. 2"],
        "countries": {
            "AD": ["안도라", "andorra", "أندورا"], "BR": ["브라질", "brazil", "brasil", "برازيل"],
            "SV": ["엘살바도르", "el salvador", "السلفادور"], "HN": ["온두라스", "hondura", "هندوراس"],
            "MC": ["모나코", "monaco", "موناكو"], "SM": ["산마리노", "san marino", "سان مارينو"],
        }},
    # BeschV § 26 Abs. 2: the Western Balkans rule
    "western_balkans": {
        "sections": ["BeschV § 26 Abs. 2"],
        "countries": {
            "AL": ["알바니아", "albani", "albanes", "ألبان"], "BA": ["보스니아", "bosni", "بوسن"],
            "XK": ["코소보", "kosov", "كوسوف"], "ME": ["몬테네그로", "montenegr", "الجبل الأسود"],
            "MK": ["북마케도니아", "마케도니아", "macedon", "mazedon", "مقدون"],
            "RS": ["세르비아", "serbia", "serb", "صرب"],
        }},
}
