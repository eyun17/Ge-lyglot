"""The concept graph: everyday words in the five question languages -> the statute sections they are about.

Dense retrieval misses questions whose words never appear in the statutes ("get my taxes back" is
Veranlagung, EStG § 46; "Anmeldung" is BMG § 17). Each CONCEPT lists aliases per language and the
sections that answer it. COUNTRY_GROUPS map nationalities to the provisions that single them out
(EU/EEA/Swiss citizens, the states privileged by AufenthV § 41 and BeschV § 26, the Western Balkans).
A concept may add sections only when a country group is also named ("with_group"), e.g. a spouse of an
EU citizen falls under FreizügG/EU § 3, and then drop the sections that no longer apply ("instead_of"): family
reunification in the Residence Act (AufenthG §§ 27–30) is not the EU citizen's case.

How aliases match (kg.py): lowercase; an alias containing Latin letters must start a word ("ital" matches
"Italian", not "capital"); Korean and Arabic aliases match anywhere, because particles and prefixes attach
to the word (بالبطاقة الزرقاء, 블루카드를).

Written from the statutes' structure and common questions of foreigners, not from single evaluation
questions; the evaluation set was known while writing it, so improvements on it may be optimistic.
"""
from __future__ import annotations

# id: {"ko"/"en"/"de"/"ar"/"it": [aliases], "sections": [...], "with_group": {group: [sections]},
#      "instead_of": {group: [sections that do not apply once the group is named; removed from the ranking]}}
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
        "ko": ["유학생", "재학 중", "공부하면서", "학생비자", "학생 비자", "대학원 합격"],
        "en": ["student", "while they study", "while i study", "student visa"],
        "de": ["studierende", "studium", "student", "studentenvisum"], "ar": ["طالب", "طلاب", "تأشيرة دراسة", "فيزا دراسة"],
        "it": ["student", "studi", "visto per studio"],
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
        "with_group": {"eu": ["FreizügG/EU § 2 Abs. 2"]},
        "instead_of": {"eu": ["AufenthG § 19", "AufenthG § 19a", "AufenthG § 19b"]}},  # ICT cards are for non-EU staff
    "freelance": {
        "ko": ["프리랜서"], "en": ["freelance"], "de": ["freiberuf", "freelancer"], "ar": ["فريلانسر", "العمل الحر"],
        "it": ["freelance", "libero professionista"],
        "sections": ["AufenthG § 21 Abs. 5", "AO § 138 Abs. 1", "EStG § 18"],
        "with_concept": {"studying": ["AufenthG § 21 Abs. 6"]}},  # self-employment next to another residence purpose
    "fast_track": {
        "ko": ["앞당길", "빨리 데려"], "en": ["speed up", "quickly"], "de": ["beschleunig"],
        "ar": ["تسريع", "تسرّع", "بسرعة"], "it": ["accelerare", "rapidamente"],
        "sections": ["AufenthG § 81a"]},
    "employment_agency": {
        "ko": ["연방고용청", "고용 동의"], "en": ["federal employment agency"], "de": ["bundesagentur für arbeit"],
        "ar": ["الوكالة الاتحادية للعمل", "وكالة العمل الاتحادية"], "it": ["agenzia federale per il lavoro"],
        "sections": ["AufenthG § 39", "BeschV § 36"]},
    "job_ends": {
        "ko": ["그만두", "퇴사", "해고", "일자리를 잃", "실직"], "en": ["quit my job", "leave my job", "laid off", "lost my job"],
        "de": ["kündige", "gekündigt", "arbeit verloren", "job verloren"],
        "ar": ["تركت الشغل", "تركت وظيفتي", "طردوني", "فُصلت", "خسرت شغلي", "فقدت وظيفتي"],
        "it": ["lascio il mio", "licenziat", "perso il lavoro"],
        "sections": ["AufenthG § 82 Abs. 6", "AufenthG § 7 Abs. 2"]},
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
        "ko": ["안멜둥", "주민등록", "전입신고", "다른 도시로 이사", "이사하면"],
        "en": ["anmeldung", "register my address", "move to another city"],
        "de": ["anmeld", "wohnsitz", "umzug", "umziehe"], "ar": ["تسجيل السكن", "سجّل السكن", "يسجّلوا السكن", "انتقلت لمدينة"],
        "it": ["anmeldung", "cambio di residenza"],
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
        "with_group": {"eu": ["FreizügG/EU § 3 Abs. 1", "FreizügG/EU § 5 Abs. 1"]},
        "instead_of": {"eu": ["AufenthG § 27", "AufenthG § 28", "AufenthG § 29", "AufenthG § 30"]}},  # not reunification
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
        "ko": ["두 나라", "소득이 있는데", "외국에서 받은 소득", "해외 소득"], "en": ["both countries", "income in", "foreign income"],
        "de": ["beiden ländern", "einkommen in", "ausländische einkünfte"],
        "ar": ["البلدين", "دخل في", "دخل ب", "دخل من الخارج"], "it": ["entrambi i paesi", "redditi anche", "redditi esteri"],
        "sections": ["EStG § 34c Abs. 1", "EStG § 1 Abs. 1", "EStG § 32b Abs. 1"]},
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
    # ---- added 2026-10-17 from the first 40 held-out questions (which are dev data from then on) ---------------
    "parents_join": {
        "ko": ["부모님을 모실", "부모님을 데려", "부모님을 초청", "부모를 데려"], "en": ["bring my parents", "my parents to germany"],
        "de": ["eltern nachholen", "meine eltern nach"], "ar": ["أحضر والدي", "أهلي لألمانيا", "والديّ"],
        "it": ["portare i miei genitori", "i miei genitori in germania"],
        "sections": ["AufenthG § 36 Abs. 2", "AufenthG § 28 Abs. 4"]},
    "german_family": {
        "ko": ["독일인과 결혼", "독일인 배우자", "독일 사람과 결혼"], "en": ["married to a german", "german spouse", "german wife", "german husband"],
        "de": ["mit einem deutschen verheiratet", "mit einer deutschen verheiratet", "deutschen ehepartner", "deutsche ehefrau"],
        "ar": ["متزوج من ألمانية", "متزوجة من ألماني", "زوجي ألماني", "زوجتي ألمانية"],
        "it": ["sposato con una tedesca", "sposata con un tedesco", "coniuge tedesco"],
        "sections": ["AufenthG § 28 Abs. 1", "AufenthG § 28 Abs. 2"]},
    "dual_citizenship": {
        "ko": ["이중국적", "복수국적"], "en": ["dual citizen", "dual nationality", "two citizenships"],
        "de": ["doppelte staatsangehörigkeit", "doppelstaat", "zwei staatsangehörigkeiten"],
        "ar": ["جنسيتين", "مزدوج الجنسية", "مزدوجي الجنسية"], "it": ["doppia cittadinanza"],
        "sections": ["AufenthG § 2 Abs. 1"]},
    "asylum_work": {
        "ko": ["망명 신청자", "망명 신청 중", "난민 신청자"], "en": ["asylum seeker", "asylum application"],
        "de": ["asylbewerber", "asylverfahren", "asylantrag"], "ar": ["طالب لجوء", "طلب لجوء", "طالبي اللجوء"],
        "it": ["richiedente asilo", "domanda di asilo"],
        "sections": ["AsylG § 61 Abs. 1", "AsylG § 61 Abs. 2"]},
    "duldung": {
        "ko": ["체류 유예", "둘둥"], "en": ["duldung", "tolerated stay"], "de": ["duldung", "geduldet"],
        "ar": ["دولدونغ", "إقامة التسامح"], "it": ["duldung", "tollerat"],
        "sections": ["AufenthG § 60c Abs. 1", "BeschV § 32 Abs. 1"]},
    "extension_pending": {
        "ko": ["연장 신청", "만료됐는데", "만료되었는데"], "en": ["extension", "expired"],
        "de": ["verlängerung beantragt", "abgelaufen"], "ar": ["طلب التمديد", "انتهت صلاحية"], "it": ["proroga", "scadut"],
        "sections": ["AufenthG § 81 Abs. 4", "AufenthG § 81 Abs. 5"]},
    "long_absence": {
        "ko": ["고국에 몇", "몇개월 이상 있으면", "몇 개월 이상 있으면", "해외에 오래"], "en": ["abroad for", "months abroad", "leave germany for"],
        "de": ["im ausland", "monate ins ausland"], "ar": ["خارج ألمانيا", "برّا ألمانيا لمدة"],
        "it": ["all'estero per", "mesi all'estero"],
        "sections": ["AufenthG § 51 Abs. 1", "AufenthG § 51 Abs. 2", "AufenthG § 51 Abs. 10"]},
    "public_funds": {
        "ko": ["실업급여", "실업금여", "수당을 받"], "en": ["unemployment benefit", "social benefits"],
        "de": ["arbeitslosengeld", "sozialleistungen"], "ar": ["إعانة البطالة", "مساعدات اجتماعية"],
        "it": ["indennità di disoccupazione", "sussidi"],
        "sections": ["AufenthG § 2 Abs. 3"]},
    "research_phd": {
        "ko": ["박사", "연구원"], "en": ["phd", "doctoral", "researcher"], "de": ["promotion", "doktorand", "forscher"],
        "ar": ["دكتوراه", "باحث"], "it": ["dottorato", "ricercator"],
        "sections": ["AufenthG § 18d Abs. 1", "AufenthG § 16b Abs. 1"]},
    "internship": {
        "ko": ["인턴"], "en": ["internship", "intern"], "de": ["praktikum"], "ar": ["تدريب عملي", "انترنشيب"],
        "it": ["tirocinio", "stage"],
        "sections": ["BeschV § 15", "AufenthG § 16e"]},
    "landlord": {
        "ko": ["집주인"], "en": ["landlord"], "de": ["vermieter", "wohnungsgeber"], "ar": ["صاحب البيت", "المؤجر"],
        "it": ["padrone di casa", "proprietario di casa"],
        "sections": ["BMG § 19 Abs. 1", "BMG § 54 Abs. 2"]},
    "name_change": {
        "ko": ["이름 바꾸", "이름을 바꾸", "개명"], "en": ["name change", "change my name", "changed my name"],
        "de": ["namensänderung", "namen geändert"], "ar": ["تغيير الاسم", "غيرت اسمي"], "it": ["cambio di nome", "cambiato nome"],
        "sections": ["AufenthV § 72 Abs. 1"]},
    "remote_work": {
        "ko": ["원격"], "en": ["remote", "remotely"], "de": ["remote", "fernarbeit"], "ar": ["عن بعد"], "it": ["da remoto"],
        "sections": ["AufenthG § 4a Abs. 1", "EStG § 1 Abs. 1"]},
    "business_trip": {
        "ko": ["출장"], "en": ["business trip"], "de": ["geschäftsreise", "dienstreise"], "ar": ["رحلة عمل", "سفرة شغل"],
        "it": ["viaggio di lavoro", "trasferta"],
        "sections": ["BeschV § 16", "BeschV § 30", "AufenthV § 17 Abs. 2"]},
    "athlete": {
        "ko": ["축구", "운동선수", "구단"], "en": ["football club", "athlete", "sports club"],
        "de": ["fußballverein", "sportler", "sportverein"], "ar": ["كرة القدم", "رياضي", "نادي رياضي"],
        "it": ["squadra di calcio", "atleta"],
        "sections": ["BeschV § 22", "AufenthV § 17 Abs. 1"]},
    "schengen_travel": {
        "ko": ["독일 비자로", "여행갈", "여행 가"], "en": ["schengen", "travel to"], "de": ["schengen", "reisen nach"],
        "ar": ["شنغن", "السفر إلى"], "it": ["schengen", "viaggiare in"],
        "sections": ["AufenthG § 6 Abs. 1"]},
    "tax_deduction": {
        "ko": ["공제"], "en": ["deduct", "deductible"], "de": ["absetzen", "werbungskosten"], "ar": ["خصم من الضريبة", "اقتطاع"],
        "it": ["detrarre", "detrazione"],
        "sections": ["EStG § 9 Abs. 1", "EStG § 10 Abs. 1"]},
    "home_office": {
        "ko": ["재택근무"], "en": ["home office", "working from home"], "de": ["homeoffice", "arbeitszimmer"],
        "ar": ["العمل من البيت", "العمل من المنزل"], "it": ["telelavoro", "lavoro da casa"],
        "sections": ["EStG § 4 Abs. 5", "EStG § 9 Abs. 5"]},
    "side_job": {
        "ko": ["부업"], "en": ["side job", "second job"], "de": ["nebenjob", "nebentätigkeit"], "ar": ["شغل جانبي", "وظيفة جانبية"],
        "it": ["secondo lavoro"],
        "sections": ["EStG § 46 Abs. 3", "EStG § 3", "EStG § 40a Abs. 2"]},
    "capital_income": {
        "ko": ["주식"], "en": ["stocks", "shares", "dividends"], "de": ["aktien", "dividende"], "ar": ["أسهم", "الأسهم"],
        "it": ["azioni", "dividendi"],
        "sections": ["EStG § 32d Abs. 1", "EStG § 20 Abs. 2", "EStG § 32d Abs. 5"]},
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
