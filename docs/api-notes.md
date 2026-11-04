# ScamGuard API Transition Notes: Narrative Match vs. Fake News Score

This document outlines the API updates for narrative classification, detailing backwards-compatible changes and frontend migration guidance.

---

## 1. Motivation & Integrity Principle
* A system analyzing public Telegram channels can measure **similarity, coordination, and alignment with known strategic narratives**, but cannot make epistemological proof that an unverified claim is definitively false.
* Naming the output `fakeNewsScore` and returning a constant `0.05` for benign news gave a false illusion of automated truth verification and caused confusion.
* The field is updated to **`narrative_match`** (`narrativeMatch` in camelCase JSON), representing the calibrated confidence that a post matches a known strategic narrative or debunked prototype.

---

## 2. API Contract & Backwards Compatibility

### Response Payload (`NarrativePredictionDto`):
```json
{
  "targetId": "msg-00123",
  "targetType": "message",
  "category": "Anti-EU / \"Europe is falling apart\"",
  "confidence": 0.8421,
  "matchedClaim": "The European Union directives cause agricultural collapse and land surrender",
  "modelVersion": "scamguard-xlmr-multilingual-v2.0",
  "narrativeMatch": 0.8421,
  "narrativeMatchConfidence": 0.8421,
  "fakeNewsScore": 0.8421,
  "isDisinformation": true,
  "subNarrative": "EU integration causes land and sovereignty surrender",
  "secondaryCategories": [],
  "nearestDebunkClaim": "Uniunea Europeană nu obligă statele candidate să vândă terenurile",
  "debunkSource": "StopFals.md",
  "debunkUrl": "https://stopfals.md/ro/article/fals-terenuri-agricole"
}
```

### Backwards Compatibility Guarantees:
1. **`narrativeMatch`** (new primary field): Real calibrated model probability ($[0.0, 1.0]$) that the post matches the assigned narrative.
2. **`fakeNewsScore`** (deprecated alias): Populated identically to `narrativeMatch` so existing UI components continue functioning without breaking.
3. **No hard-coded `0.05` for benign news**: For Category 10 (*"Other / not disinformation"*), `narrativeMatch` dynamically reflects the true inverse narrative distance rather than an arbitrary static constant.

---

## 3. Frontend Migration Guide

| Old Component Usage | Recommended Migration | User-Facing Label |
|---|---|---|
| `message.fakeNewsScore` | `message.narrativeMatch ?? message.fakeNewsScore` | *"Narrative Match Confidence"* |
| Tag: `"Fake News: 85%"` | Tag: `"Matches Known Narrative (85%)"` | Transparent evidence framing |
| Evidence link | Display `nearestDebunkClaim` and `debunkUrl` | *"Verified Debunk Source: StopFals.md"* |

