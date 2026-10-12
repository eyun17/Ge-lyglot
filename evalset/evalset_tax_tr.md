# Tax and pension module — Turkish (15 items)

- t01–t03 were written by the project owner; t04–t15 come from the agreed idea list.
- Gold sections were checked against the statute text (EStG, AO, SGB IV, SGB VI as of 2026-10-09; AufenthG as of 2026-10-08) but are not yet `verified`.
- t05–t07 name the asker's country and are localized per set (`localized: true`); for Italian (EU) t05 and t06 have different correct answers, see notes.
- Terms are written the way the community usually writes them (Werkstudent, HiWi, Minijob, Kindergeld, Steuer-ID).
- Translated from Korean; not yet reviewed by a native speaker.

| id | type | expected | gold | English | Turkish | notes |
|---|---|---|---|---|---|---|
| t01 | Multiple sections | `answer` | AufenthG § 21 Abs. 5, AO § 138 Abs. 1, EStG § 18 Abs. 1 | Can I work as a freelancer in Germany? If so, do I have to register somewhere first? | Almanya'da freelancer olarak çalışabilir miyim? Çalışacaksam önce bir yere kayıt yaptırmam gerekiyor mu? | 체류허가(§ 21 Abs. 5 프리랜서) + 세무서 신고(AO § 138 Abs. 1 Satz 3) + 프리랜서 소득 정의(EStG § 18). 영업 신고(GewO)는 코퍼스 밖 |
| t02 | Multiple sections | `answer` | SGB VI § 1, SGB VI § 6 Abs. 1b, SGB IV § 28e Abs. 1 | Do Werkstudents and HiWis have to pay into the pension insurance? Or does the company or university take care of it? | Werkstudent'ler ve HiWi'ler emeklilik sigortası ödemek zorunda mı? Yoksa şirket ya da üniversite bunu kendisi mi hallediyor? | 베르크스튜던트는 연금보험 의무(§ 5 Abs. 3 예외는 필수 실습만). 히비가 미니잡이면 § 6 Abs. 1b로 면제 신청 가능. 보험료는 고용주가 납부(SGB IV § 28e). 건강·실업보험 특례(SGB V/III)는 코퍼스 밖 |
| t03 | Multiple sections | `answer` | EStG § 46 Abs. 2, SGB VI § 210 Abs. 1, SGB VI § 210 Abs. 2 | Can I get back the taxes I paid when I go back home? | Ödediğim vergileri ülkeme dönerken geri alabilir miyim? | 전제가 반만 맞음: 세금은 출국으로 환급되지 않고 신고(§ 46 Abs. 2)로 과다 원천징수분 환급. 연금보험료는 § 210(의무 종료 후 24개월). 사회보장협정은 코퍼스 밖 |
| t04 | Multiple sections | `answer` | EStG § 1 Abs. 1, AO § 9 | How many months do I have to live in Germany before I have to pay tax here? | Almanya'da vergi ödemem için burada kaç ay yaşamış olmam gerekiyor? | AO § 9 Satz 2: 6개월 넘게 머물면 상시 거주 |
| t05 | Multiple sections | `answer` | EStG § 26 Abs. 1, EStG § 1a Abs. 1 | My spouse lives in Turkey. Can we be taxed jointly in Germany? | Eşim Türkiye'de yaşıyor. Almanya'da eşimle birlikte ortak vergilendirilebilir miyiz? | § 26 Abs. 1은 부부 모두 무제한 납세의무자일 것을 요구. § 1a Abs. 1 Nr. 2 특례는 EU·EEA 국적자이고 배우자가 EU·EEA에 살 때만 |
| t06 | Multiple sections | `answer` | EStG § 62 Abs. 1, EStG § 62 Abs. 2 | I'm a Turkish citizen. Can I get Kindergeld in Germany? | Türk vatandaşıyım. Almanya'da Kindergeld alabilir miyim? | 비EU 외국인은 § 62 Abs. 2의 체류허가 요건. EU 시민은 Abs. 2 대상이 아님 |
| t07 | Single section | `answer` | EStG § 34c Abs. 1 | I also have income in Turkey. Do I have to pay tax on it in both countries? | Türkiye'de de gelirim var. İki ülkede de vergi ödemek zorunda mıyım? | 외국 세액 공제. 이중과세방지협정은 코퍼스 밖이라 그 부분은 밝히고 답할 것 |
| t08 | Single section | `answer` | AO § 139b | When I first come to Germany, how do I get a Steuer-ID? | Almanya'ya ilk geldiğimde Steuer-ID'yi nasıl alırım? | 세금 식별번호 |
| t09 | Multiple sections | `answer` | EStG § 40a Abs. 2, SGB IV § 8 Abs. 1 | Is the money I earn from a Minijob taxed? | Minijob'dan kazandığım paradan da vergi kesiliyor mu? | 미니잡 정의 + 2% 일괄 과세 |
| t10 | Single section | `answer` | AufenthG § 9 Abs. 2 | If I don't pay into the pension insurance, can I still get permanent residence? | Emeklilik sigortası ödemezsem süresiz oturum izni alamaz mıyım? | § 9 Abs. 2 Nr. 3: 60개월 연금보험료. 블루카드 등 다른 경로는 별도 요건 |
| t11 | Multiple sections | `answer` | EStG § 46 Abs. 2, AO § 149 Abs. 2 | Do I have to file a tax return? If so, what is the deadline? | Vergi beyannamesi vermek zorunda mıyım? Zorundaysam son tarih ne zaman? | 신고 의무가 생기는 경우 + 기한 |
| t12 | Refusal | `refuse_out_of_scope` | — | Do I have to have health insurance in Germany? | Almanya'da sağlık sigortası yaptırmak zorunlu mu? | 건강보험(SGB V)은 코퍼스 밖 |
| t13 | Refusal | `refuse_out_of_scope` | — | Is the Rundfunkbeitrag a tax? Do I have to pay it? | GEZ ücreti bir vergi mi? Ödemek zorunda mıyım? | 방송 수신료는 세금이 아님(방송수신료 국가협약), 코퍼스 밖 |
| t14 | Refusal | `explain_without_judgment` | EStG § 32a Abs. 1 | My salary is 50,000 euros a year. Exactly how much tax will I pay? | Yıllık maaşım 50.000 avro. Tam olarak ne kadar vergi ödeyeceğim? | 세율 구조는 설명하되 개인 세액을 계산·단정하지 않는다 |
| t15 | Refusal | `explain_without_judgment` | AO § 347 Abs. 1, AO § 355 Abs. 1 | The tax office made a decision that seems wrong to me, and I want to object. Will I win? | Vergi dairesinin verdiği karar bana yanlış görünüyor, itiraz etmek istiyorum. Kazanır mıyım? | 이의 신청 제도와 1개월 기한을 안내하고 승소 가능성은 판단하지 않는다 |
