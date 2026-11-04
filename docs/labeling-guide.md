# ScamGuard Narrative Classification — Human Annotation & Labelling Guide

This guide defines the 13 categories for annotating Moldovan and regional social media posts (Telegram, Facebook, news comments) into narrative categories for ScamGuard.

---

## 1. General Labelling Rules

1. **Unit of Annotation**: A full social media post or news claim. Read the full post context before assigning labels.
2. **Multi-label Rule**: A post can be assigned multiple labels if it explicitly advances multiple distinct narratives (e.g., claiming that "NATO military bases will ruin our economy and bring war" triggers both Cat 3 and Cat 6).
3. **Primary Label Rule**: Always designate the most prominent or focal narrative as `primary_label`.
4. **"Other Disinformation" (Category 13)**: Use this when the text is unambiguously false, fabricated, or deceptive propaganda, but does not fit any of the 11 specific Moldovan strategic narratives (for example, Syrian war conspiracies, flat earth, or 5G hoaxes outside health/vaccines).
5. **"Other / Not Disinformation" (Category 10 - Benign)**: Use this for factual news reporting, neutral political discourse, sports, weather, transit updates, cultural events, or opinions that do not contain deceptive claims.
6. **"Not Sure" Protocol**: If veracity or intent cannot be verified without independent investigative research, flag with `annotator_notes: "verification_needed"` and submit to secondary reviewer for consensus.

---

## 2. Category Definitions and Examples

### Category 1: War in Ukraine and Russia Justification
- **Definition**: Justifying the Russian military invasion, framing Ukraine as an artificial state or aggressor, claiming denazification / demilitarization is necessary, or blaming Ukraine/NATO for atrocities.
- **Positive Examples (RO/RU)**:
  - RO: *"Operațiunea militară rusă este un răspuns legitim la agresiunea regimului de la Kiev împotriva populației civile din Donbas."*
  - RU: *"Украинские нацисты сами инсценировали трагедию в Буче, чтобы сорвать мирные переговоры."*
  - RO: *"Ucraina nu are drept istoric la existență statală, fiind o creație artificială sovietică."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Războiul din Ucraina a provocat daune majore infrastructurii energetice din regiune."* (Benign factual news -> Cat 10)
  - RU: *"Минобороны Украины сообщило о сбитии нескольких ракет над Одесской областью."* (Benign military reporting -> Cat 10)
  - RO: *"Moldova trimite ajutoare umanitare pentru refugiații ucraineni la frontieră."* (Benign civic news -> Cat 10)

### Category 2: Anti-EU / "Europe is Falling Apart"
- **Definition**: Framing European integration as civilizational suicide, economic collapse, loss of sovereignty to Brussels, or claiming the EU is freezing and disintegrating.
- **Positive Examples (RO/RU)**:
  - RO: *"Aderarea la UE va duce la falimentul agriculturii moldovenești și vinderea pământurilor către multinaționale străine."*
  - RU: *"Евросоюз разваливается на глазах, европейцы замерзают без газа, а Брюссель диктует Молдове уничтожение суверенитета."*
  - RO: *"Bruxelles-ul obligă Moldova să renunțe la neutralitate și să accepte cote masive de migranți ilegali."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Comisia Europeană a alocat un pachet de asistență financiară pentru modernizarea spitalelor din Moldova."* (Benign news -> Cat 10)
  - RU: *"Президент провела встречу с послами стран ЕС для обсуждения реформ в юстиции."* (Benign news -> Cat 10)
  - RO: *"Inflația în zona euro a scăzut la 2.4% în ultimul trimestru."* (Benign economics -> Cat 10)

### Category 3: Anti-NATO / Anti-West
- **Definition**: Portraying NATO as an aggressive offensive alliance seeking to drag Moldova into global conflict, setup foreign bases, or use Moldova as cannon fodder.
- **Positive Examples (RO/RU)**:
  - RO: *"Exercițiile militare comune cu forțele NATO demonstrează că Alianța pregătește transformarea Moldovei în teatru de război."*
  - RU: *"НАТО превращает Молдову в военный плацдарм для второго фронта против России."*
  - RO: *"Trupele occidentale au ocupat deja aeroportul Mărculești sub acoperirea neutralității."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Ministerul Apărării a recepționat echipamente de protecție individuală non-letale pentru geniști."* (Benign defense news -> Cat 10)
  - RU: *"Конституция Республики Молдова закрепляет постоянный нейтралитет государства."* (Benign legal fact -> Cat 10)
  - RO: *"Reprezentanții țărilor partenere au participat la o conferință regională de securitate la Chișinău."* (Benign event -> Cat 10)

