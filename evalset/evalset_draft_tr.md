# Evaluation set draft — Turkish, asked by a Turkish citizen (30 items)

- Translated from the English file. Not yet reviewed by a native speaker (`translation_reviewed: false`).
- The asker is a Turkish citizen. The 6 questions that mention nationality are rewritten for that (`localized: true`); `question_en` holds their English version.
- Terms for German institutions and permits are written the way the community usually writes them, without the German term in parentheses. Please check these in particular.
- The English column below is the English version of *this* set, so it can be compared line by line.
- `reference_answer` must be written separately.

## Localized items

| id | type | expected | gold | English | This set | notes |
|---|---|---|---|---|---|---|
| q01 | single | `answer` | AufenthG § 16b Abs. 3 | Can Turkish students work in Germany while they study? How much are they allowed to work? | Türk öğrenciler Almanya'da okurken çalışabilir mi? Ne kadar çalışmalarına izin veriliyor? |  |
| q15 | multi | `answer` | BeschV § 26 Abs. 1, AufenthG § 19c Abs. 1 | Can Turkish citizens get a work visa for Germany without a university degree? | Türk vatandaşları üniversite diploması olmadan Almanya için çalışma vizesi alabilir mi? | 튀르키예은(는) BeschV § 26 Abs. 1·2 목록에 없음: 특례가 없다는 점을 § 26에 근거해 말하고 일반 경로(§ 19c)를 안내. 연합협정(ARB 1/80)은 코퍼스 밖 |
| q24 | multi | `answer` | AufenthG § 19, BeschV § 10a | What residence permit does an employee of a company's head office in Turkey get when they are transferred to the company's German branch? | Türkiye'deki merkez ofisin bir çalışanı şirketin Almanya şubesine görevlendirildiğinde hangi oturum iznini alır? |  |
| q26 | refusal | `refuse_out_of_scope` | — | Do Turkish citizens who move to Germany not have to do their Anmeldung? | Almanya'ya taşınan Türk vatandaşlarının Anmeldung yaptırması gerekmiyor mu? | 주민등록법(BMG) 영역. 범위 밖임을 밝히고 모델 지식으로 답하지 않는다 |
| q27 | refusal | `explain_without_judgment` | AufenthG § 17 Abs. 2, AufenthG § 16b Abs. 1 | I'm a Turkish citizen and applied for the October semester, but I haven't heard back yet. The semester starts in a month. Will I be able to get a visa? | Türk vatandaşıyım ve Ekim dönemi için başvurdum ama henüz yanıt alamadım. Dönemin başlamasına bir ay var. Vize alabilecek miyim? | 한국과 달리 튀르키예 국적자는 무비자 입국 후 국내 신청 특례가 없음(AufenthV § 41, 코퍼스 밖). 요건만 안내하고 판단하지 않는다 |
| q29 | refusal | `explain_without_judgment` | AufenthG § 18g Abs. 1 | I'm 32, a Turkish citizen, and have a bachelor's degree in computer engineering. I've been offered a salary of 48,000 euros. Will I get a Blue Card? | 32 yaşındayım, Türk vatandaşıyım ve bilgisayar mühendisliği alanında lisans diplomam var. 48.000 avro maaş teklifi aldım. Mavi Kart alabilir miyim? | 요건은 안내하되 충족 여부는 판단하지 않는다. 연봉 기준 금액을 모델 지식으로 단정하면 감점 |

## All items

