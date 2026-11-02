"""Text normalisation, Romanian diacritic unification, and language detection."""

import hashlib
import re
from typing import Protocol

from app.dtos.collector_dto import DetectedLanguage, NormalisedTextDto

_URL_PATTERN = re.compile(
    r"(?:https?://\S+|www\.\S+|t\.me/[a-zA-Z0-9_/]+)", re.IGNORECASE
)
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
    }
)


def transliterate_cyrillic(text: str) -> str:
    """Converts Russian Cyrillic characters to Latin equivalents for cross-script comparison."""
    return "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in text)


def detect_language(normalised_text: str) -> DetectedLanguage:
    """Classifies normalised text into RO, RU, or OTHER."""
    letters = [ch for ch in normalised_text if ch.isalpha()]
    if not letters:
        return "OTHER"

    cyrillic_count = sum(1 for ch in letters if "\u0400" <= ch <= "\u04ff")
    if cyrillic_count / len(letters) >= 0.35:
        return "RU"

    has_ro_diacritic = any(ch in "ăâîșț" for ch in normalised_text)
    words = set(normalised_text.split())
    if has_ro_diacritic or bool(words & _ROMANIAN_STOPWORDS):
        return "RO"

    return "OTHER"


class ITextNormaliser(Protocol):
    def normalise(self, raw_text: str) -> NormalisedTextDto: ...


class TextNormaliser:
    """Normalises Telegram message text for deduplication and similarity comparison."""

    def normalise(self, raw_text: str) -> NormalisedTextDto:
        without_urls = _URL_PATTERN.sub(" ", raw_text)
        unified = without_urls.translate(_ROMANIAN_CEDILLA_MAP).lower()
        without_punct = _NON_WORD_PATTERN.sub(" ", unified)
        without_underscores = _UNDERSCORE_PATTERN.sub(" ", without_punct)
        normalised = _MULTI_SPACE_PATTERN.sub(" ", without_underscores).strip()

        transliterated = transliterate_cyrillic(normalised)
        text_hash = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
        language = detect_language(normalised)

        return NormalisedTextDto(
            normalisedText=normalised,
            transliteratedText=transliterated,
            textHash=text_hash,
            language=language,
        )