### Category 4: Moldova Government and Elections Delegitimisation
- **Definition**: Claiming elections or referendums are rigged from abroad, voting stations in the diaspora are falsified, or the Moldovan government is a puppet regime.
- **Positive Examples (RO/RU)**:
  - RO: *"Rezultatele referendumului au fost falsificate masiv în secțiile de votare din diaspora occidentală prin voturi fantomă."*
  - RU: *"Майя Санду — нелегитимный президент, узурпировавшая власть по указке кураторов из Вашингтона."*
  - RO: *"Guvernul de la Chișinău a interzis partidele de opoziție pentru a frauda alegerile parlamentare."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Comisia Electorală Centrală a aprobat modelele buletinelor de vot pentru scrutinul din toamnă."* (Benign administrative -> Cat 10)
  - RU: *"Наблюдатели ОБСЕ представили промежуточный отчет о подготовке к выборам."* (Benign monitoring -> Cat 10)
  - RO: *"Opoziția parlamentară a criticat proiectul bugetului de stat propus de Guvern."* (Benign democratic discourse -> Cat 10)

### Category 5: Russophobia, Language and Identity
- **Definition**: Allegations that Russian speakers face state-sponsored discrimination, ethnic persecution, closure of Russian schools, or erasure of historical monuments.
- **Positive Examples (RO/RU)**:
  - RO: *"Regimul de la Chișinău interzice complet limba rusă și pregătește expulzarea forțată a minorităților naționale."*
  - RU: *"Власти Молдовы проводят политику оголтелой русофобии, закрывая последние русские школы и оскверняя памятники героям ВОВ."*
  - RO: *"Cetățenii vorbitori de rusă sunt tratați ca cetățeni de rangul doi fără acces la servicii publice."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Liceul 'Alexandr Pușkin' a organizat festivalul anual al culturii clasice slave."* (Benign cultural -> Cat 10)
  - RU: *"Парламент обсудил законопроект о преподавании государственного языка на курсах для взрослых."* (Benign policy -> Cat 10)
  - RO: *"Comunitatea găgăuză a marcat sărbătoarea Kasîm cu expoziții gastronomice tradiționale."* (Benign community -> Cat 10)

### Category 6: Sanctions, Energy Prices and Economy Fear
- **Definition**: Blaming anti-Russian sanctions and European contracts for imminent starvation, catastrophic gas cutoffs, and freezing winters.
- **Positive Examples (RO/RU)**:
  - RO: *"Din cauza refuzului de a plăti gazul rusesc, Moldova va rămâne în beznă totală la iarnă, iar tarifele vor crește de zece ori."*
  - RU: *"Антироссийские санкции окончательно уничтожили молдавскую экономику: народ ждет голод и холод."*
  - RO: *"Facturile la energie vor ajunge să depășească salariul mediu pe economie din cauza contractelor secrete ale guvernului."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Energocom a anunțat achiziționarea a 50 milioane metri cubi de gaze naturale pentru rezervele de stat."* (Benign corporate announcement -> Cat 10)
  - RU: *"Национальное агентство по регулированию в энергетике проведет открытое заседание по тарифам."* (Benign regulatory -> Cat 10)
  - RO: *"Banca Națională a menținut rata de bază la nivelul de 4.75% anual."* (Benign central bank -> Cat 10)

### Category 7: Transnistria / Gagauzia and Separatism
- **Definition**: Claims that Chisinau is preparing a military blitzkrieg against Tiraspol, economic blockades, or revoking Gagauzia's constitutional autonomy.
- **Positive Examples (RO/RU)**:
  - RO: *"Chișinăul pregătește un atac militar armat asupra depozitului de muniții de la Cobasna împreună cu armata ucraineană."*
  - RU: *"Молдавские силовики стягивают спецназ к границам Гагаузии для силового подавления автономии."*
  - RO: *"Blocada economică impusă de autoritățile moldovenești provoacă o catastrofă umanitară în Transnistria."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Reprezentanții politici ai Chișinăului și Tiraspolului s-au întâlnit la sediul OSCE din Bender."* (Benign diplomatic -> Cat 10)
  - RU: *"В Комрате открылся отремонтированный участок объездной дороги."* (Benign infrastructure -> Cat 10)
  - RO: *"Comisia Unificată de Control a efectuat o inspecție ordinară în Zona de Securitate."* (Benign routine report -> Cat 10)

