# Disinformation Narrative Classification — Dataset Sources & Licences

> **Important:** Raw dataset files (`ml/data/raw/*`), processed splits (`ml/data/processed/*`), and model weights (`ml/models/*`) are excluded via `.gitignore` and must never be committed to Git.

| Dataset | Languages | Licence | Primary Role | Source / DOI |
|---|---|---|---|---|
| **EUvsDisinfo (Leite et al., CIKM 2024)** | Multilingual (`ro`, `ru`, `en`, +) | CC BY-SA 4.0 | Primary topic-labelled disinformation claims & credible counter-articles (508 topics mapped to 10 categories) | `https://doi.org/10.5281/zenodo.10514307` |
| **FAKEROM** | Romanian (`ro`) | Open Academic | Romanian fake vs. real news baseline (~14,000 items) | `https://www.tagtog.com/fakerom` |
| **MOROCO (Moldavian & Romanian Dialectal Corpus)** | Romanian / Moldovan (`ro`) | CC BY-NC-SA 4.0 | Negative ("Other / not disinformation") news examples reflecting Moldovan newsroom style (~33,000 samples) | Hugging Face `moroco` |
| **dimonsleep/antipropaganda** | Romanian & Russian (`ro`, `ru`) | Apache-2.0 | Bilingual propaganda reference baseline | Hugging Face `dimonsleep/antipropaganda` |
| **StopFals.md Debunk Set** | Romanian & Russian (`ro`, `ru`) | Public Fact-Check | Moldova-specific held-out evaluation benchmark (100–300 verified claims) | `https://stopfals.md` |
| **Moldovan Public Telegram Test Set** | Romanian & Russian (`ro`, `ru`) | Public Channels | Domain-specific evaluation set (300–500 short Telegram posts labelled with inter-annotator Cohen's kappa) | Collected via Scamguard collector |

## Anti-Leakage Split Policy
All training, validation, and test splits in `ml/scripts/prepare_splits.py` are partitioned **by source channel/outlet and chronological publication date** (never random row shuffling) so near-duplicate articles or claims cannot leak across train and test sets.
