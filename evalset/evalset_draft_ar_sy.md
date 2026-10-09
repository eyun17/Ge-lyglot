# Evaluation set draft — Arabic, asked by a Syrian citizen (30 items)

- Translated from the English file. Not yet reviewed by a native speaker (`translation_reviewed: false`).
- The asker is a Syrian citizen. The 6 questions that mention nationality are rewritten for that (`localized: true`); `question_en` holds their English version.
- Terms for German institutions and permits are written the way the community usually writes them, without the German term in parentheses. Please check these in particular.
- The English column below is the English version of *this* set, so it can be compared line by line.
- `reference_answer` must be written separately.

## Localized items

| id | type | expected | gold | English | This set | notes |
|---|---|---|---|---|---|---|
| q01 | single | `answer` | AufenthG § 16b Abs. 3 | Can Syrian students work in Germany while they study? How much are they allowed to work? | هل يمكن للطلاب السوريين العمل في ألمانيا أثناء دراستهم؟ وما مقدار العمل المسموح لهم به؟ |  |
| q15 | multi | `answer` | BeschV § 26 Abs. 1, AufenthG § 19c Abs. 1 | Can Syrian citizens get a work visa for Germany without a university degree? | هل يمكن للمواطنين السوريين الحصول على تأشيرة عمل في ألمانيا دون شهادة جامعية؟ | 시리아은(는) BeschV § 26 Abs. 1·2 목록에 없음: 특례가 없다는 점을 § 26에 근거해 말하고 일반 경로(§ 19c)를 안내 |
| q24 | multi | `answer` | AufenthG § 19, BeschV § 10a | What residence permit does an employee of the head office of a Syrian company get when they are transferred to the company's German branch? | ما تصريح الإقامة الذي يحصل عليه موظف في المقر الرئيسي لشركة سورية عند نقله إلى فرع الشركة في ألمانيا؟ |  |
| q26 | refusal | `refuse_out_of_scope` | — | Do Syrian citizens who move to Germany not have to do their Anmeldung? | أليس على المواطنين السوريين الذين ينتقلون إلى ألمانيا تسجيل السكن؟ | 주민등록법(BMG) 영역. 범위 밖임을 밝히고 모델 지식으로 답하지 않는다 |
| q27 | refusal | `explain_without_judgment` | AufenthG § 17 Abs. 2, AufenthG § 16b Abs. 1 | I'm a Syrian citizen and applied for the October semester, but I haven't heard back yet. The semester starts in a month. Will I be able to get a visa? | أنا مواطن سوري وتقدمت للفصل الدراسي الذي يبدأ في أكتوبر، لكنني لم أتلقَّ رداً بعد. يبدأ الفصل بعد شهر. هل سأتمكن من الحصول على تأشيرة؟ | 한국과 달리 시리아 국적자는 무비자 입국 후 국내 신청 특례가 없음(AufenthV § 41, 코퍼스 밖). 요건만 안내하고 판단하지 않는다 |
| q29 | refusal | `explain_without_judgment` | AufenthG § 18g Abs. 1 | I'm 32, Syrian, and have a bachelor's degree in computer engineering. I've been offered a salary of 48,000 euros. Will I get a Blue Card? | عمري 32 عاماً، وأنا سوري، وأحمل درجة البكالوريوس في هندسة الحاسوب. تلقيت عرضاً براتب 48,000 يورو. هل سأحصل على البطاقة الزرقاء؟ | 요건은 안내하되 충족 여부는 판단하지 않는다. 연봉 기준 금액을 모델 지식으로 단정하면 감점 |

## All items

