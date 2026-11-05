"""Three-stage cross-channel similarity engine v2.

Combines Exact Hash, MinHash+LSH (Adaptive & Verified), and Embeddings with Detail Guard.
"""

import hashlib
import math
import re
from datetime import datetime
from typing import Any, Protocol

from app.dtos.cluster_dto import MatchStage, SimilarityEdgeDto
from app.dtos.collector_dto import StoredMessageDto

_NUM_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?%?\b")
_NEG_TOKENS = frozenset({"nu", "nici", "fara", "fără", "deloc", "не", "нет", "без"})

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
    def embed(self, text: str) -> list[float]: ...


class DeterministicMultilingualEmbedder:
    """Projects Romanian and Russian text into a shared concept vector space (Baseline Lexicon)."""

    def __init__(self, dim: int = 48) -> None:
        self._dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = text.lower().split()
        if not tokens:
            return vec

        for token in tokens:
            matched_concept = False
            for idx, group in enumerate(_CONCEPT_GROUPS):
                if any(token.startswith(stem) or stem in token for stem in group):
                    vec[idx % self._dim] += 2.8
                    matched_concept = True
            if not matched_concept and len(token) >= 4:
                slot = (
                    int(hashlib.md5(token[:4].encode("utf-8")).hexdigest()[:8], 16)
                    % (self._dim - len(_CONCEPT_GROUPS))
                ) + len(_CONCEPT_GROUPS)
                vec[slot] += 0.5

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


# Alias for explicit baseline comparison in evaluation harness
BaselineLexiconEmbedder = DeterministicMultilingualEmbedder