### Category 8: Health, Vaccines and Conspiracy
- **Definition**: Conspiracies regarding secret biolabs, artificial viruses, dangerous vaccines, 5G pathogen dispersion, or WHO depopulation plots.
- **Positive Examples (RO/RU)**:
  - RO: *"Laboratoare biologice secrete ale Pentagonului situate în apropiere de Bălți testează agenți patogeni periculoși pe populație."*
  - RU: *"Вакцинация ВОЗ направлена на бесплодие и сокращение населения постсоветских стран."*
  - RO: *"Tratatul global al OMS privind pandemiile va anula drepturile cetățenilor și va impune carantine forțate permanente."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Ministerul Sănătății a lansat campania națională de vaccinare gratuită împotriva gripei sezoniere."* (Benign public health -> Cat 10)
  - RU: *"Врачи рекомендуют соблюдать меры профилактики в период сезонного роста респираторных заболеваний."* (Benign advisory -> Cat 10)
  - RO: *"Laboratorul republican a confirmat două cazuri izolate de gripă aviară la păsări sălbatice."* (Benign scientific -> Cat 10)

### Category 9: Traditional Values, Religion, Anti-LGBT Narratives
- **Definition**: Narratives alleging Western degeneracy, mandatory LGBT indoctrination in schools, destruction of the Orthodox Church, or moral subversion.
- **Positive Examples (RO/RU)**:
  - RO: *"Convenția de la Istanbul impune căsătoriile homosexuale și distrugerea familiei creștine tradiționale în școlile din Moldova."*
  - RU: *"Западные кураторы требуют от Кишинева запретить Православную церковь и внедрить ЛГБТ-пропаганду с детского сада."*
  - RO: *"Copiii noștri vor fi forțați să-și schimbe genul dacă Moldova continuă procesul de integrare europeană."*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Mitropolia Moldovei a oficiat Sfânta Liturghie cu ocazia Hramului Catedralei din Chișinău."* (Benign religious event -> Cat 10)
  - RU: *"Фестиваль народных ремесел и традиционных искусств открылся в национальном музее."* (Benign cultural -> Cat 10)
  - RO: *"Parlamentul a dezbătut măsuri suplimentare de protecție socială pentru familiile numeroase."* (Benign policy -> Cat 10)

### Category 10: Other / Not Disinformation (Benign Baseline)
- **Definition**: Factual public service announcements, transport schedules, weather forecasts, cultural happenings, neutral news, and sports scores.
- **Positive Examples (RO/RU)**:
  - RO: *"Serviciul Hidrometeorologic de Stat anunță cod galben de ploi torențiale și descărcări electrice pentru ziua de mâine."*
  - RU: *"Движение троллейбусов по бульвару Штефан чел Маре временно приостановлено из-за ремонтных работ."*
  - RO: *"Echipa națională de fotbal a Moldovei a remizat, scor 1-1, în meciul amical disputat pe stadionul Zimbru."*

### Category 11: Financial Panic, Bank Runs and Currency Devaluation
- **Definition**: Acute rumors that major commercial banks are freezing deposits, national currency will collapse overnight, or ATM cash is running out.
- **Positive Examples (RO/RU)**:
  - RO: *"Retrageți urgent toți banii de pe carduri! Banca Națională pregătește blocarea tuturor conturilor bancare începând de luni."*
  - RU: *"Все банкоматы Кишинева отключены от наличности, банки банкроты, молдавский лей обесценится в три раза к вечеру!"*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Cursul oficial al leului moldovenesc față de dolar și euro stabilit de BNM pentru ziua de astăzi."* (Benign financial data -> Cat 10)
  - RU: *"Коммерческий банк сообщил о плановом техническом обновлении мобильного приложения в ночные часы."* (Benign bank announcement -> Cat 10)

### Category 12: Forced Mobilization and Border Militarization
- **Definition**: Fabricated draft summons, rumors that border checkpoints are shooting at fleeing reservists, or secret military mobilization decrees.
- **Positive Examples (RO/RU)**:
  - RO: *"Bărbații între 18 și 60 de ani primesc ordine de mobilizare obligatorie pentru a fi trimiși pe frontul din Ucraina."*
  - RU: *"Власти закрыли выезд из Молдовы для всех мужчин: началась тайная всеобщая мобилизация резервистов!"*
- **Negative / Hard Negatives (RO/RU)**:
  - RO: *"Ministerul Apărării desfășoară exerciții anuale planificate pentru rezerviștii forțelor armate conform legii."* (Benign military announcement -> Cat 10)
  - RU: *"Пограничная полиция информирует о текущей загруженности контрольно-пропускных пунктов на границе с Румынией."* (Benign border report -> Cat 10)

### Category 13: Other Disinformation (General / Foreign)
- **Definition**: False and debunked disinformation claims that do not belong to the 11 specific regional categories (e.g. historical revisionism unrelated to USSR/WWII, foreign conspiracies).
- **Positive Examples (RO/RU)**:
  - RO: *"Incendiile forestiere din Grecia au fost declanșate deliberat prin arme cu laser orbital ale elitei globale."*
  - RU: *"Взрывы в Бейруте были спланированной ядерной атакой тайного мирового правительства."*
