"""
Balanced Telegram-style data augmentation for disinformation and benign claims.
Addresses the shortcut risk: applies broadcast noise symmetrically across BOTH classes,
preventing the model from learning formatting cues as class predictors.
NEVER applied to validation, test, or gold evaluation partitions.
"""

import json
import random
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "ml" / "data" / "processed" / "v1"

BROADCAST_PREFIXES_RO = [
    "⚡️ ",
    "🔴 ",
    "👉 ",
    "☝️ ",
    "💬 ",
    "📌 ",
    "❗️ ",
    "🚨 ATENȚIE: ",
    "‼️ BREAKING: ",
    "📢 IMPORTANT: ",
]

BROADCAST_PREFIXES_RU = [
    "⚡️ ",
    "🔴 ",
    "👉 ",
    "☝️ ",
    "💬 ",
    "📌 ",
    "❗️ ",
    "🚨 ВНИМАНИЕ! ",
    "‼️ СРОЧНО: ",
    "📢 ВАЖНО: ",
]

FORWARD_HEADERS_RO = [
    "Redirecționat de la @stiri_chisinau:\n",
    "Preluat din surse locale:\n",
    "Mesaj primit de la un abonat:\n",
    "Transmis pe chat-ul canalului:\n",
]

FORWARD_HEADERS_RU = [
    "Переслано из @moldova_segodnya:\n",
    "Подгон от подписчика:\n",
    "Сообщение из нашего чата:\n",
    "Передают с мест:\n",
]

FOOTERS_RO = [
    "\n\n👉 Abonați-vă la canal pentru actualizări zilnice!",
    "\n\n💬 Distribuiți masiv prietenilor și familiei!",
    "\n\n📌 Detalii suplimentare și discuții în comentarii.",
    "\n\n🔔 Urmăriți fluxul nostru live pe Telegram.",
]

FOOTERS_RU = [
    "\n\n👉 Подписывайтесь на канал и оставайтесь в курсе!",
    "\n\n💬 Срочно пересылайте родным и близким!",
    "\n\n📌 Все подробности в нашем закрытом чате.",
    "\n\n🔔 Подпишитесь, чтобы не пропустить важное.",
]


def apply_balanced_telegram_noise(text: str, language: str, rng: random.Random) -> str:
    """Applies realistic broadcast noise independently of claim veracity."""
    lang = language.lower() if language else "ro"
    prefixes = BROADCAST_PREFIXES_RU if lang == "ru" else BROADCAST_PREFIXES_RO
    headers = FORWARD_HEADERS_RU if lang == "ru" else FORWARD_HEADERS_RO
    footers = FOOTERS_RU if lang == "ru" else FOOTERS_RO

    augmented = text

    # 1. 50% chance to add broadcast prefix emoji/header
    if rng.random() < 0.50:
        augmented = rng.choice(prefixes) + augmented

    # 2. 25% chance to prepend forward attribution
    if rng.random() < 0.25:
        augmented = rng.choice(headers) + augmented

    # 3. 40% chance to append footer/CTA
    if rng.random() < 0.40:
        augmented = augmented + rng.choice(footers)

    return augmented


def generate_augmented_dataset(
    input_train_path: Path,
    telegram_train_path: Path,
    output_train_path: Path,
    seed: int = 42,
) -> dict[str, int]:
    """Generates balanced augmented training set combining clean debunks, benign news, and real Telegram.

    Noise is applied with EXACT symmetry to both disinformation (is_disinformation=True)
    and benign (is_disinformation=False) samples.
    """
    rng = random.Random(seed)

    records: list[dict[str, Any]] = []

    # 1. Load base training items
    with open(input_train_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # 2. Load domain Telegram training items
    if telegram_train_path.exists():
        with open(telegram_train_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))

    disinfo_count_orig = sum(1 for r in records if r.get("is_disinformation", True))
    benign_count_orig = len(records) - disinfo_count_orig

    # Symmetrically augment 35% of disinformation samples and 35% of benign samples
    augmented_records: list[dict[str, Any]] = []
    disinfo_augmented = 0
    benign_augmented = 0

    for r in records:
        is_disinfo = r.get("is_disinformation", True)
        # Symmetrically sample for augmentation
        if rng.random() < 0.35:
            new_r = dict(r)
            new_r["id"] = f"{r['id']}-aug"
            new_r["text"] = apply_balanced_telegram_noise(
                str(r["text"]), str(r.get("language", "ro")), rng
            )
            new_r["notes"] = f"{r.get('notes', '')} [Balanced Telegram-Style Augmentation]"
            augmented_records.append(new_r)
            if is_disinfo:
                disinfo_augmented += 1
            else:
                benign_augmented += 1

    final_corpus = records + augmented_records
    rng.shuffle(final_corpus)

    with open(output_train_path, "w", encoding="utf-8") as f:
        for r in final_corpus:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "original_total": len(records),
        "original_disinfo": disinfo_count_orig,
        "original_benign": benign_count_orig,
        "augmented_total": len(augmented_records),
        "augmented_disinfo": disinfo_augmented,
        "augmented_benign": benign_augmented,
        "final_total": len(final_corpus),
    }
    return stats


if __name__ == "__main__":
    train_in = PROCESSED_DIR / "train.jsonl"
    tg_train_in = PROCESSED_DIR / "telegram_train.jsonl"
    train_out = PROCESSED_DIR / "train_augmented.jsonl"

    print("[*] Generating balanced Telegram-augmented training set...")
    stats = generate_augmented_dataset(train_in, tg_train_in, train_out)
    print(f"[+] Output written to {train_out}")
    print(f"    Original Total: {stats['original_total']} (Disinfo: {stats['original_disinfo']}, Benign: {stats['original_benign']})")
    print(f"    Augmented Added: {stats['augmented_total']} (Disinfo: {stats['augmented_disinfo']}, Benign: {stats['augmented_benign']})")
    print(f"    Final Training Size: {stats['final_total']}")
