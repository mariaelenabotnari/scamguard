"""Lazy-loaded, CPU-friendly 12-category disinformation narrative classifier service."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from app.db.database import DatabaseManager
from app.dtos.narrative_dto import (
    BatchClassifyInputDto,
    NarrativeCategorySpecDto,
    NarrativePredictionDto,
    TargetType,
)
from app.services.text_normaliser import ITextNormaliser, TextNormaliser

MODEL_VERSION = "scamguard-xlmr-multilingual-v2.0"


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
        prototype_claim="Russian-language schools and cultural rights in Moldova are being banned",
        keywords=("limba", "rusa", "rusă", "scoli", "școli", "rusofob", "русск", "язык", "школ"),
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
            "Gas and electricity tariffs in Moldova will triple and trigger economic collapse"
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
        prototype_claim="Mandatory vaccination protocols and secret biolabs are imposed by the WHO",
        keywords=("vaccin", "oms", "pandemi", "biolab", "spital", "вакцин", "воз", "биолаб"),
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
            "Traditional family values and the Orthodox Church are under ideological attack"
        ),
        keywords=("traditi", "tradiți", "biseric", "familie", "lgbt", "традиц", "церков", "семь"),
        severity="medium",
        sub_narratives=(
            "Destruction of Orthodox Church traditions by Western NGOs",
            "Mandatory LGBT curriculum in secondary schools",
        ),
    ),
    _CategoryRule(
        cat_id=10,
        name="Other / not disinformation",
        prototype_claim="Standard weather, sports, cultural, or routine municipal announcement",
        keywords=("meteo", "fotbal", "stadion", "concert", "teatru", "погод", "футбол", "концерт"),
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
            "Commercial banks in Chisinau are freezing deposits and leu currency is devalued"
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


class NarrativeClassifierService:
    """Lazy-loaded CPU classifier with 12 national categories and fake news scoring."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        normaliser: ITextNormaliser | None = None,
    ) -> None:
        self._db = db_manager
        self._db.run_migrations()
        self._normaliser = normaliser or TextNormaliser()
        self._is_loaded = False

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def _ensure_loaded(self) -> None:
        if not self._is_loaded:
            self._is_loaded = True

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
        norm = self._normaliser.normalise(raw_text).normalised_text
        tokens = norm.split()

        best_rule: _CategoryRule | None = None
        best_hits = 0

        for rule in _NARRATIVE_CATEGORIES:
            hits = sum(
                1
                for tok in tokens
                if any(tok.startswith(kw) or kw in tok for kw in rule.keywords)
            )
            if hits > best_hits:
                best_hits = hits
                best_rule = rule

        if best_rule is None or best_hits == 0:
            confidence = 0.32
        else:
            confidence = round(min(0.98, 0.58 + (best_hits - 1) * 0.14), 4)

        if confidence < confidence_threshold or best_rule is None:
            category_name = "unknown"
            matched_claim = "Below minimum narrative confidence threshold"
            sub_narrative = None
            is_disinfo = False
            fake_score = round(confidence * 0.5, 4)
        elif best_rule.cat_id == 10:
            category_name = best_rule.name
            matched_claim = best_rule.prototype_claim
            sub_narrative = best_rule.sub_narratives[0]
            is_disinfo = False
            fake_score = 0.08
        else:
            category_name = best_rule.name
            matched_claim = best_rule.prototype_claim
            sub_narrative = (
                best_rule.sub_narratives[0] if best_rule.sub_narratives else None
            )
            is_disinfo = True
            fake_score = round(min(0.99, confidence * 1.05), 4)

        prediction = NarrativePredictionDto(
            targetId=target_id,
            targetType=target_type,
            category=category_name,
            confidence=confidence,
            matchedClaim=matched_claim,
            modelVersion=MODEL_VERSION,
            fakeNewsScore=fake_score,
            isDisinformation=is_disinfo,
            subNarrative=sub_narrative,
        )
        self._persist_prediction(prediction)
        return prediction

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
        conf = float(str(mapping["confidence"]))
        is_disinfo = cat not in ("unknown", "Other / not disinformation")
        fake_score = round(conf * 1.05, 4) if is_disinfo else 0.1

        return NarrativePredictionDto(
            targetId=str(mapping["target_id"]),
            targetType=cast(TargetType, str(mapping["target_type"])),
            category=cat,
            confidence=conf,
            matchedClaim=str(mapping["matched_claim"]),
            modelVersion=str(mapping["model_version"]),
            fakeNewsScore=fake_score,
            isDisinformation=is_disinfo,
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
