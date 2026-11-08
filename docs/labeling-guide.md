# ScamGuard Narrative Classification — Human Annotation & Labelling Guide

This guide defines the 13 categories for annotating Moldovan and regional social media posts (Telegram, Facebook, news comments) into narrative categories for ScamGuard, and explains how to complete the blind annotation file [`ml/data/labeling/telegram_blind_batch.csv`](file:///c:/Users/maria/scamguard/ml/data/labeling/telegram_blind_batch.csv).

---

## 1. How to Fill `ml/data/labeling/telegram_blind_batch.csv`

1. **Open the file**: Open [`ml/data/labeling/telegram_blind_batch.csv`](file:///c:/Users/maria/scamguard/ml/data/labeling/telegram_blind_batch.csv) in Excel, LibreOffice Calc, Google Sheets, or any UTF-8 CSV editor (the file includes a UTF-8 BOM so Cyrillic and Romanian diacritics open cleanly in Excel).
2. **Columns**:
   - `id`: Unique identifier (`tg-00001` .. `tg-00400`). **Do not modify.**
   - `text`: Full text of the Telegram post. **Do not modify.** (The keyword script's label has been completely stripped from this file so your judgment cannot be influenced.)
   - `my_label`: Enter a single integer from `1` to `13` corresponding to the **primary narrative category** defined in Section 3 below. If you are genuinely uncertain after reading the rules below, write `not_sure` in `my_label`.
   - `my_note`: Optional free-text note. Use this to record:
     - Secondary categories if a post combines two narratives (e.g., `secondary: 6`),
     - Why a post is borderline or why you wrote `not_sure`,
     - Sarcasm, irony, or quoted speech where a channel quotes a false claim only to mock or debunk it (which should be labeled `10` Benign).
3. **Evaluate after completion**: Once you save the completed CSV, run:
   ```powershell
   backend\.venv\Scripts\python ml/scripts/evaluate_human_labels.py
   ```
   This script computes Cohen's $\kappa$ agreement against the heuristic script and re-evaluates all candidate models on your human ground-truth labels.

---

## 2. Sampling Scheme & Inverse-Probability Reweighting

To ensure the 150-message blind annotation batch is not dominated by routine neutral posts while preserving 100% coverage of the held-out test split (`ml/data/processed/v1/telegram_test.jsonl`):

1. **Source Pool (`backend/scamguard.db`)**:
   - Out of 891 candidate Telegram messages ($\ge 40$ characters) in `backend/scamguard.db`, the keyword script (`ml/scripts/label_telegram_messages.py`) classified **160 messages ($17.96\%$)** as disinformation (`is_disinformation = True`) and **731 messages ($82.04\%$)** as benign (`is_disinformation = False`).
   - Those 160 script-disinfo messages + 240 randomly sampled script-benign messages formed the 400-message corpus (`telegram_labeled_400.jsonl`, $40.0\%$ script-disinfo / $60.0\%$ script-benign), which was split $250 / 150$ into `telegram_train.jsonl` and `telegram_test.jsonl`.
2. **Composition of `telegram_blind_batch.csv` ($N = 150$)**:
   - **Every message in `telegram_test.jsonl` that the script marked as disinformation**: **$n_{\text{disinfo}} = 58$ messages** ($38.67\%$ of the file).
   - **Sample of the remaining messages in `telegram_test.jsonl` marked as benign by the script**: **$n_{\text{benign}} = 92$ messages** ($61.33\%$ of the file).
   - All 150 rows were deterministically shuffled with `random.Random(42)` so row position gives zero clue about the script's label.
3. **Reweighting Formula to Natural Channel Prevalence**:
   - Because script-disinfo messages were oversampled relative to the raw database stream ($38.67\%$ in the batch vs. $17.96\%$ in the raw 891-message stream) and script-benign messages were undersampled ($61.33\%$ in the batch vs. $82.04\%$ in the raw stream), unweighted metrics measure performance on the stratified test distribution, while inverse-probability weights restore natural stream prevalence:
     $$w_{\text{script-disinfo}} = \frac{160 / 891}{58 / 150} = \frac{0.17957}{0.38667} \approx 0.4644, \qquad w_{\text{script-benign}} = \frac{731 / 891}{92 / 150} = \frac{0.82043}{0.61333} \approx 1.3377$$
   - `ml/scripts/evaluate_human_labels.py` reports both **unweighted** metrics on the 150-item batch and **inverse-probability weighted** metrics reflecting the natural stream.

---

## 3. Core Labelling Rules

1. **Topic vs. Disinformation Claim (Crucial Distinction)**:
   - Mentioning a sensitive topic (elections, gas tariffs, NATO, EU, Ukraine, Transnistria, banks, vaccines) does **not** make a post disinformation.
   - Factual news reports, official institutional announcements, normal political criticism, parliamentary debates, and opinion pieces without fabricated claims or manipulative conspiracy narratives must be labeled **`10` (Other / Not Disinformation — Benign)**.
2. **Rule for "Other Disinformation" (`13`)**:
   - Assign **`13`** **only** when the message advances a demonstrably false, fabricated, or conspiratorial propaganda claim that **does not fit any of the 11 specific regional narrative categories (`1`–`9`, `11`, `12`)** (for example: foreign conspiracy theories about orbital weather weapons, flat earth, or unrelated foreign events).
   - Do **not** use `13` as a fallback for harsh Moldovan political opinions; if a political opinion is not advancing a false/manipulative disinformation narrative, label it **`10`**.
3. **Rule for "Not Sure" (`not_sure`)**:
   - If a post makes a specific factual assertion whose veracity you cannot determine from context and that could plausibly be either a legitimate breaking news report or a fabricated hoax, enter **`not_sure`** in `my_label` and briefly note the ambiguity in `my_note`.
   - Items marked `not_sure` are reported separately and excluded from strict ground-truth error penalization until verified.

---

## 4. Category Definitions (with 3 Positive & 3 Negative Examples Each)

### Category 1: War in Ukraine and Russia Justification
- **Definition**: Justifying the Russian military invasion, framing Ukraine as an artificial state or aggressor, claiming "denazification" is necessary, or blaming Ukraine/NATO for Russian war crimes.
- **3 Positive Examples (Label = `1`)**:
  1. RO: *"Operațiunea militară rusă este un răspuns legitim la agresiunea regimului de la Kiev împotriva populației civile din Donbas."*
  2. RU: *"Украинские нацисты сами инсценировали трагедию в Буче, чтобы сорвать мирные переговоры."*
  3. RO: *"Ucraina nu are drept istoric la existență statală, fiind o creație artificială sovietică condusă din exterior."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Războiul din Ucraina a provocat daune majore infrastructurii energetice din regiunea Odesa."* (Factual war reporting)
  2. RU: *"Минобороны Украины сообщило о работе систем ПВО над южными областями страны."* (Neutral military dispatch)
  3. RO: *"Moldova a trimis un nou lot de ajutoare umanitare pentru refugiații ucraineni cazați în centrele regionale."* (Factual humanitarian news)

### Category 2: Anti-EU / "Europe is Falling Apart"
- **Definition**: Framing European integration as civilizational collapse, forced loss of sovereignty to Brussels, mandatory land seizure by foreigners, or claiming the EU is disintegrating and freezing.
- **3 Positive Examples (Label = `2`)**:
  1. RO: *"Aderarea la UE va duce la falimentul agriculturii moldovenești și confiscarea pământurilor de către corporațiile străine."*
  2. RU: *"Евросоюз разваливается на глазах, европейцы замерзают без газа, а Брюссель диктует Молдове уничтожение суверенитета."*
  3. RO: *"Bruxelles-ul obligă secret Moldova să accepte zeci de mii de migranți ilegali în schimbul creditelor europene."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Comisia Europeană a alocat un grant de 40 milioane euro pentru reabilitarea căilor ferate din Moldova."* (Factual EU aid news)
  2. RU: *"Делегация Европарламента провела встречу с представителями парламентских фракций в Кишиневе."* (Neutral diplomatic news)
  3. RO: *"Exporturile agricole moldovenești pe piața UE au înregistrat o creștere de 18% în primele nouă luni."* (Factual trade statistics)

### Category 3: Anti-NATO / Anti-West
- **Definition**: Portraying NATO or Western partners as preparing to drag Moldova into war, building secret foreign military bases on Moldovan soil, or occupying the country.
- **3 Positive Examples (Label = `3`)**:
  1. RO: *"Exercițiile militare comune cu forțele NATO demonstrează că Alianța pregătește transformarea Moldovei în teatru de război."*
  2. RU: *"НАТО превращает Молдову в военный плацдарм для открытия второго фронта против России."*
  3. RO: *"Trupele occidentale au ocupat deja aeroportul Mărculești sub acoperirea neutralității pentru a lansa atacuri."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Ministerul Apărării a recepționat echipamente de deminare și protecție individuală prin programul Parteneriat pentru Pace."* (Factual defense news)
  2. RU: *"Конституция Республики Молдова закрепляет статус постоянного нейтралитета государства."* (Factual legal statement)
  3. RO: *"Geniștii Armatei Naționale au participat la o conferință tehnică internațională privind securitatea regională."* (Factual military event)

### Category 4: Moldova Government and Elections Delegitimisation
- **Definition**: Claiming Moldovan elections or referendums are systematically rigged via phantom ballots, asserting the government is an illegal foreign puppet junta, or fabricating election cancellation decrees.
- **3 Positive Examples (Label = `4`)**:
  1. RO: *"Rezultatele referendumului au fost falsificate masiv în secțiile de votare din diaspora occidentală prin sute de mii de voturi fantomă."*
  2. RU: *"Майя Санду — нелегитимный президент, узурпировавшая власть по прямому приказу кураторов из Вашингтона и Сороса."*
  3. RO: *"CEC a tipărit în secret buletine de vot deja ștampilate pentru a fura alegerile parlamentare."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Comisia Electorală Centrală a aprobat modelele buletinelor de vot și lista secțiilor din străinătate."* (Routine electoral administration)
  2. RU: *"Наблюдатели ОБСЕ представили промежуточный отчет о ходе избирательной кампании в Молдове."* (Factual monitoring report)
  3. RO: *"Deputații din opoziție au criticat în ședința Parlamentului proiectul bugetului de stat propus de Guvern."* (Normal democratic opposition criticism)

### Category 5: Russophobia, Language and Identity
- **Definition**: Alleging state-sponsored persecution of Russian speakers, forced closure of all Russian schools, banning the Russian language in daily life, or ethnic cleansing of minorities.
- **3 Positive Examples (Label = `5`)**:
  1. RO: *"Regimul de la Chișinău interzice complet limba rusă și pregătește expulzarea forțată a minorităților naționale."*
  2. RU: *"Власти Молдовы проводят политику оголтелой русофобии, закрывая все русские школы и объявляя русскоязычных гражданами второго сорта."*
  3. RO: *"Poliția lingvistică va amenda cetățenii care vorbesc limba rusă pe stradă sau în spitale."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Ministerul Educației a deschis înscrierile la cursurile gratuite de limbă română pentru adulți, cu 6.500 de locuri disponibile."* (Factual education program)
  2. RU: *"Государственный русский драматический театр имени А. П. Чехова открыл новый театральный сезон в Кишиневе."* (Factual cultural news)
  3. RO: *"În Chișinău s-a desfășurat festivalul etnocultural anual cu participarea comunităților ucrainene, ruse, găgăuze și bulgare."* (Factual community report)

### Category 6: Sanctions, Energy Prices and Economy Fear
- **Definition**: Inducing panic that Moldova will freeze in total darkness without Russian gas, claiming tariffs will increase tenfold overnight, or alleging secret government energy theft causing starvation.
- **3 Positive Examples (Label = `6`)**:
  1. RO: *"Din cauza refuzului de a cere gaz de la Moscova, Moldova va rămâne în beznă totală la iarnă, iar tarifele vor crește de zece ori."*
  2. RU: *"Антироссийские санкции окончательно уничтожили молдавскую экономику: зимой страну ждет полное отключение света, голод и холод."*
  3. RO: *"Facturile la energie vor depăși salariul mediu deoarece guvernul vinde curentul moldovenilor în străinătate pe ascuns."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Energocom a anunțat că stocurile comerciale de gaze naturale depozitate pentru iarnă depășesc 150 milioane metri cubi."* (Factual energy update)
  2. RU: *"Национальное агентство по регулированию в энергетике проведет открытое заседание по пересмотру тарифов на теплоэнергию."* (Factual regulatory announcement)
  3. RO: *"Ministerul Muncii a deschis înregistrarea cetățenilor pe platforma compensatii.gov.md pentru sezonul rece."* (Factual social policy news)

### Category 7: Transnistria / Gagauzia and Separatism
- **Definition**: Claiming Chisinau and Ukraine are preparing an armed military invasion of Transnistria (Cobasna) or sending special forces to abolish Gagauzia's autonomy by force.
- **3 Positive Examples (Label = `7`)**:
  1. RO: *"Chișinăul pregătește un atac militar armat asupra depozitului de muniții de la Cobasna împreună cu trupele ucrainene."*
  2. RU: *"Молдавские силовики стягивают спецназ к границам Гагаузии для вооруженного захвата Комрата и ликвидации автономии."*
  3. RO: *"Autoritățile de la Chișinău au instituit o blocadă totală a medicamentelor și alimentelor către Transnistria pentru a provoca o catastrofă umanitară."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Reprezentanții politici în procesul de negocieri de la Chișinău și Tiraspol s-au întrunit la sediul Misiunii OSCE."* (Factual diplomatic meeting)
  2. RU: *"Народное собрание Гагаузии провело публичные слушания по проекту регионального бюджета в Комрате."* (Factual regional governance news)
  3. RO: *"Comisia Unificată de Control a examinat raportul săptămânal al observatorilor militari din Zona de Securitate."* (Routine peacekeeping report)

### Category 8: Health, Vaccines and Conspiracy
- **Definition**: Conspiracies about secret Pentagon biolabs in Moldova/Ukraine spreading pathogens, lethal depopulation vaccines, or WHO pandemic treaties abolishing national sovereignty.
- **3 Positive Examples (Label = `8`)**:
  1. RO: *"Laboratoare biologice secrete ale Pentagonului situate în apropiere de Bălți testează virusuri letale pe populația locală."*
  2. RU: *"Принудительная вакцинация ВОЗ направлена на бесплодие и сокращение населения постсоветских республик."*
  3. RO: *"Tratatul global al OMS privind pandemiile va anula Constituția și va permite închiderea cetățenilor în lagăre de carantină."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Agenția Națională pentru Sănătate Publică a distribuit 200 de mii de doze de vaccin antigripal în policlinici."* (Factual public health news)
  2. RU: *"Министерство здравоохранения рекомендует соблюдать меры профилактики в период сезонного роста ОРВИ."* (Routine medical advisory)
  3. RO: *"Spitalul Clinic Republican a inaugurat un nou bloc operator dotat cu echipamente moderne de chirurgie."* (Factual healthcare infrastructure news)

### Category 9: Traditional Values, Religion, Anti-LGBT Narratives
- **Definition**: Claiming the EU/West requires Moldova to ban the Orthodox Church, replace Christian holidays, legalize pedophilia, or force gender reassignment on school children.
- **3 Positive Examples (Label = `9`)**:
  1. RO: *"Integrarea europeană obligă școlile din Moldova să introducă propaganda LGBT obligatorie de la grădiniță și să interzică icoanele."*
  2. RU: *"Западные кураторы требуют от Кишинева закрыть Православную церковь Молдовы и узаконить однополые браки под угрозой штрафов."*
  3. RO: *"Conform noilor legi impuse de Bruxelles, părinții care își duc copiii la biserică vor fi decăzuți din drepturile părintești."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Mitropolia Moldovei și Mitropolia Basarabiei au anunțat programul slujbelor religioase de sărbătoarea Sfinților Arhangheli."* (Factual religious news)
  2. RU: *"Министерство культуры выделило средства на реставрацию исторических деревянных церквей XVIII века."* (Factual heritage preservation)
  3. RO: *"Parlamentul a votat majorarea indemnizațiilor unice la nașterea copilului pentru familiile tinere."* (Factual family policy news)

### Category 10: Other / Not Disinformation (Benign Baseline)
- **Definition**: Factual news reports, official communiqués, economic/energy/electoral updates without fabricated claims, normal political commentary, weather, traffic, culture, and sports.
- **3 Positive Examples (Label = `10`)**:
  1. RO: *"Serviciul Hidrometeorologic de Stat anunță cod galben de ceață și intensificări ale vântului pentru următoarele 24 de ore."*
  2. RU: *"Национальный банк Молдовы сохранил базовую ставку на уровне 3,60% годовых на фоне замедления инфляции."*
  3. RO: *"Poliția de Frontieră informează că toate punctele de trecere a frontierei cu România și Ucraina activează în regim normal."*
- **3 Negative Examples (Do NOT Label `10` — these are Disinformation)**:
  1. RO: *"Băncile comerciale din Chișinău blochează mâine toate cardurile cetățenilor — scoateți urgent numerarul!"* (Financial panic hoax $\rightarrow$ Label `11`)
  2. RU: *"Власти тайно подписали указ о всеобщей мобилизации молдавских резервистов для отправки под Одессу."* (Mobilization hoax $\rightarrow$ Label `12`)
  3. RO: *"UE ne impune distrugerea bisericii și vânzarea terenurilor agricole către străini."* (Anti-EU disinformation $\rightarrow$ Label `2`)

### Category 11: Financial Panic, Bank Runs and Currency Devaluation
- **Definition**: Acute rumors engineered to trigger bank runs, claiming commercial banks are insolvent or freezing customer deposits, ATMs are out of cash, or the Moldovan Leu is collapsing overnight.
- **3 Positive Examples (Label = `11`)**:
  1. RO: *"Retrageți urgent toți banii de pe carduri! Banca Națională pregătește blocarea tuturor conturilor bancare ale populației începând de luni."*
  2. RU: *"Все банкоматы Кишинева пустые, крупнейшие банки страны банкроты, молдавский лей обесценится до 50 леев за евро к концу недели!"*
  3. RO: *"Guvernul confiscă economiile din bănci ale cetățenilor și blochează transferurile din diaspora pentru a acoperi gaura din buget."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Banca Națională a Moldovei a anunțat că rezervele valutare oficiale au atins 5,4 miliarde de dolari, asigurând stabilitatea leului."* (Factual central bank report)
  2. RU: *"Один из коммерческих банков предупредил клиентов о плановых технических работах в мобильном приложении с 02:00 до 04:00 ночи."* (Routine maintenance notice)
  3. RO: *"Asociația Băncilor din Moldova a raportat creșterea volumului de plăți instant prin sistemul MIA în trimestrul trei."* (Factual banking statistics)

### Category 12: Forced Mobilization and Border Militarization
- **Definition**: Fabricated military draft orders, rumors that men aged 18–60 are banned from leaving Moldova, or claims that Moldovan conscripts are being secretly sent to fight at the front.
- **3 Positive Examples (Label = `12`)**:
  1. RO: *"Bărbații între 18 și 60 de ani primesc ordine de mobilizare generală pentru a fi trimiși pe frontul din Ucraina începând de săptămâna viitoare."*
  2. RU: *"Власти тайно закрыли выезд из Молдовы для всех военнообязанных мужчин: началась принудительная мобилизация резервистов!"*
  3. RO: *"Ministerul Apărării a emis un ordin secret de rechiziționare a autoturismelor personale și încorporare de urgență a tinerilor."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Ministerul Apărării desfășoară în perioada 4-8 noiembrie exerciții anuale planificate de instruire cu rezerviștii Armatei Naționale."* (Routine planned military training)
  2. RU: *"Пограничная полиция опровергла слухи об ограничениях на выезд мужчин и подтвердила штатную работу всех пунктов пропуска."* (Official debunk/clarification)
  3. RO: *"Centrele militare teritoriale efectuează actualizarea anuală de rutină a datelor de evidență militară a cetățenilor."* (Routine administrative procedure)

### Category 13: Other Disinformation (Unclassified / General)
- **Definition**: Demonstrably false, fabricated, or conspiratorial propaganda claims that do not belong to any of the 11 specific regional narrative categories (`1`–`9`, `11`, `12`).
- **3 Positive Examples (Label = `13`)**:
  1. RO: *"Incendiile forestiere din Europa au fost declanșate deliberat prin arme cu laser orbital pentru a impune orașele de 15 minute."*
  2. RU: *"Тайное мировое правительство искусственно вызывает землетрясения с помощью климатического оружия HAARP."*
  3. RO: *"Aterizarea pe Lună și imaginile sateliților meteorologici sunt falsuri regizate în studiouri pentru a ascunde forma reală a Pământului."*
- **3 Negative / Hard-Negative Examples (Label = `10`)**:
  1. RO: *"Un cutremur cu magnitudinea de 4,2 grade pe scara Richter s-a produs în această dimineață în zona seismică Vrancea."* (Factual seismology report)
  2. RU: *"Астрофизики сообщили о наблюдении редкого солнечного затмения и геомагнитной бури среднего уровня."* (Factual science news)
  3. RO: *"Un analist politic de la Chișinău a comentat într-un editorial perspectivele relațiilor comerciale bilaterale."* (Normal commentary/opinion)
