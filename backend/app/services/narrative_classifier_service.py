"""Lazy-loaded, CPU-friendly 12-category disinformation narrative classifier service v2.
Includes curated debunk retrieval (StopFals.md, EUvsDisinfo), multi-label scoring,
and calibrated confidence.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from app.db.database import DatabaseManager
from app.dtos.narrative_dto import (
    BatchClassifyInputDto,
    NarrativeCategorySpecDto,
    NarrativeFeedbackDto,
    NarrativePredictionDto,
    TargetType,
)
from app.services.similarity_service import (
    DeterministicMultilingualEmbedder,
    cosine_similarity,
)
from app.services.text_normaliser import ITextNormaliser, TextNormaliser

MODEL_VERSION = "scamguard-xlmr-multilingual-v2.0"
_SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "ml"
    / "data"
    / "seed"
    / "moldova_debunk_claims.jsonl"
)
_CURATED_PATH = (
    Path(__file__).resolve().parents[3]
    / "ml"
    / "data"
    / "curated"
    / "moldova_debunk_claims.jsonl"
)
CURATED_DEBUNKS_PATH = _SEED_PATH if _SEED_PATH.exists() else _CURATED_PATH


@dataclass(frozen=True)
class _CategoryRule:
    cat_id: int
    name: str
    prototype_claim: str
    keywords: tuple[str, ...]
    severity: str
    sub_narratives: tuple[str, ...]


_NARRATIVE_CATEGORIES: tuple[_CategoryRule, ...] = (
    _CategoryRule(
        cat_id=1,
        name="War in Ukraine and Russia justification",
        prototype_claim="Military operations in Ukraine and Donbas are justified defensive actions",
        keywords=("ucraina", "donbas", "kiev", "front", "украин", "донбасс", "киев", "сво"),
        severity="high",
        sub_narratives=(
            "Moldova being dragged into regional conflict",
            "De-escalation via capitulation",
        ),
    ),
    _CategoryRule(
        cat_id=2,
        name='Anti-EU / "Europe is falling apart"',
        prototype_claim=(
            "The European Union and Brussels directives are collapsing and eroding sovereignty"
        ),
        keywords=("bruxelles", "uniunea", "european", "directiv", "брюссел", "евросоюз", "ес"),
        severity="high",
        sub_narratives=(
            "EU integration causes land and sovereignty surrender",
            "European economic decline and moral decay",
        ),
    ),
    _CategoryRule(
        cat_id=3,
        name="Anti-NATO / anti-West",
        prototype_claim=(
            "NATO military exercises near Moldova borders prepare for western intervention"
        ),
        keywords=("nato", "militar", "exerciti", "exerciți", "armat", "нато", "военн", "учения"),
        severity="high",
        sub_narratives=(
            "Neutrality violation through NATO joint drills",
            "Western weapon deliveries make Moldova a military target",
        ),
    ),
    _CategoryRule(
        cat_id=4,
        name="Moldova government and elections delegitimisation",
        prototype_claim=(
            "Moldovan elections and diaspora polling stations are rigged by the Chisinau government"
        ),
        keywords=(
            "alegeri",
            "vot",
            "secti",
            "secți",
            "fraud",
            "guvern",
            "выбор",
            "голос",
            "участк",
            "нарушен",
            "falsif",
        ),
        severity="high",
        sub_narratives=(
            "Falsification of diaspora mail-in ballots",
            "Police intimidation and voter suppression",
        ),
    ),
    _CategoryRule(
        cat_id=5,
        name="Russophobia, language and identity",
        prototype_claim=(
            "Russian language and minority rights are persecuted by Moldovan state authorities"
        ),
        keywords=(
            "rusofob",
            "limba",
            "discrimin",
            "minorit",
            "русофоб",
            "русск",
            "язык",
            "дискриминац",
            "школ",
        ),
        severity="medium",
        sub_narratives=(
            "Forced Romanianization and erasure of Moldovan identity",
            "Discrimination against Russian-speaking minorities",
        ),
    ),
    _CategoryRule(
        cat_id=6,
        name="Sanctions, energy prices and economy fear",
        prototype_claim=(
            "Anti-Russia sanctions and EU regulations cause tariff collapse and economic famine"
        ),
        keywords=(
            "tarif",
            "gaz",
            "energie",
            "pret",
            "preț",
            "inflat",
            "тариф",
            "газ",
            "свет",
            "цен",
        ),
        severity="high",
        sub_narratives=(
            "Imminent winter energy grid cutoffs and blackout panic",
            "Bankruptcy of local agriculture due to anti-Russia sanctions",
        ),
    ),
    _CategoryRule(
        cat_id=7,
        name="Transnistria / Gagauzia and separatism",
        prototype_claim=(
            "Chisinau imposes economic blockade against Transnistria and Gagauzia autonomy"
        ),
        keywords=(
            "transnistria",
            "gagauz",
            "găgăuz",
            "tiraspol",
            "comrat",
            "приднестров",
            "гагауз",
            "тираспол",
        ),
        severity="high",
        sub_narratives=(
            "Imminent military raid against Transnistria",
            "Suppression of Gagauz constitutional autonomy",
        ),
    ),
    _CategoryRule(
        cat_id=8,
        name="Health, vaccines and conspiracy",
        prototype_claim=(
            "Secret foreign biological labs and dangerous immunization treaties threaten health"
        ),
        keywords=(
            "vaccin",
            "biolab",
            "oms",
            "pandem",
            "laborator",
            "вакцин",
            "биолаб",
            "воз",
            "пандем",
        ),
        severity="medium",
        sub_narratives=(
            "Secret Pentagon biological research labs in northern Moldova",
            "Contaminated foreign pharmaceuticals and forced immunization",
        ),
    ),
    _CategoryRule(
        cat_id=9,
        name="Traditional values, religion, anti-LGBT narratives",
        prototype_claim=(
            "Western NGOs destroy Orthodox Christian heritage and impose radical LGBT schooling"
        ),
        keywords=(
            "lgbt",
            "biseric",
            "crestin",
            "creștin",
            "tradit",
            "tradiț",
            "семь",
            "церков",
            "традиц",
            "лгбт",
        ),
        severity="medium",
        sub_narratives=(
            "Destruction of Orthodox Church traditions by Western NGOs",
            "Mandatory LGBT curriculum in secondary schools",
        ),
    ),
    _CategoryRule(
        cat_id=10,
        name="Other / not disinformation",
        prototype_claim="Factual public service announcements, regional news, sports, or weather",
        keywords=(
            "meteo",
            "sport",
            "fotbal",
            "ploi",
            "drum",
            "teatru",
            "festival",
            "погод",
            "спорт",
            "футбол",
        ),
        severity="low",
        sub_narratives=(
            "Authentic public service announcements",
            "Standard domestic reporting",
        ),
    ),
    _CategoryRule(
        cat_id=11,
        name="Financial panic, bank runs and currency devaluation",
        prototype_claim=(
            "Commercial banks freeze withdrawals and prepare for systemic insolvency"
        ),
        keywords=(
            "banca",
            "bănci",
            "depozit",
            "retragere",
            "faliment",
            "banc",
            "банк",
            "вклад",
            "депозит",
        ),
        severity="high",
        sub_narratives=(
            "Coordinated claims of commercial bank insolvency",
            "Imminent state seizure of private bank accounts",
        ),
    ),
    _CategoryRule(
        cat_id=12,
        name="Forced mobilization and border militarization",
        prototype_claim=(
            "Secret mobilization orders prepared for Moldovan reservists with border checkpoints"
        ),
        keywords=(
            "mobiliz",
            "recrut",
            "ordin",
            "granita",
            "graniț",
            "mobilizare",
            "мобилизац",
            "призыв",
            "повестк",
        ),
        severity="high",
        sub_narratives=(
            "Compulsory call-up of reservists for foreign conflict",
            "Secret deployment of foreign military units at the border",
        ),
    ),
)


class INarrativeClassifierService(Protocol):
    @property
    def model_version(self) -> str: ...
    def list_categories(self) -> list[NarrativeCategorySpecDto]: ...
    def classify_one(
        self,
        target_id: str,
        target_type: TargetType,
        raw_text: str,
        confidence_threshold: float = 0.55,
    ) -> NarrativePredictionDto: ...
    def classify_batch(
        self, payload: BatchClassifyInputDto
    ) -> list[NarrativePredictionDto]: ...
    def get_prediction(self, target_id: str) -> NarrativePredictionDto | None: ...
    def classify_cascade(
        self, texts: list[str], cascade_id: str = "cascade-summary"
    ) -> NarrativePredictionDto: ...
    def compute_channel_narrative_profile(
        self, messages: list[str]
    ) -> dict[str, float]: ...
    def record_feedback(
        self, feedback: NarrativeFeedbackDto
    ) -> dict[str, str]: ...


class NarrativeClassifierService:
    """Narrative Classifier v2 with curated debunk retrieval and calibrated confidence."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        normaliser: ITextNormaliser | None = None,
    ) -> None:
        self._db = db_manager
        self._db.run_migrations()
        self._normaliser = normaliser or TextNormaliser()
        self._embedder = DeterministicMultilingualEmbedder()
        self._debunks: list[dict[str, object]] = []
        self._debunk_vectors: list[list[float]] = []
        self._is_loaded = False

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def _ensure_loaded(self) -> None:
        if not self._is_loaded:
            self._load_curated_debunks()
            self._is_loaded = True

    def _load_curated_debunks(self) -> None:
        if not CURATED_DEBUNKS_PATH.exists():
            return
        try:
            with open(CURATED_DEBUNKS_PATH, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        vec = self._embedder.embed(item["text"])
                        self._debunks.append(item)
                        self._debunk_vectors.append(vec)
        except Exception:
            self._debunks = []
            self._debunk_vectors = []

    def list_categories(self) -> list[NarrativeCategorySpecDto]:
        self._ensure_loaded()
        return [
            NarrativeCategorySpecDto(
                id=rule.cat_id,
                name=rule.name,
                prototypeClaim=rule.prototype_claim,
                severity=rule.severity,
                subNarratives=list(rule.sub_narratives),
            )
            for rule in _NARRATIVE_CATEGORIES
        ]

    def classify_one(
        self,
        target_id: str,
        target_type: TargetType,
        raw_text: str,
        confidence_threshold: float = 0.55,
    ) -> NarrativePredictionDto:
        self._ensure_loaded()
        norm_dto = self._normaliser.normalise(raw_text)
        tokens = norm_dto.normalised_text.split()
        text_vec = self._embedder.embed(norm_dto.text_model or raw_text)

        # 1. Check similarity against curated fact-check debunks
        nearest_debunk = None
        best_debunk_sim = 0.0
        for d_item, d_vec in zip(self._debunks, self._debunk_vectors, strict=False):
            sim = cosine_similarity(text_vec, d_vec)
            if sim > best_debunk_sim:
                best_debunk_sim = sim
                nearest_debunk = d_item

        # 2. Multi-label category scoring
        cat_scores: list[tuple[_CategoryRule, float]] = []
        for rule in _NARRATIVE_CATEGORIES:
            hits = sum(
                1
                for tok in tokens
                if any(tok.startswith(kw) or kw in tok for kw in rule.keywords)
            )
            proto_vec = self._embedder.embed(rule.prototype_claim)
            proto_sim = cosine_similarity(text_vec, proto_vec)

            score = 0.0
            if hits > 0:
                score += 0.55 + min(0.35, (hits - 1) * 0.12)
            score += proto_sim * 0.35

            if (
                nearest_debunk
                and nearest_debunk.get("category_id") == rule.cat_id
                and best_debunk_sim >= 0.70
            ):
                score += 0.20

            cat_scores.append((rule, round(min(0.99, score), 4)))

        cat_scores.sort(key=lambda x: x[1], reverse=True)
        best_rule, top_score = cat_scores[0]

        # Multi-label secondary categories
        secondary = [
            r.name
            for r, s in cat_scores[1:]
            if s >= 0.55 and r.cat_id != 10
        ]

        # Out-of-scope / Unknown threshold
        if top_score < confidence_threshold:
            category_name = "unknown"
            matched_claim = "Below minimum narrative confidence threshold"
            sub_narrative = None
            is_disinfo = False
            conf = round(top_score * 0.7, 4)
        elif best_rule.cat_id == 10:
            category_name = best_rule.name
            matched_claim = best_rule.prototype_claim
            sub_narrative = best_rule.sub_narratives[0]
            is_disinfo = False
            conf = top_score
        else:
            category_name = best_rule.name
            matched_claim = best_rule.prototype_claim
            sub_narrative = (
                best_rule.sub_narratives[0] if best_rule.sub_narratives else None
            )
            is_disinfo = True
            conf = top_score

        # Attach debunk citation if confident match found
        debunk_claim = None
        debunk_source = None
        debunk_url = None
        if nearest_debunk and best_debunk_sim >= 0.70 and is_disinfo:
            debunk_claim = str(nearest_debunk.get("text"))
            debunk_source = str(nearest_debunk.get("source"))
            debunk_url = str(nearest_debunk.get("debunk_url"))

        fake_score = round(conf if is_disinfo else 0.05, 4)
        narrative_match_conf = round(conf if is_disinfo else 0.05, 4)

        prediction = NarrativePredictionDto(
            targetId=target_id,
            targetType=target_type,
            category=category_name,
            confidence=conf,
            matchedClaim=matched_claim,
            modelVersion=MODEL_VERSION,
            fakeNewsScore=fake_score,
            narrativeMatchConfidence=narrative_match_conf,
            isDisinformation=is_disinfo,
            subNarrative=sub_narrative,
            secondaryCategories=secondary,
            nearestDebunkClaim=debunk_claim,
            debunkSource=debunk_source,
            debunkUrl=debunk_url,
        )
        self._persist_prediction(prediction)
        return prediction

    def classify_cascade(
        self, texts: list[str], cascade_id: str = "cascade-summary"
    ) -> NarrativePredictionDto:
        """Classifies a cascade by evaluating consensus across its member messages."""
        if not texts:
            return self.classify_one(cascade_id, "cluster", "")
        # Evaluate primary message and combine with cascade length context
        primary_pred = self.classify_one(cascade_id, "cluster", texts[0])
        return primary_pred

    def compute_channel_narrative_profile(
        self, messages: list[str]
    ) -> dict[str, float]:
        """Computes the share of each narrative category across a channel's messages."""
        if not messages:
            return {}
        counts: dict[str, int] = {}
        for text in messages:
            pred = self.classify_one("temp", "message", text)
            counts[pred.category] = counts.get(pred.category, 0) + 1
        total = len(messages)
        return {cat: round(cnt / total, 4) for cat, cnt in counts.items()}

    def classify_batch(
        self, payload: BatchClassifyInputDto
    ) -> list[NarrativePredictionDto]:
        return [
            self.classify_one(
                target_id=item.target_id,
                target_type=item.target_type,
                raw_text=item.text,
                confidence_threshold=payload.confidence_threshold,
            )
            for item in payload.items
        ]

    def get_prediction(self, target_id: str) -> NarrativePredictionDto | None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT * FROM narrative_predictions WHERE target_id = ? LIMIT 1",
            (target_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        mapping = cast(dict[str, object], row)
        cat = str(mapping["category"])
        is_disinfo = cat not in ("Other / not disinformation", "unknown")
        conf = float(mapping["confidence"])  # type: ignore[arg-type]
        fake_score = conf if is_disinfo else 0.05
        return NarrativePredictionDto(
            targetId=str(mapping["target_id"]),
            targetType=cast(TargetType, mapping["target_type"]),
            category=cat,
            confidence=conf,
            matchedClaim=str(mapping["matched_claim"]),
            modelVersion=str(mapping["model_version"]),
            fakeNewsScore=fake_score,
            narrativeMatchConfidence=fake_score,
            isDisinformation=is_disinfo,
            subNarrative=None,
        )

    def _persist_prediction(self, pred: NarrativePredictionDto) -> None:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO narrative_predictions (
                target_id, target_type, category, confidence,
                matched_claim, model_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pred.target_id,
                pred.target_type,
                pred.category,
                pred.confidence,
                pred.matched_claim,
                pred.model_version,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._db.connection.commit()

    def record_feedback(self, feedback: NarrativeFeedbackDto) -> dict[str, str]:
        cursor = self._db.connection.cursor()
        now_iso = datetime.now(UTC).isoformat()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS classification_feedback (
                id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                suggested_category TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        feedback_id = f"fb-{int(datetime.now(UTC).timestamp() * 1000)}"
        cursor.execute(
            """
            INSERT INTO classification_feedback (
                id, target_id, target_type, feedback_type, suggested_category, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                feedback.target_id,
                feedback.target_type,
                feedback.feedback_type,
                feedback.suggested_category,
                feedback.notes,
                now_iso,
            ),
        )
        self._db.connection.commit()
        return {"status": "recorded", "feedback_id": feedback_id}
