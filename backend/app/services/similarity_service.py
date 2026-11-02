"""Three-stage cross-channel similarity engine: Exact Hash, MinHash+LSH, and Embeddings."""

import hashlib
import math
from datetime import datetime
from typing import Protocol

from app.dtos.cluster_dto import MatchStage, SimilarityEdgeDto
from app.dtos.collector_dto import StoredMessageDto

# Shared multilingual concept lexicon (Romanian & Russian stems mapped to canonical concept IDs)
_CONCEPT_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "tarif",
        "tarife",
        "tarifele",
        "pret",
        "preturile",
        "preț",
        "prețurile",
        "тариф",
        "тарифы",
        "цен",
        "цены",
    ),
    (
        "gaz",
        "gaze",
        "energie",
        "electrica",
        "electrică",
        "curent",
        "газ",
        "свет",
        "электроэнерг",
        "энерг",
    ),
    (
        "cresc",
        "creste",
        "crește",
        "exploda",
        "dubla",
        "300",
        "200",
        "50",
        "вырастут",
        "рост",
        "взлетят",
        "вдвое",
    ),
    (
        "chisinau",
        "chișinău",
        "moldova",
        "moldovei",
        "кишинев",
        "кишиневе",
        "молдов",
        "молдове",
        "молдовы",
    ),
    (
        "bruxelles",
        "ue",
        "uniunea",
        "europeana",
        "europeană",
        "directiva",
        "брюссел",
        "ес",
        "евросоюз",
        "европ",
    ),
    (
        "nato",
        "armata",
        "militar",
        "exercitii",
        "exerciții",
        "razboi",
        "război",
        "нато",
        "военн",
        "учения",
        "войн",
    ),
    (
        "alegeri",
        "vot",
        "votare",
        "sectiile",
        "secțiile",
        "frauda",
        "fraudă",
        "выбор",
        "голос",
        "участк",
        "нарушен",
    ),
    (
        "gagauzia",
        "găgăuzia",
        "transnistria",
        "tiraspol",
        "comrat",
        "гагауз",
        "приднестров",
        "тираспол",
        "комрат",
    ),
    (
        "banca",
        "nationala",
        "națională",
        "inflatia",
        "inflației",
        "credite",
        "банк",
        "инфляц",
        "кредит",
    ),
    ("spital", "vaccin", "sanatate", "sănătate", "oms", "больниц", "вакцин", "здрав", "воз"),
    (
        "fermieri",
        "fermierii",
        "agricultori",
        "subventii",
        "subvenții",
        "motorina",
        "аграр",
        "фермер",
        "субсид",
        "трасс",
    ),
    (
        "scoala",
        "școli",
        "limba",
        "rusa",
        "rusă",
        "traditii",
        "tradiții",
        "школ",
        "русск",
        "язык",
        "традиц",
    ),
    ("meteo", "vant", "vânt", "ploi", "cod", "galben", "погод", "ветер", "дожд"),
    ("sport", "fotbal", "stadion", "campionat", "meci", "спорт", "футбол", "матч"),
    (
        "cultura",
        "festival",
        "concert",
        "teatru",
        "muzeu",
        "культур",
        "фестивал",
        "концерт",
        "театр",
    ),
)


class IMultilingualEmbedder(Protocol):
    def embed(self, normalised_text: str) -> list[float]: ...