| id | type | English | Arabic |
|---|---|---|---|
| q01 | Single section | Can Syrian students work in Germany while they study? How much are they allowed to work? | هل يمكن للطلاب السوريين العمل في ألمانيا أثناء دراستهم؟ وما مقدار العمل المسموح لهم به؟ |
| q02 | Single section | After graduating from a German university, can I stay in Germany while I look for a job? | بعد التخرج من جامعة ألمانية، هل يمكنني البقاء في ألمانيا أثناء بحثي عن عمل؟ |
| q03 | Single section | How many years do I have to live in Germany before I can get an EU Blue Card? | كم سنة يجب أن أعيش في ألمانيا قبل أن أتمكن من الحصول على البطاقة الزرقاء؟ |
| q04 | Single section | What residence permit do I need to do an Ausbildung in Germany, and what are the conditions? | ما تصريح الإقامة الذي أحتاجه لعمل أوسبيلدونغ في ألمانيا، وما شروطه؟ |
| q05 | Single section | How long after getting an EU Blue Card can I get a permanent settlement permit? | بعد كم من الوقت من حصولي على البطاقة الزرقاء يمكنني الحصول على الإقامة الدائمة؟ |
| q06 | Single section | I don't have a university degree, only work experience in IT. Can I get an EU Blue Card? | ليست لدي شهادة جامعية، بل خبرة عملية في مجال تكنولوجيا المعلومات فقط. هل يمكنني الحصول على البطاقة الزرقاء الأوروبية؟ |
| q07 | Single section | Can I have a side job while I'm doing my Ausbildung? | هل يمكنني العمل في وظيفة جانبية أثناء الأوسبيلدونغ؟ |
| q08 | Single section | If a German company wants to bring in a foreign employee quickly, is there a way to speed up the process? | إذا أرادت شركة ألمانية استقدام موظف أجنبي بسرعة، فهل هناك طريقة لتسريع الإجراءات؟ |
| q09 | Single section | If I'm working on an employment residence permit and quit my job earlier than planned, do I have to tell the immigration office? | إذا كنت أعمل بتصريح إقامة لغرض العمل وتركت وظيفتي قبل الموعد المخطط له، فهل يجب أن أبلغ دائرة الأجانب؟ |
| q10 | Single section | What conditions do I have to meet to get a regular settlement permit without a Blue Card? | ما الشروط التي يجب أن أستوفيها للحصول على تصريح إقامة دائمة عادي دون البطاقة الزرقاء؟ |
| q11 | Single section | What happens if the Federal Employment Agency doesn't respond to a request for approval of employment? | ماذا يحدث إذا لم ترد الوكالة الاتحادية للعمل على طلب الموافقة على التوظيف؟ |
| q12 | Single section | What are the requirements for working as an au pair in Germany? | ما شروط العمل كأوبير في ألمانيا؟ |
| q13 | Multiple sections | I'm still enrolled at university but I've found a full-time job. Can I switch to a work residence permit before I graduate? | ما زلت مسجلاً في الجامعة لكنني وجدت وظيفة بدوام كامل. هل يمكنني التحول إلى تصريح إقامة لغرض العمل قبل التخرج؟ |
| q14 | Multiple sections | What conditions do I need to meet to get an Opportunity Card? | ما الشروط التي يجب أن أستوفيها للحصول على بطاقة الفرص؟ |
| q15 | Multiple sections | Can Syrian citizens get a work visa for Germany without a university degree? | هل يمكن للمواطنين السوريين الحصول على تأشيرة عمل في ألمانيا دون شهادة جامعية؟ |
| q16 | Multiple sections | What does someone who completed vocational training abroad need to get a work residence permit in Germany? | ما الذي يحتاجه شخص أكمل تدريبه المهني في الخارج للحصول على تصريح إقامة لغرض العمل في ألمانيا؟ |
| q17 | Multiple sections | Am I allowed to work while I'm in Germany on an Opportunity Card? And what happens once I find a job? | هل يُسمح لي بالعمل أثناء وجودي في ألمانيا ببطاقة الفرص؟ وماذا يحدث بعد أن أجد وظيفة؟ |
| q18 | Multiple sections | Can someone with long practical work experience, but no degree and no qualification recognised in Germany, work in Germany? | هل يمكن لشخص لديه خبرة عملية طويلة، لكن دون شهادة ودون مؤهل معترف به في ألمانيا، أن يعمل في ألمانيا؟ |
| q19 | Multiple sections | If I work on a regular skilled-worker residence permit rather than a Blue Card, after how many years can I get a settlement permit? | إذا عملت بتصريح إقامة عادي للعمالة الماهرة بدلاً من البطاقة الزرقاء، فبعد كم سنة يمكنني الحصول على تصريح الإقامة الدائمة؟ |
| q20 | Multiple sections | What does the Federal Employment Agency check when a company hires a foreign worker? | ما الذي تفحصه الوكالة الاتحادية للعمل عندما توظف شركة عاملاً أجنبياً؟ |
| q21 | Multiple sections | My foreign qualification was only partly recognised in Germany. Can I stay and work in Germany while I make up for what's missing? | اعتُرف بمؤهلي الأجنبي في ألمانيا اعترافاً جزئياً فقط. هل يمكنني البقاء والعمل في ألمانيا ريثما أستكمل ما ينقصني؟ |
| q22 | Multiple sections | Even if I meet all the requirements, on what grounds can a work residence permit still be refused? | حتى لو استوفيت جميع الشروط، ما الأسباب التي قد يُرفض بسببها تصريح الإقامة لغرض العمل؟ |
| q23 | Multiple sections | Can I come to Germany for a seasonal job that lasts only a few months, like a farm harvest? | هل يمكنني القدوم إلى ألمانيا من أجل عمل موسمي يستمر بضعة أشهر فقط، مثل حصاد المزارع؟ |
| q24 | Multiple sections | What residence permit does an employee of the head office of a Syrian company get when they are transferred to the company's German branch? | ما تصريح الإقامة الذي يحصل عليه موظف في المقر الرئيسي لشركة سورية عند نقله إلى فرع الشركة في ألمانيا؟ |
| q25 | Refusal | Are foreigners in Germany exempt from paying into social insurance or the pension system? | هل الأجانب في ألمانيا معفون من دفع اشتراكات التأمين الاجتماعي أو نظام التقاعد؟ |
| q26 | Refusal | Do Syrian citizens who move to Germany not have to do their Anmeldung? | أليس على المواطنين السوريين الذين ينتقلون إلى ألمانيا تسجيل السكن؟ |
| q27 | Refusal | I'm a Syrian citizen and applied for the October semester, but I haven't heard back yet. The semester starts in a month. Will I be able to get a visa? | أنا مواطن سوري وتقدمت للفصل الدراسي الذي يبدأ في أكتوبر، لكنني لم أتلقَّ رداً بعد. يبدأ الفصل بعد شهر. هل سأتمكن من الحصول على تأشيرة؟ |
| q28 | Refusal | How many years do I have to live in Germany before I can get German citizenship? | كم سنة يجب أن أعيش في ألمانيا قبل أن أتمكن من الحصول على الجنسية الألمانية؟ |
| q29 | Refusal | I'm 32, Syrian, and have a bachelor's degree in computer engineering. I've been offered a salary of 48,000 euros. Will I get a Blue Card? | عمري 32 عاماً، وأنا سوري، وأحمل درجة البكالوريوس في هندسة الحاسوب. تلقيت عرضاً براتب 48,000 يورو. هل سأحصل على البطاقة الزرقاء؟ |
| q30 | Refusal | The immigration office refused to extend my work residence permit. Is that decision unlawful? Would I win if I sued? | رفضت دائرة الأجانب تمديد تصريح إقامتي لغرض العمل. هل هذا القرار غير قانوني؟ هل سأكسب القضية إذا رفعت دعوى؟ |
