"""Text normalisation, multi-view representation, and language detection."""

import hashlib
import re
from typing import Protocol

from app.dtos.collector_dto import DetectedLanguage, NormalisedTextDto

_URL_PATTERN = re.compile(r"(?:https?://\S+|www\.\S+|t\.me/[a-zA-Z0-9_/]+)", re.IGNORECASE)
_HANDLE_PATTERN = re.compile(r"@[a-zA-Z0-9_]+")
# Keep Latin (including Romanian diacritics), Cyrillic, digits, and whitespace
_NON_WORD_PATTERN = re.compile(r"[^\w\săâîșțĂÂÎȘȚа-яА-ЯёЁ]", re.UNICODE)
_UNDERSCORE_PATTERN = re.compile(r"_+")
_MULTI_SPACE_PATTERN = re.compile(r"\s+")

_ROMANIAN_CEDILLA_MAP = str.maketrans(
    {
        "ş": "ș",
        "Ş": "ș",
        "ţ": "ț",
        "Ţ": "ț",
        "ă": "ă",
        "Ă": "ă",
        "â": "â",
        "Â": "â",
        "î": "î",
        "Î": "î",
        "Ș": "ș",
        "Ț": "ț",
        "ё": "е",
        "Ё": "е",
    }
)

_I_A_UNIFICATION_MAP = str.maketrans(
    {
        "î": "i",
        "â": "a",
    }
)

_CYRILLIC_TO_LATIN: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

_ROMANIAN_STOPWORDS = frozenset(
    {
        "și",
        "în",
        "la",
        "cu",
        "de",
        "pe",
        "pentru",
        "din",
        "este",
        "sunt",
        "moldova",
        "chișinău",
        "guvernul",
        "prețurile",
        "cetățenii",
        "românia",
        "alegeri",
        "energie",
        "după",
        "acest",
        "care",
        "sau",
        "fost",
        "anunță",
        "gaz",
        "tarif",
        "tariful",
    }
)

_RUSSIAN_STOPWORDS = frozenset(
    {
        "и",
        "в",
        "на",
        "с",
        "по",
        "для",
        "из",
        "молдова",
        "кишинев",
        "правительство",
        "цены",
        "граждане",
        "выборы",
        "энергия",
        "газ",
        "тариф",
        "после",
        "это",
        "что",
    }
)


def transliterate_cyrillic(text: str) -> str:
    """Converts Russian Cyrillic characters to Latin equivalents for cross-script comparison."""
    return "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)


def detect_language(text: str) -> tuple[DetectedLanguage, bool]:
    """Classifies text into RO, RU, MIXED, or OTHER, and detects mixed-script posts."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "OTHER", False

    total_letters = len(letters)
    cyrillic_count = sum(1 for ch in letters if "\u0400" <= ch <= "\u04ff")
    latin_count = sum(1 for ch in letters if "a" <= ch.lower() <= "z" or ch.lower() in "ăâîșț")

    cyrillic_ratio = cyrillic_count / total_letters
    latin_ratio = latin_count / total_letters

    is_mixed = cyrillic_ratio >= 0.15 and latin_ratio >= 0.15
    if is_mixed:
        return "MIXED", True

    if cyrillic_ratio >= 0.35:
        return "RU", False

    has_ro_diacritic = any(ch in "ăâîșțĂÂÎȘȚ" for ch in text)
    words = set(text.lower().split())
    if has_ro_diacritic or bool(words & _ROMANIAN_STOPWORDS):
        return "RO", False

    if bool(words & _RUSSIAN_STOPWORDS):
        return "RU", False

    return "OTHER", False


class ITextNormaliser(Protocol):
    def normalise(self, raw_text: str) -> NormalisedTextDto: ...


class TextNormaliser:
    """Normalises Telegram message text into three distinct views:
    1. text_hash: strong normalisation with î->i, â->a for exact hash and MinHash
    2. text_model: light cleaning for transformer embeddings and classifiers
    3. text_display: original raw text for UI inspection
    """

    def normalise(self, raw_text: str) -> NormalisedTextDto:
        text_display = raw_text

        # 1. Light model text: remove URLs and handles, collapse spaces, preserve case & diacritics
        without_urls = _URL_PATTERN.sub(" ", raw_text)
        without_handles = _HANDLE_PATTERN.sub(" ", without_urls)
        text_model = _MULTI_SPACE_PATTERN.sub(" ", without_handles).strip()

        # 2. Canonical normalised text: unified cedillas, strip punctuation, lowercase
        unified_cedillas = text_model.translate(_ROMANIAN_CEDILLA_MAP).lower()
        without_punct = _NON_WORD_PATTERN.sub(" ", unified_cedillas)
        without_underscores = _UNDERSCORE_PATTERN.sub(" ", without_punct)
        normalised_text = _MULTI_SPACE_PATTERN.sub(" ", without_underscores).strip()

        # 3. Strong hash view: î->i, â->a for hash and minhash stability
        hash_view = normalised_text.translate(_I_A_UNIFICATION_MAP)
        text_hash = hashlib.sha256(hash_view.encode("utf-8")).hexdigest()

        transliterated = transliterate_cyrillic(normalised_text)
        language, is_mixed = detect_language(text_model or raw_text)

        return NormalisedTextDto(
            normalisedText=normalised_text,
            transliteratedText=transliterated,
            textHash=text_hash,
            textModel=text_model,
            textDisplay=text_display,
            language=language,
            isMixedScript=is_mixed,
        )