class DeterministicMultilingualEmbedder:
    """Projects Romanian and Russian normalised text into a shared concept vector space."""

    def __init__(self, dim: int = 48) -> None:
        self._dim = dim

    def embed(self, normalised_text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = normalised_text.split()
        if not tokens:
            return vec

        for token in tokens:
            matched_concept = False
            for idx, group in enumerate(_CONCEPT_GROUPS):
                if any(token.startswith(stem) for stem in group):
                    vec[idx % self._dim] += 2.5
                    matched_concept = True
            if not matched_concept and len(token) >= 4:
                slot = (
                    int(hashlib.md5(token[:4].encode("utf-8")).hexdigest()[:8], 16)
                    % (self._dim - len(_CONCEPT_GROUPS))
                ) + len(_CONCEPT_GROUPS)
                vec[slot] += 0.6

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def build_word_shingles(normalised_text: str) -> set[str]:
    tokens = [t for t in normalised_text.split() if len(t) > 1]
    if not tokens:
        return set()
    shingles = set(tokens)
    for i in range(len(tokens) - 1):
        shingles.add(f"{tokens[i]} {tokens[i + 1]}")
    return shingles


def compute_minhash_signature(shingles: set[str], num_hashes: int = 64) -> list[int]:
    if not shingles:
        return [0] * num_hashes
    sig: list[int] = []
    for seed in range(num_hashes):
        min_hash = min(
            int(
                hashlib.blake2b(
                    f"{seed}:{shingle}".encode(), digest_size=4
                ).hexdigest(),
                16,
            )
            for shingle in shingles
        )
        sig.append(min_hash)
    return sig


def lsh_shares_band(sig_a: list[int], sig_b: list[int], bands: int = 16) -> bool:
    rows_per_band = max(1, len(sig_a) // bands)
    for band_idx in range(bands):
        start = band_idx * rows_per_band
        end = start + rows_per_band
        if sig_a[start:end] == sig_b[start:end]:
            return True
    return False


def jaccard_similarity(shingles_a: set[str], shingles_b: set[str]) -> float:
    if not shingles_a or not shingles_b:
        return 0.0
    union_len = len(shingles_a | shingles_b)
    if union_len == 0:
        return 0.0
    return len(shingles_a & shingles_b) / union_len


def _parse_iso_seconds(iso_str: str) -> int:
    cleaned = iso_str.strip().replace("Z", "+00:00")
    try:
        return int(datetime.fromisoformat(cleaned).timestamp())
    except ValueError:
        return 0


class ISimilarityService(Protocol):
    def score_pair(
        self, msg_a: StoredMessageDto, msg_b: StoredMessageDto
    ) -> tuple[float, MatchStage]: ...
    def detect_similar_pairs(
        self,
        messages: list[StoredMessageDto],
        threshold: float = 0.85,
        time_window_minutes: int = 60,
        parameter_version: str = "v1.4",
    ) -> list[SimilarityEdgeDto]: ...


class SimilarityService:
    """Executes 3-stage cross-channel similarity detection inside a configurable time window."""

    def __init__(self, embedder: IMultilingualEmbedder | None = None) -> None:
        self._embedder = embedder or DeterministicMultilingualEmbedder()

    def score_pair(
        self, msg_a: StoredMessageDto, msg_b: StoredMessageDto
    ) -> tuple[float, MatchStage]:
        if msg_a.text_hash and msg_a.text_hash == msg_b.text_hash:
            return 1.0, "exact_hash"

        shingles_a = build_word_shingles(msg_a.normalised_text)
        shingles_b = build_word_shingles(msg_b.normalised_text)
        sig_a = compute_minhash_signature(shingles_a)
        sig_b = compute_minhash_signature(shingles_b)

        jaccard = jaccard_similarity(shingles_a, shingles_b)
        if lsh_shares_band(sig_a, sig_b) and jaccard >= 0.55:
            scaled_minhash = min(0.99, 0.85 + (jaccard - 0.55) * 0.30)
            return round(scaled_minhash, 4), "minhash_lsh"

        vec_a = self._embedder.embed(msg_a.normalised_text)
        vec_b = self._embedder.embed(msg_b.normalised_text)
        cos_sim = cosine_similarity(vec_a, vec_b)
        return round(cos_sim, 4), "semantic_embedding"

    def detect_similar_pairs(
        self,
        messages: list[StoredMessageDto],
        threshold: float = 0.85,
        time_window_minutes: int = 60,
        parameter_version: str = "v1.4",
    ) -> list[SimilarityEdgeDto]:
        max_delta_sec = max(1, time_window_minutes) * 60
        ordered = sorted(messages, key=lambda m: (m.posted_at, m.id))
        edges: list[SimilarityEdgeDto] = []

        for i in range(len(ordered)):
            msg_a = ordered[i]
            ts_a = _parse_iso_seconds(msg_a.posted_at)
            for j in range(i + 1, len(ordered)):
                msg_b = ordered[j]
                # Never compare messages from the same channel
                if msg_a.channel_id == msg_b.channel_id:
                    continue

                ts_b = _parse_iso_seconds(msg_b.posted_at)
                time_diff = abs(ts_b - ts_a)
                if time_diff > max_delta_sec:
                    continue

                score, stage = self.score_pair(msg_a, msg_b)
                if score >= threshold:
                    edge_id = f"edge-{msg_a.id}-{msg_b.id}"
                    edges.append(
                        SimilarityEdgeDto(
                            id=edge_id,
                            sourceMessageId=msg_a.id,
                            targetMessageId=msg_b.id,
                            sourceChannelId=msg_a.channel_id,
                            targetChannelId=msg_b.channel_id,
                            similarityScore=score,
                            matchStage=stage,
                            timeDiffSeconds=time_diff,
                            parameterVersion=parameter_version,
                        )
                    )
        return edges