| id | type | English | Turkish |
|---|---|---|---|
| q01 | Single section | Can Turkish students work in Germany while they study? How much are they allowed to work? | Türk öğrenciler Almanya'da okurken çalışabilir mi? Ne kadar çalışmalarına izin veriliyor? |
| q02 | Single section | After graduating from a German university, can I stay in Germany while I look for a job? | Bir Alman üniversitesinden mezun olduktan sonra iş ararken Almanya'da kalmaya devam edebilir miyim? |
| q03 | Single section | How many years do I have to live in Germany before I can get an EU Blue Card? | Mavi Kart alabilmek için Almanya'da kaç yıl yaşamış olmam gerekiyor? |
| q04 | Single section | What residence permit do I need to do an Ausbildung in Germany, and what are the conditions? | Almanya'da Ausbildung yapmak için hangi oturum iznine ihtiyacım var ve koşulları neler? |
| q05 | Single section | How long after getting an EU Blue Card can I get a permanent settlement permit? | Mavi Kart aldıktan ne kadar süre sonra süresiz oturum izni alabilirim? |
| q06 | Single section | I don't have a university degree, only work experience in IT. Can I get an EU Blue Card? | Üniversite diplomam yok, sadece bilişim alanında iş deneyimim var. AB Mavi Kartı alabilir miyim? |
| q07 | Single section | Can I have a side job while I'm doing my Ausbildung? | Ausbildung sırasında yan iş yapabilir miyim? |
| q08 | Single section | If a German company wants to bring in a foreign employee quickly, is there a way to speed up the process? | Bir Alman şirketi yabancı bir çalışanı hızlıca getirmek isterse süreci hızlandırmanın bir yolu var mı? |
| q09 | Single section | If I'm working on an employment residence permit and quit my job earlier than planned, do I have to tell the immigration office? | Çalışma amaçlı oturum izniyle çalışırken işimden planlanandan erken ayrılırsam yabancılar dairesine bildirmem gerekir mi? |
| q10 | Single section | What conditions do I have to meet to get a regular settlement permit without a Blue Card? | Mavi Kart olmadan normal bir yerleşim izni almak için hangi koşulları sağlamam gerekiyor? |
| q11 | Single section | What happens if the Federal Employment Agency doesn't respond to a request for approval of employment? | Federal İş Ajansı bir çalışma onayı talebine yanıt vermezse ne olur? |
| q12 | Single section | What are the requirements for working as an au pair in Germany? | Almanya'da au pair olarak çalışmanın koşulları nelerdir? |
| q13 | Multiple sections | I'm still enrolled at university but I've found a full-time job. Can I switch to a work residence permit before I graduate? | Hâlâ üniversiteye kayıtlıyım ama tam zamanlı bir iş buldum. Mezun olmadan önce çalışma amaçlı oturum iznine geçebilir miyim? |
| q14 | Multiple sections | What conditions do I need to meet to get an Opportunity Card? | Fırsat Kartı almak için hangi koşulları sağlamam gerekiyor? |
| q15 | Multiple sections | Can Turkish citizens get a work visa for Germany without a university degree? | Türk vatandaşları üniversite diploması olmadan Almanya için çalışma vizesi alabilir mi? |
| q16 | Multiple sections | What does someone who completed vocational training abroad need to get a work residence permit in Germany? | Mesleki eğitimini yurt dışında tamamlamış biri Almanya'da çalışma amaçlı oturum izni almak için neye ihtiyaç duyar? |
| q17 | Multiple sections | Am I allowed to work while I'm in Germany on an Opportunity Card? And what happens once I find a job? | Fırsat Kartı ile Almanya'dayken çalışmama izin var mı? Bir iş bulduğumda ne olur? |
| q18 | Multiple sections | Can someone with long practical work experience, but no degree and no qualification recognised in Germany, work in Germany? | Diploması ve Almanya'da tanınmış bir mesleki yeterliliği olmayan ama uzun süreli pratik iş deneyimi olan biri Almanya'da çalışabilir mi? |
| q19 | Multiple sections | If I work on a regular skilled-worker residence permit rather than a Blue Card, after how many years can I get a settlement permit? | Mavi Kart yerine normal bir nitelikli işgücü oturum izniyle çalışırsam kaç yıl sonra yerleşim izni alabilirim? |
| q20 | Multiple sections | What does the Federal Employment Agency check when a company hires a foreign worker? | Bir şirket yabancı bir çalışanı işe aldığında Federal İş Ajansı neleri inceler? |
| q21 | Multiple sections | My foreign qualification was only partly recognised in Germany. Can I stay and work in Germany while I make up for what's missing? | Yurt dışında aldığım mesleki yeterlilik Almanya'da yalnızca kısmen tanındı. Eksiklerimi tamamlarken Almanya'da kalıp çalışabilir miyim? |
| q22 | Multiple sections | Even if I meet all the requirements, on what grounds can a work residence permit still be refused? | Tüm koşulları sağlasam bile çalışma amaçlı oturum izni hangi gerekçelerle reddedilebilir? |
| q23 | Multiple sections | Can I come to Germany for a seasonal job that lasts only a few months, like a farm harvest? | Tarladaki hasat gibi yalnızca birkaç ay süren mevsimlik bir iş için Almanya'ya gelebilir miyim? |
| q24 | Multiple sections | What residence permit does an employee of a company's head office in Turkey get when they are transferred to the company's German branch? | Türkiye'deki merkez ofisin bir çalışanı şirketin Almanya şubesine görevlendirildiğinde hangi oturum iznini alır? |
| q25 | Refusal | Are foreigners in Germany exempt from paying into social insurance or the pension system? | Almanya'daki yabancılar sosyal sigorta veya emeklilik sistemine prim ödemekten muaf mı? |
| q26 | Refusal | Do Turkish citizens who move to Germany not have to do their Anmeldung? | Almanya'ya taşınan Türk vatandaşlarının Anmeldung yaptırması gerekmiyor mu? |
| q27 | Refusal | I'm a Turkish citizen and applied for the October semester, but I haven't heard back yet. The semester starts in a month. Will I be able to get a visa? | Türk vatandaşıyım ve Ekim dönemi için başvurdum ama henüz yanıt alamadım. Dönemin başlamasına bir ay var. Vize alabilecek miyim? |
| q28 | Refusal | How many years do I have to live in Germany before I can get German citizenship? | Alman vatandaşlığı alabilmek için Almanya'da kaç yıl yaşamam gerekiyor? |
| q29 | Refusal | I'm 32, a Turkish citizen, and have a bachelor's degree in computer engineering. I've been offered a salary of 48,000 euros. Will I get a Blue Card? | 32 yaşındayım, Türk vatandaşıyım ve bilgisayar mühendisliği alanında lisans diplomam var. 48.000 avro maaş teklifi aldım. Mavi Kart alabilir miyim? |
| q30 | Refusal | The immigration office refused to extend my work residence permit. Is that decision unlawful? Would I win if I sued? | Yabancılar dairesi çalışma amaçlı oturum iznimin uzatılmasını reddetti. Bu karar hukuka aykırı mı? Dava açarsam kazanır mıyım? |