class SentenceTransformerEmbedder:
    """Dense neural multilingual sentence encoder with memory cache and baseline fallback."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self._model_name = model_name
        self._model: Any = None
        self._cache: dict[str, list[float]] = {}
        self._fallback = DeterministicMultilingualEmbedder()

    def _ensure_loaded(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                # Try loading from local cache first to avoid network timeout
                try:
                    self._model = SentenceTransformer(self._model_name, device="cpu", local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self._model_name, device="cpu")
            except Exception:
                self._model = False

    def embed(self, text: str) -> list[float]:
        clean = text.strip()
        if not clean:
            return [0.0] * 48
        if clean in self._cache:
            return self._cache[clean]

        self._ensure_loaded()
        if self._model:
            try:
                raw_vec = self._model.encode(clean, normalize_embeddings=True, show_progress_bar=False).tolist()
                vec: list[float] = [float(x) for x in raw_vec]
                self._cache[clean] = vec
                return vec
            except Exception:
                pass

        vec = self._fallback.embed(clean)
        self._cache[clean] = vec
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


def build_adaptive_shingles(normalised_text: str) -> set[str]:
    """Adaptive shingling: character 4/5-grams for short posts, word n-grams for longer posts."""
    tokens = [t for t in normalised_text.split() if len(t) > 1]
    if len(tokens) <= 12 or len(normalised_text) < 80:
        compact = "".join(normalised_text.split())
        if len(compact) < 4:
            return set(tokens)
        shingles = {compact[i : i + 4] for i in range(len(compact) - 3)}
        if len(compact) >= 5:
            shingles.update(compact[i : i + 5] for i in range(len(compact) - 4))
        return shingles

    shingles = set(tokens)
    for i in range(len(tokens) - 1):
        shingles.add(f"{tokens[i]} {tokens[i + 1]}")
    for i in range(len(tokens) - 2):
        shingles.add(f"{tokens[i]} {tokens[i + 1]} {tokens[i + 2]}")
    return shingles


_MERSENNE_PRIME = 2147483647
# Deterministic universal hash coefficients for 128 permutations
_MINHASH_COEFFS: tuple[tuple[int, int], ...] = tuple(
    (
        ((i * 10007 + 104729) % (_MERSENNE_PRIME - 1)) + 1,
        (i * 32452843 + 49979) % _MERSENNE_PRIME,
    )
    for i in range(128)
)


def compute_minhash_signature(shingles: set[str], num_hashes: int = 128) -> list[int]:
    if not shingles:
        return [0] * num_hashes
    # Hash each shingle once
    base_hashes = [
        int(hashlib.blake2b(s.encode(), digest_size=4).hexdigest(), 16) for s in shingles
    ]
    sig: list[int] = []
    for a, b in _MINHASH_COEFFS[:num_hashes]:
        min_val = min((a * h + b) % _MERSENNE_PRIME for h in base_hashes)
        sig.append(min_val)
    return sig


def estimate_minhash_jaccard(sig_a: list[int], sig_b: list[int]) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    matches = sum(1 for a, b in zip(sig_a, sig_b, strict=True) if a == b)
    return matches / len(sig_a)


def lsh_shares_band(sig_a: list[int], sig_b: list[int], bands: int = 32) -> bool:
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


_TIME_PATTERN = re.compile(r"\b(?:ora\s+)?(?:[01]?\d|2[0-3])[:.][0-5]\d\b", re.IGNORECASE)
_DATE_PATTERN = re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b")
_PERCENT_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?%\b")
_SIGNIFICANT_NUMBER_PATTERN = re.compile(r"\b\d{2,}(?:[\.,]\d+)?\b")

_PREDICATE_NEG_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bnu\s+(?:va|vor|este|sunt|au|exista|există|se|poate|trebuie|s-a|mai)\b", re.IGNORECASE),
    re.compile(r"\bне\s+(?:будет|будут|является|было|может|должен|существует|станет|хочет)\b", re.IGNORECASE),
    re.compile(r"\b(?:fără|без|niciun|niciuna|никаких|никогда)\b", re.IGNORECASE),
)


def check_detail_conflict(text_a: str, text_b: str) -> tuple[bool, str | None]:
    """Detail guard: detects conflicting numbers, key metrics, or assertion negation flips."""
    clean_a = re.sub(r"(?:https?://\S+|www\.\S+|t\.me/\S+)", " ", text_a)
    clean_b = re.sub(r"(?:https?://\S+|www\.\S+|t\.me/\S+)", " ", text_b)

    # 1. Predicate negation conflict on overlapping sentence assertions
    neg_a = any(p.search(clean_a) for p in _PREDICATE_NEG_PATTERNS)
    neg_b = any(p.search(clean_b) for p in _PREDICATE_NEG_PATTERNS)
    words_a = set(re.findall(r"\w+", clean_a.lower())) - _NEG_TOKENS
    words_b = set(re.findall(r"\w+", clean_b.lower())) - _NEG_TOKENS
    common_content = words_a & words_b
    if common_content and len(common_content) >= 3:
        j_content = len(common_content) / len(words_a | words_b)
        if j_content >= 0.35 and neg_a != neg_b:
            return True, "negation_conflict"

    # 2. Key numerical metrics conflict (excluding incidental times and dates)
    no_time_a = _TIME_PATTERN.sub(" ", _DATE_PATTERN.sub(" ", clean_a))
    no_time_b = _TIME_PATTERN.sub(" ", _DATE_PATTERN.sub(" ", clean_b))

    pct_a = set(_PERCENT_PATTERN.findall(no_time_a))
    pct_b = set(_PERCENT_PATTERN.findall(no_time_b))
    if pct_a and pct_b and pct_a != pct_b:
        return True, "number_date_conflict"

    sig_nums_a = set(_SIGNIFICANT_NUMBER_PATTERN.findall(no_time_a))
    sig_nums_b = set(_SIGNIFICANT_NUMBER_PATTERN.findall(no_time_b))
    if sig_nums_a and sig_nums_b and not (sig_nums_a & sig_nums_b):
        return True, "number_date_conflict"

    return False, None


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
        parameter_version: str = "v2.0",
    ) -> list[SimilarityEdgeDto]: ...


class SimilarityService:
    """Similarity Engine v2 with verified LSH, adaptive n-grams, and detail guards."""

    def __init__(self, embedder: IMultilingualEmbedder | None = None) -> None:
        self._embedder = embedder or DeterministicMultilingualEmbedder()

    def get_calibrated_threshold(
        self, lang_a: str, lang_b: str, default_thresh: float = 0.85
    ) -> float:
        """Calibrated similarity thresholds by language pair."""
        if lang_a == "RO" and lang_b == "RO":
            return min(default_thresh, 0.82)
        if lang_a == "RU" and lang_b == "RU":
            return min(default_thresh, 0.82)
        if (lang_a == "RO" and lang_b == "RU") or (lang_a == "RU" and lang_b == "RO"):
            return min(default_thresh, 0.78)
        return default_thresh

    def score_pair(
        self, msg_a: StoredMessageDto, msg_b: StoredMessageDto
    ) -> tuple[float, MatchStage]:
        # 1. Exact SHA-256 hash
        if msg_a.text_hash and msg_a.text_hash == msg_b.text_hash:
            return 1.0, "exact_hash"

        # Check detail conflict before accepting near-duplicate or embedding match
        raw_a = msg_a.raw_text or msg_a.normalised_text
        raw_b = msg_b.raw_text or msg_b.normalised_text
        has_conflict, _ = check_detail_conflict(raw_a, raw_b)

        # 2. Adaptive MinHash + LSH with Verification Step
        shingles_a = build_adaptive_shingles(msg_a.normalised_text)
        shingles_b = build_adaptive_shingles(msg_b.normalised_text)
        sig_a = compute_minhash_signature(shingles_a, num_hashes=128)
        sig_b = compute_minhash_signature(shingles_b, num_hashes=128)

        # Explicit verification: band collision AND estimated Jaccard >= 0.65
        estimated_j = estimate_minhash_jaccard(sig_a, sig_b)
        actual_j = jaccard_similarity(shingles_a, shingles_b)

        if lsh_shares_band(sig_a, sig_b, bands=32) and estimated_j >= 0.65 and actual_j >= 0.65:
            if has_conflict:
                return 0.40, "semantic_embedding"
            scaled_minhash = min(0.99, 0.85 + (actual_j - 0.65) * 0.35)
            return round(scaled_minhash, 4), "minhash_lsh"

        # 3. Multilingual concept vector embeddings (using clean text_model when available)
        embed_input_a = msg_a.text_model or raw_a or msg_a.normalised_text
        embed_input_b = msg_b.text_model or raw_b or msg_b.normalised_text
        vec_a = self._embedder.embed(embed_input_a)
        vec_b = self._embedder.embed(embed_input_b)
        cos_sim = cosine_similarity(vec_a, vec_b)

        if has_conflict:
            # Penalize semantic similarity when facts/dates/numbers or negations directly conflict
            cos_sim = min(0.40, cos_sim * 0.50)

        return round(cos_sim, 4), "semantic_embedding"

    def detect_similar_pairs(
        self,
        messages: list[StoredMessageDto],
        threshold: float = 0.85,
        time_window_minutes: int = 60,
        parameter_version: str = "v2.0",
    ) -> list[SimilarityEdgeDto]:
        max_delta_sec = max(1, time_window_minutes) * 60
        ordered = sorted(messages, key=lambda m: (m.posted_at, m.id))
        edges: list[SimilarityEdgeDto] = []

        # Precompute shingles, signatures, and vectors once per message
        shingles_cache: dict[str, set[str]] = {}
        sig_cache: dict[str, list[int]] = {}
        vec_cache: dict[str, list[float]] = {}
        for m in ordered:
            sh = build_adaptive_shingles(m.normalised_text)
            shingles_cache[m.id] = sh
            sig_cache[m.id] = compute_minhash_signature(sh, num_hashes=128)
            embed_text = m.text_model or m.raw_text or m.normalised_text
            vec_cache[m.id] = self._embedder.embed(embed_text)

        for i in range(len(ordered)):
            msg_a = ordered[i]
            if getattr(msg_a, "skip_similarity", False):
                continue
            ts_a = _parse_iso_seconds(msg_a.posted_at)
            for j in range(i + 1, len(ordered)):
                msg_b = ordered[j]
                if getattr(msg_b, "skip_similarity", False):
                    continue
                if msg_a.channel_id == msg_b.channel_id:
                    continue

                ts_b = _parse_iso_seconds(msg_b.posted_at)
                time_diff = abs(ts_b - ts_a)
                if time_diff > max_delta_sec:
                    continue

                # Calibrated threshold per language pair
                eff_threshold = self.get_calibrated_threshold(
                    msg_a.language, msg_b.language, default_thresh=threshold
                )

                # 1. Exact hash
                stage: MatchStage = "semantic_embedding"
                if msg_a.text_hash and msg_a.text_hash == msg_b.text_hash:
                    score, stage = 1.0, "exact_hash"
                else:
                    raw_a = msg_a.raw_text or msg_a.normalised_text
                    raw_b = msg_b.raw_text or msg_b.normalised_text
                    has_conflict, _ = check_detail_conflict(raw_a, raw_b)

                    # 2. MinHash with cached signatures
                    sh_a = shingles_cache[msg_a.id]
                    sh_b = shingles_cache[msg_b.id]
                    s_a = sig_cache[msg_a.id]
                    s_b = sig_cache[msg_b.id]

                    est_j = estimate_minhash_jaccard(s_a, s_b)
                    act_j = jaccard_similarity(sh_a, sh_b)
                    if lsh_shares_band(s_a, s_b, bands=32) and est_j >= 0.65 and act_j >= 0.65:
                        if has_conflict:
                            score, stage = 0.40, "semantic_embedding"
                        else:
                            scaled = min(0.99, 0.85 + (act_j - 0.65) * 0.35)
                            score, stage = round(scaled, 4), "minhash_lsh"
                    else:
                        # 3. Embedding cosine
                        cos_sim = cosine_similarity(vec_cache[msg_a.id], vec_cache[msg_b.id])
                        if has_conflict:
                            cos_sim = min(0.40, cos_sim * 0.50)
                        score, stage = round(cos_sim, 4), "semantic_embedding"

                if score >= eff_threshold:
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
