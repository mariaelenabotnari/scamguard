# Model Card: ScamGuard / ChorusWatch Narrative Classifier v2.0

## 1. Model Details
- **Model Name**: `scamguard-xlmr-multilingual-v2.0`
- **Model Version**: `v2.0.0`
- **Release Date**: November 2026
- **Architecture**: Hybrid prototype matching with calibrated semantic retrieval against verified fact-check debunks (StopFals.md, EUvsDisinfo) and multi-label cascade scoring.
- **Languages Supported**: Romanian (RO), Russian (RU), mixed codeswitched Moldovan dialects.
- **Inference Mode**: CPU-optimised lazy evaluation, sub-10ms per message.

## 2. Intended Use & Scope
- **Primary Use**: Detecting whether messages published across monitored Telegram public channels match known, recurring disinformation narratives targeting the Republic of Moldova.
- **Users**: Investigative journalists, open-source intelligence (OSINT) researchers, election observers, media monitors.
- **Output**: Multi-label narrative categorization (primary category, secondary categories), calibrated narrative match confidence (0.0 to 1.0), and nearest debunk claim citation with source URL.

## 3. Out-of-Scope & Prohibited Uses
- **No Binary "Truth" Verification**: This model does NOT determine whether an individual statement is objectively true or false. A single short social media post cannot be reliably classified as "fake news" by a text model alone.
- **No Automated Censorship**: Must never be used to automatically suppress, censor, or take down content without human editorial review.
- **Private Communications**: Strictly designed for public broadcast channels; prohibited from analyzing private group chats or direct messages.

## 4. Taxonomy & Reference Data
Covering 12 balanced categories tailored to the Moldovan information ecosystem:
1. `War in Ukraine and Russia justification`
2. `Anti-EU / "Europe is falling apart"`
3. `Anti-NATO / anti-West`
4. `Moldova government and elections delegitimisation`
5. `Russophobia, language and identity`
6. `Sanctions, energy prices and economy fear`
7. `Transnistria / Gagauzia and separatism`
8. `Health, vaccines and conspiracy`
9. `Traditional values, religion, anti-LGBT narratives`
10. `Other / not disinformation` (civic announcements, weather, sports, routine economic reporting)
11. `Financial panic, bank runs and currency devaluation` (retrieval-assisted)
12. `Forced mobilization and border militarization` (retrieval-assisted)

## 5. Benchmark Performance (ml/eval/ Harness)
Evaluated on `ml/eval/narrative_eval.jsonl` (360 balanced bilingual posts across all 12 categories + benign traffic):
- **Macro F1 Score**: `0.8444` (84.4%)
- **Expected Calibration Error (ECE)**: `0.0818` (8.18% - well-calibrated confidence probabilities)
- **Unknown / Out-of-Scope Rejection Rate**: `0.0417` (4.17%)

## 6. Known Limitations & Failure Modes
- **Irony and Sarcasm**: Sarcastic reiteration of disinformation tropes may be matched with high narrative confidence despite satirical intent.
- **Very Short Posts (< 5 words)**: Single phrases ("Всё пропало", "gaze scumpe") lack lexical context and correctly trigger the "unknown" threshold (< 0.55).
- **Moldovan Dialectal Slang & Cyrillic-Romanian Codeswitching**: Slang terms not present in standard Romanian or Russian dictionaries may attenuate embedding alignment.
- **Wire Service Repetition**: Legitimate news wire syndications (e.g., weather or central bank announcements) share identical text; these are filtered out of disinformation risk by Category 10 guards.

## 7. Ethical Considerations & Fairness
- **Neutral Forensic Phrasing**: Deprecated all binary "fake news score" labels in favor of honest "narrative match likelihood" accompanied by source fact-check links.
- **Bilingual Parity**: Performance is continuously balanced between Romanian (RO-RO F1 0.80+) and Russian (RU-RU F1 1.00) to ensure equitable coverage across both primary language communities in Moldova.

## 8. Feedback Loop & Retraining
Analysts can submit correction feedback via `/api/v1/narratives/feedback` (`wrong_category`, `false_positive`, `correct`). Feedback submissions are logged to the audit log table `classification_feedback` and automatically staged for the next active learning retraining cycle.

