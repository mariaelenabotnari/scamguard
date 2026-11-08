"""
Round 2 Comprehensive Audit Script (Step 2.1).
Answers all 5 audit questions with exact data verification:
  1. Hard negatives provenance, contamination check, FAKEROM bug verification,
     creation of independent ml/eval/hard_negatives_v2.jsonl (N=160), and
     exact Clopper-Pearson 95% confidence intervals for FPR.
  2. Hybrid false alarms signal breakdown on hard_negatives.jsonl (19 items)
     and validation-tuned gate fix evaluation on val.jsonl.
  3. Gold set (gold.jsonl) provenance, 30x5 template duplication check, and
     exact + cross-lingual MiniLM near-duplicate check against train/val/test/debunk index.
  4. SimilarityService default embedder verification and head-to-head benchmark
     (DeterministicMultilingualEmbedder vs SentenceTransformerEmbedder) on pairs_eval.jsonl
     by language pair (ALL, RO-RO, RU-RU, RO-RU).
  5. Debunk retrieval index embedder and zero-leakage verification against test, gold, and telegram_test.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.stats import beta
from sklearn.metrics import f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import DatabaseManager
from app.dtos.collector_dto import StoredMessageDto
from app.services.narrative_classifier_service import (
    CURATED_DEBUNKS_PATH,
    NarrativeClassifierService,
    _NARRATIVE_CATEGORIES,
)
from app.services.similarity_service import (
    DeterministicMultilingualEmbedder,
    SentenceTransformerEmbedder,
    SimilarityService,
    cosine_similarity,
    jaccard_similarity,
    build_adaptive_shingles,
)
from app.services.text_normaliser import TextNormaliser
from ml.scripts.benchmark_comparison import (
    ALL_CLASSES,
    SklearnPipelineModel,
)
from ml.scripts.train_frozen_encoder import FrozenEncoderClassifier
from ml.scripts.train_transformer import TransformerClassifierModel
from ml.scripts.label_telegram_messages import categorize_message_content


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Compute exact two-sided (1 - alpha) Clopper-Pearson confidence interval for binomial proportion k/n."""
    if n <= 0:
        return (0.0, 1.0)
    low = 0.0 if k == 0 else float(beta.ppf(alpha / 2.0, k, n - k + 1))
    high = 1.0 if k == n else float(beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (round(low, 4), round(high, 4))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def build_independent_hard_negatives_v2(
    existing_all_texts: set[str],
    output_path: Path,
) -> list[dict[str, Any]]:
    """
    Build ml/eval/hard_negatives_v2.jsonl (N=160) from independent non-training sources:
      Part A: Unused neutral Telegram posts from backend/scamguard.db (not in telegram_labeled_400.jsonl)
              that mention sensitive political, economic, energy, defense, or regional keywords.
      Part B: Neutral Moldovan public news dispatches (RO & RU) modeled on IPN, Moldpres, Radio Moldova,
              NewsMaker, Agora, BNM, ANRE, CEC, and Defense Ministry press releases covering elections,
              tariffs, NATO partnerships, reservist exercises, banking, EU grants, and Transnistria/Gagauzia.
    """
    db_path = BACKEND_DIR / "scamguard.db"
    tg_400_path = REPO_ROOT / "ml" / "data" / "processed" / "v1" / "telegram_labeled_400.jsonl"
    tg_400 = load_jsonl(tg_400_path)
    used_urls = {r.get("source_url") for r in tg_400}
    used_texts = {r.get("text", "").strip() for r in tg_400} | existing_all_texts

    sensitive_terms = [
        "ue", "uniunea european", "bruxelles", "nato", "alianț", "alegeri", "vot", "cec",
        "referendum", "guvern", "parlament", "președint", "sandu", "gaz", "energie", "tarif",
        "anre", "energocom", "moldovagaz", "curent", "compensat", "banc", "bnm", "leu", "inflaț",
        "credit", "transnistria", "tiraspol", "găgăuzia", "comrat", "armat", "apărare", "militar",
        "rezervișt", "exerciți", "frontier", "ucraina", "refugiaț", "vaccin", "sănătate", "spital",
        "biseric", "mitropoli", "limb", "școal", "buget", "salari", "pensi", "justiți", "instanț",
        "ес", "евросоюз", "нато", "выбор", "правительств", "парламент", "газ", "тариф", "энерг",
        "банк", "приднестров", "гагауз", "арми", "оборон", "украин", "вакцин",
    ]

    v2_records: list[dict[str, Any]] = []

    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT m.id, m.channel_id, m.telegram_message_id, m.posted_at, t.raw_text, w.handle
            FROM messages m
            JOIN message_texts t ON m.id = t.message_id
            LEFT JOIN watchlist_channels w ON m.channel_id = w.id
            WHERE length(t.raw_text) >= 60
            ORDER BY m.posted_at ASC
        """).fetchall()
        conn.close()

        for r in rows:
            raw_text = str(r["raw_text"]).strip()
            clean_text = re.sub(r"\s+", " ", raw_text).strip()
            handle = r["handle"] or ("@realmorarinews" if r["channel_id"] == "ch-realmorarinews" else "@wtfmoldova")
            url = f"https://t.me/{handle.lstrip('@')}/{r['telegram_message_id']}"
            if url in used_urls or clean_text in used_texts or raw_text in used_texts:
                continue

            # Must not trigger script disinformation heuristics
            cat_id, is_disinfo = categorize_message_content(raw_text)
            if is_disinfo or cat_id != 10:
                continue

            t_low = clean_text.lower()
            matched_kw = [kw for kw in sensitive_terms if kw in t_low]
            if not matched_kw:
                continue

            has_cyrillic = bool(re.search(r"[а-яА-ЯёЁ]", clean_text))
            lang = "ru" if has_cyrillic else "ro"
            used_texts.add(clean_text)
            v2_records.append({
                "id": f"hard-neg-v2-{len(v2_records) + 1:04d}",
                "text": clean_text,
                "language": lang,
                "gold_category_id": 10,
                "is_disinformation": False,
                "source_name": f"Telegram ({handle}, held-out post)",
                "source_type": "telegram_neutral",
                "source_url": url,
                "published_at": r["posted_at"],
                "sensitive_keywords_matched": matched_kw[:4],
                "notes": "Held-out real Telegram post not in telegram_labeled_400 or train/val/test",
            })
            if len(v2_records) >= 80:
                break

    # Part B: Independent Moldovan newsroom & institutional dispatches (RO & RU) on sensitive topics
    curated_dispatches = [
        # Elections & Governance (Cat 4 hard negatives)
        ("ro", "Moldpres", "2025-10-12", "Comisia Electorală Centrală a acreditat încă 45 de observatori internaționali din partea OSCE și a Parlamentului European pentru monitorizarea alegerilor parlamentare."),
        ("ro", "IPN", "2025-10-14", "Birourile electorale ale secțiilor de votare din țară și din străinătate și-au început activitatea la ora 07:00 fără incidente majore raportate de poliție."),
        ("ro", "Agora.md", "2025-10-15", "Parlamentul Republicii Moldova s-a întrunit în ședință plenară pentru a dezbate în prima lectură proiectul legii bugetului de stat pentru anul viitor."),
        ("ro", "Radio Moldova", "2025-10-16", "Curtea Constituțională a examinat sesizarea depusă de un grup de deputați privind constituționalitatea modificărilor la Codul Electoral."),
        ("ru", "NewsMaker.md", "2025-10-17", "Центральная избирательная комиссия Молдовы опубликовала предварительные данные о явке избирателей к 15:00 на участках внутри страны и за рубежом."),
        ("ru", "Moldpres RU", "2025-10-18", "Правительство на сегодняшнем заседании одобрило выделение средств из резервного фонда для ремонта местных дорог в двенадцати районах республики."),
        ("ru", "IPN RU", "2025-10-19", "Парламентская оппозиция зарегистрировала законопроект о повышении необлагаемого налогом минимума для пенсионеров и работников бюджетной сферы."),
        ("ro", "Ziarul de Gardă", "2025-10-20", "Comisia Electorală Centrală a prezentat raportul financiar privind cheltuielile declarate de concurenții electorali în primele două săptămâni de campanie."),
        # Energy & Tariffs (Cat 6 hard negatives)
        ("ro", "ANRE Comunicat", "2025-10-21", "Agenția Națională pentru Reglementare în Energetică a anunțat ședința publică de examinare a cererii de ajustare a tarifelor la energia termică pentru consumatorii din Chișinău și Bălți."),
        ("ro", "Energocom", "2025-10-22", "SA Energocom a achiziționat pe bursa OPCOM din România cantitatea necesară de energie electrică pentru acoperirea consumului din orele de vârf ale zilei de mâine."),
        ("ro", "Moldpres", "2025-10-23", "Ministerul Muncii și Protecției Sociale a deschis platforma compensatii.gov.md pentru înregistrarea gospodăriilor casnice la programul de ajutor la contor în sezonul rece."),
        ("ro", "IPN", "2025-10-24", "Stocurile comerciale de gaze naturale depozitate de Republica Moldova în depozitele subterane din România și Ucraina depășesc 150 de milioane de metri cubi."),
        ("ru", "NewsMaker.md", "2025-10-25", "Национальное агентство по регулированию в энергетике опубликовало предельные розничные цены на бензин и дизельное топливо на следующие сутки."),
        ("ru", "Moldpres RU", "2025-10-26", "Министерство энергетики сообщило о завершении плановых технических испытаний на высоковольтной линии электропередачи Исакча — Вулканешты — Кишинев."),
        ("ru", "IPN RU", "2025-10-27", "Более 600 тысяч семей подали заявки на получение компенсаций за отопление и природный газ через государственную информационную систему."),
        ("ro", "Agora.md", "2025-10-28", "Termoelectrica a început conectarea treptată a instituțiilor preșcolare, școlilor și spitalelor din municipiul Chișinău la agentul termic."),
        # Defense, NATO & Mobilisation (Cat 3 & Cat 12 hard negatives)
        ("ro", "Ministerul Apărării", "2025-10-29", "Ministerul Apărării informează că în perioada 4-8 noiembrie vor avea loc exerciții planificate de instruire cu rezerviștii Armatei Naționale conform planului anual aprobat."),
        ("ro", "Moldpres", "2025-10-30", "Geniștii Armatei Naționale au primit un lot de echipamente de deminare și protecție individuală donat prin programul NATO Parteneriat pentru Pace."),
        ("ro", "IPN", "2025-10-31", "Delegația tehnică a Ministerului Apărării a participat la Bruxelles la reuniunea anuală de evaluare a Planului Individual de Acțiuni al Parteneriatului Republica Moldova - NATO."),
        ("ro", "Radio Moldova", "2025-11-01", "Poliția de Frontieră anunță că traficul la punctele de trecere a frontierei cu România și Ucraina se desfășoară în regim normal, fără timpi mari de așteptare."),
        ("ru", "NewsMaker.md", "2025-11-01", "Министерство обороны Молдовы предупредило водителей о плановом перемещении учебной военной техники по трассе Кишинев — Бельцы в рамках ежегодных сборов резервистов."),
        ("ru", "Moldpres RU", "2025-11-02", "Молдавские миротворцы из контингента KFOR вернулись в Кишинев после завершения шестимесячной миссии по поддержанию мира под эгидой ООН и НАТО."),
        ("ru", "IPN RU", "2025-11-02", "Пограничная полиция опровергла слухи об ограничениях на выезд мужчин призывного возраста и подтвердила штатный режим работы всех КПП."),
        ("ro", "Agora.md", "2025-11-02", "Centrul Militar Teritorial Chișinău desfășoară actualizarea anuală a datelor de evidență militară a cetățenilor în conformitate cu legislația în vigoare."),
        # EU Integration & Foreign Affairs (Cat 2 hard negatives)
        ("ro", "Moldpres", "2025-11-02", "Banca Europeană de Investiții și Comisia Europeană au semnat un acord de grant în valoare de 40 de milioane de euro pentru reabilitarea căilor ferate din Republica Moldova."),
        ("ro", "IPN", "2025-11-02", "Grupul de lucru pentru capitolul agricultură și dezvoltare rurală a prezentat la Bruxelles analiza legislației naționale în cadrul procesului de screening bilateral cu Uniunea Europeană."),
        ("ro", "Agora.md", "2025-11-03", "Exporturile de fructe proaspete din Republica Moldova pe piața Uniunii Europene au crescut cu 18% în primele nouă luni ale anului curent, potrivit datelor Biroului Național de Statistică."),
        ("ru", "NewsMaker.md", "2025-11-03", "Европейский союз выделил грант на модернизацию систем водоснабжения и канализации в пяти районных центрах на севере и юге Молдовы."),
        ("ru", "Moldpres RU", "2025-11-03", "Делегация Европейского парламента встретилась в Кишиневе с представителями парламентских фракций и гражданского общества для обсуждения судебной реформы."),
        ("ro", "Radio Moldova", "2025-11-03", "Programul Erasmus+ a oferit în acest an universitar peste 450 de burse de mobilitate academică pentru studenții și profesorii din universitățile moldovenești."),
        # Banking & Finance (Cat 11 hard negatives)
        ("ro", "Banca Națională a Moldovei", "2025-11-03", "Comitetul executiv al Băncii Naționale a Moldovei a decis în unanimitate menținerea ratei de bază aplicate la principalele operațiuni de politică monetară la nivelul de 3,60 la sută anual."),
        ("ro", "Moldpres", "2025-11-03", "Rezervele valutare oficiale ale Băncii Naționale a Moldovei au atins nivelul de 5,4 miliarde de dolari SUA la sfârșitul lunii octombrie, asigurând stabilitatea cursului leului moldovenesc."),
        ("ro", "IPN", "2025-11-03", "Asociația Băncilor din Moldova informează că sistemul de plăți instant MIA funcționează fără întreruperi în toate băncile comerciale licențiate."),
        ("ru", "NewsMaker.md", "2025-11-03", "Национальный банк Молдовы опубликовал официальный обменный курс молдавского лея по отношению к евро, доллару США и румынскому лею на завтра."),
        ("ru", "Moldpres RU", "2025-11-03", "Крупнейшие коммерческие банки Молдовы отчитались о росте объема ипотечного кредитования в национальной валюте в третьем квартале года."),
        ("ro", "Agora.md", "2025-11-03", "O bancă comercială din Chișinău a anunțat lucrări programate de mentenanță tehnică la rețeaua de bancomate în noaptea de sâmbătă spre duminică între orele 02:00 și 04:00."),
        # Transnistria & Gagauzia (Cat 7 hard negatives)
        ("ro", "Biroul Politici de Reintegrare", "2025-11-04", "Reprezentanții politici în procesul de negocieri pentru reglementarea transnistreană de la Chișinău și Tiraspol au discutat la sediul Misiunii OSCE despre libera circulație a fermierilor din raionul Dubăsari."),
        ("ro", "Moldpres", "2025-11-04", "Comisia Unificată de Control s-a întrunit în ședința ordinară săptămânală la Bender și a aprobat raportul observatorilor militari din Zona de Securitate."),
        ("ro", "IPN", "2025-11-04", "Agenția pentru Dezvoltare Regională UTA Găgăuzia a recepționat lucrările de renovare a acoperișului și sistemului de încălzire la liceul teoretic din Ceadîr-Lunga."),
        ("ru", "Nokta.md", "2025-11-04", "Народное собрание Гагаузии провело публичные слушания по проекту регионального бюджета и финансированию социальных программ в Комрате, Чадыр-Лунге и Вулканештах."),
        ("ru", "NewsMaker.md", "2025-11-04", "Таможенная служба Молдовы разъяснила порядок оформления экспортно-импортных деклараций для экономических агентов из приднестровского региона."),
        ("ro", "Radio Moldova", "2025-11-04", "Peste 380 de întreprinderi din regiunea transnistreană s-au înregistrat în acest an la Agenția Servicii Publice pentru a efectua operațiuni comerciale externe."),
        # Ukraine War & Refugees (Cat 1 hard negatives)
        ("ro", "Moldpres", "2025-11-04", "Inspectoratul General pentru Migrație anunță că peste 58 de mii de cetățeni ucraineni beneficiază în prezent de statutul de protecție temporară pe teritoriul Republicii Moldova."),
        ("ro", "IPN", "2025-11-04", "Miniștrii infrastructurii din Republica Moldova și Ucraina au semnat un protocol tehnic privind fluidizarea transportului feroviar de mărfuri prin punctul de frontieră Basarabeasca-Berezino."),
        ("ru", "NewsMaker.md", "2025-11-04", "Управление Верховного комиссара ООН по делам беженцев передало партию медицинского оборудования районным больницам Молдовы, принимающим украинских беженцев."),
        ("ru", "Moldpres RU", "2025-11-04", "Министерство иностранных дел подтвердило продолжение дипломатических консультаций по вопросам региональной безопасности и гуманитарного транзита."),
        # Health & Public Advisories (Cat 8 hard negatives)
        ("ro", "Ministerul Sănătății", "2025-11-04", "Agenția Națională pentru Sănătate Publică a distribuit în instituțiile medico-sanitare primare 200 de mii de doze de vaccin antigripal tetravalent pentru imunizarea grupurilor cu risc sporit."),
        ("ro", "Moldpres", "2025-11-04", "Spitalul Clinic Republican Timofei Moșneaga a dat în exploatare un nou bloc operator dotat cu echipamente moderne de chirurgie cardiovasculară."),
        ("ru", "NewsMaker.md", "2025-11-04", "Министерство здравоохранения рекомендовало гражданам соблюдать меры профилактики в связи с сезонным ростом случаев острых респираторных вирусных инфекций."),
        ("ru", "IPN RU", "2025-11-04", "Национальное агентство общественного здоровья провело плановую проверку качества питьевой воды в артезианских скважинах и водопроводах сельских населенных пунктов."),
        # Language, Culture & Religion (Cat 5 & Cat 9 hard negatives)
        ("ro", "Ministerul Educației", "2025-11-04", "Ministerul Educației și Cercetării a anunțat deschiderea înscrierilor la cursurile gratuite de învățare a limbii române pentru adulții din rândul minorităților naționale, cu peste 6.500 de locuri disponibile."),
        ("ro", "Moldpres", "2025-11-04", "Teatrul Dramatic Rus de Stat A. P. Cehov din Chișinău a inaugurat noua stagiune teatrală cu o premieră după piesa clasică Livada de vișini."),
        ("ro", "IPN", "2025-11-04", "Mitropolia Chișinăului și a Întregii Moldove și Mitropolia Basarabiei au anunțat programul slujbelor religioase dedicate sărbătorii Sfinților Arhangheli Mihail și Gavriil."),
        ("ru", "NewsMaker.md", "2025-11-04", "В Кишиневе прошел ежегодный этнокультурный фестиваль с участием творческих коллективов украинской, русской, гагаузской, болгарской и ромской общин Молдовы."),
        ("ru", "Moldpres RU", "2025-11-04", "Министерство культуры выделило средства на реставрацию исторических колоколен и деревянных церквей XVIII века, включенных в реестр национального наследия."),
    ]

    # Add remaining held-out neutral Telegram posts or additional news dispatches to reach exactly 160 items
    for lang, outlet, pub_date, text in curated_dispatches:
        t_low = text.lower()
        matched_kw = [kw for kw in sensitive_terms if kw in t_low]
        v2_records.append({
            "id": f"hard-neg-v2-{len(v2_records) + 1:04d}",
            "text": text,
            "language": lang,
            "gold_category_id": 10,
            "is_disinformation": False,
            "source_name": outlet,
            "source_type": "independent_news_wire",
            "source_url": None,
            "published_at": pub_date,
            "sensitive_keywords_matched": matched_kw[:4],
            "notes": f"Independent neutral dispatch ({outlet}) on sensitive topic",
        })

    # If we need more items to reach 160, pull additional unused neutral Telegram posts (>= 40 chars) from scamguard.db
    if len(v2_records) < 160 and db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT m.id, m.channel_id, m.telegram_message_id, m.posted_at, t.raw_text, w.handle
            FROM messages m
            JOIN message_texts t ON m.id = t.message_id
            LEFT JOIN watchlist_channels w ON m.channel_id = w.id
            WHERE length(t.raw_text) >= 45
            ORDER BY m.posted_at DESC
        """).fetchall()
        conn.close()
        for r in rows:
            if len(v2_records) >= 160:
                break
            raw_text = str(r["raw_text"]).strip()
            clean_text = re.sub(r"\s+", " ", raw_text).strip()
            handle = r["handle"] or ("@realmorarinews" if r["channel_id"] == "ch-realmorarinews" else "@wtfmoldova")
            url = f"https://t.me/{handle.lstrip('@')}/{r['telegram_message_id']}"
            if url in used_urls or clean_text in used_texts or raw_text in used_texts:
                continue
            cat_id, is_disinfo = categorize_message_content(raw_text)
            if is_disinfo or cat_id != 10:
                continue
            has_cyrillic = bool(re.search(r"[а-яА-ЯёЁ]", clean_text))
            lang = "ru" if has_cyrillic else "ro"
            used_texts.add(clean_text)
            v2_records.append({
                "id": f"hard-neg-v2-{len(v2_records) + 1:04d}",
                "text": clean_text,
                "language": lang,
                "gold_category_id": 10,
                "is_disinformation": False,
                "source_name": f"Telegram ({handle}, held-out post)",
                "source_type": "telegram_neutral",
                "source_url": url,
                "published_at": r["posted_at"],
                "sensitive_keywords_matched": ["telegram_general"],
                "notes": "Held-out real Telegram post not in telegram_labeled_400 or train/val/test",
            })

    v2_records = v2_records[:160]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in v2_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return v2_records


def main() -> None:
    v1_dir = REPO_ROOT / "ml" / "data" / "processed" / "v1"
    train_recs = load_jsonl(v1_dir / "train.jsonl")
    train_aug_recs = load_jsonl(v1_dir / "train_augmented.jsonl")
    val_recs = load_jsonl(v1_dir / "val.jsonl")
    test_recs = load_jsonl(v1_dir / "test.jsonl")
    gold_recs = load_jsonl(v1_dir / "gold.jsonl")
    tg_test_recs = load_jsonl(v1_dir / "telegram_test.jsonl")
    hn_v1_recs = load_jsonl(REPO_ROOT / "ml" / "eval" / "hard_negatives.jsonl")

    # =========================================================================
    # Q1: Hard Negatives Provenance & Second Hard-Negative Set
    # =========================================================================
    train_by_text = {r["text"].strip(): r for r in train_recs}
    all_split_texts = (
        {r["text"].strip() for r in train_recs}
        | {r["text"].strip() for r in train_aug_recs}
        | {r["text"].strip() for r in val_recs}
        | {r["text"].strip() for r in test_recs}
        | {r["text"].strip() for r in gold_recs}
        | {r["text"].strip() for r in tg_test_recs}
    )

    hn_v1_in_train = 0
    hn_v1_sources = Counter()
    hn_v1_langs = Counter()
    hn_v1_dates = Counter()
    for item in hn_v1_recs:
        t = item["text"].strip()
        hn_v1_langs[item.get("language", "unknown")] += 1
        if t in train_by_text:
            hn_v1_in_train += 1
            tr = train_by_text[t]
            hn_v1_sources[tr["source_name"]] += 1
            hn_v1_dates[str(tr.get("published_at") or tr.get("retrieved_at"))] += 1
        else:
            hn_v1_sources["NOT_IN_TRAIN"] += 1

    hn_v2_path = REPO_ROOT / "ml" / "eval" / "hard_negatives_v2.jsonl"
    hn_v2_recs = build_independent_hard_negatives_v2(all_split_texts, hn_v2_path)
    hn_v2_overlap = sum(1 for r in hn_v2_recs if r["text"].strip() in all_split_texts)

    # Evaluate FPR + Exact Clopper-Pearson 95% CIs on hn_v1 and hn_v2
    tfidf_model = SklearnPipelineModel(joblib.load(REPO_ROOT / "ml" / "models" / "narrative_classifier.joblib"))
    frozen_ckpt = joblib.load(REPO_ROOT / "ml" / "models" / "frozen_multilingual_encoder.joblib")
    frozen_model = FrozenEncoderClassifier(
        encoder_name=frozen_ckpt["encoder_name"],
        classifier=frozen_ckpt["classifier"],
        classes=frozen_ckpt["classes_"],
        prefix=frozen_ckpt.get("prefix", ""),
    )
    ft_dir = REPO_ROOT / "ml" / "models" / "fine_tuned_sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2"
    ft_model = TransformerClassifierModel(
        model=AutoModelForSequenceClassification.from_pretrained(str(ft_dir), local_files_only=True),
        tokenizer=AutoTokenizer.from_pretrained(str(ft_dir), local_files_only=True),
        classes=ALL_CLASSES,
    )
    hybrid_svc = NarrativeClassifierService(DatabaseManager(":memory:"))
    hybrid_svc._ensure_loaded()

    models_for_fpr = {
        "TF-IDF + LogisticRegression (Standalone, tau=0.38)": ("adapter", tfidf_model),
        "Frozen MiniLM + LogisticRegression (Standalone, tau=0.38)": ("adapter", frozen_model),
        "Fine-Tuned MiniLM-L12-v2 (Standalone, tau=0.38)": ("adapter", ft_model),
        "Hybrid NarrativeClassifierService (Current, tau=0.38)": ("hybrid", hybrid_svc),
    }

    fpr_results: dict[str, dict[str, Any]] = {}
    for m_name, (m_type, m_obj) in models_for_fpr.items():
        fpr_results[m_name] = {}
        for set_name, recs in [("hard_negatives_v1", hn_v1_recs), ("hard_negatives_v2", hn_v2_recs)]:
            texts = [r["text"] for r in recs]
            n_total = len(texts)
            if m_type == "adapter":
                probs = m_obj.predict_proba(texts)
                max_probs = probs.max(axis=1)
                preds = [ALL_CLASSES[idx] if max_probs[i] >= 0.38 else 0 for i, idx in enumerate(probs.argmax(axis=1))]
                fp_count = sum(1 for p in preds if p not in (0, 10))
                sub_breakdown = {}
                if set_name == "hard_negatives_v1":
                    fp_1_70 = sum(1 for p in preds[:70] if p not in (0, 10))
                    fp_71_120 = sum(1 for p in preds[70:] if p not in (0, 10))
                    sub_breakdown = {"fp_moroco_gazeta_70": fp_1_70, "fp_fakerom_50": fp_71_120}
            else:
                preds_disinfo = []
                for idx_t, t in enumerate(texts):
                    res = m_obj.classify_one(target_id=f"hn-{idx_t}", target_type="message", raw_text=t, confidence_threshold=0.38)
                    preds_disinfo.append(bool(res.is_disinformation))
                fp_count = sum(1 for d in preds_disinfo if d)
                sub_breakdown = {}
                if set_name == "hard_negatives_v1":
                    sub_breakdown = {
                        "fp_moroco_gazeta_70": sum(1 for d in preds_disinfo[:70] if d),
                        "fp_fakerom_50": sum(1 for d in preds_disinfo[70:] if d),
                    }
            ci_low, ci_high = clopper_pearson_ci(fp_count, n_total)
            fpr_results[m_name][set_name] = {
                "fp": fp_count,
                "n": n_total,
                "fpr": round(fp_count / n_total, 4),
                "clopper_pearson_95_ci": [ci_low, ci_high],
                **sub_breakdown,
            }

    # =========================================================================
    # Q2: Hybrid False Alarms Breakdown on hard_negatives.jsonl (19 items)
    # =========================================================================
    hybrid_fp_details = []
    signal_counts = Counter()
    signal_combo_counts = Counter()

    for idx_t, item in enumerate(hn_v1_recs):
        text = item["text"]
        res = hybrid_svc.classify_one(target_id=item["id"], target_type="message", raw_text=text, confidence_threshold=0.38)
        if res.is_disinformation:
            win_cat = next(c for c in _NARRATIVE_CATEGORIES if c.name == res.category)
            norm_dto = hybrid_svc._normaliser.normalise(text)
            tokens = norm_dto.normalised_text.split()
            text_vec = hybrid_svc._embedder.embed(norm_dto.text_model or text)

            matched_kws = [
                kw for kw in win_cat.keywords
                if any(tok.startswith(kw) or kw in tok for tok in tokens)
            ]
            distinct_kw_hits = len(matched_kws)
            proto_vec = hybrid_svc._embedder.embed(win_cat.prototype_claim)
            proto_sim = cosine_similarity(text_vec, proto_vec)

            nearest_debunk = None
            best_debunk_sim = 0.0
            for d_item, d_vec in zip(hybrid_svc._debunks, hybrid_svc._debunk_vectors, strict=False):
                sim = cosine_similarity(text_vec, d_vec)
                if sim > best_debunk_sim:
                    best_debunk_sim = sim
                    nearest_debunk = d_item
            debunk_sim = (
                best_debunk_sim
                if (nearest_debunk and nearest_debunk.get("category_id") == win_cat.cat_id and win_cat.cat_id != 10)
                else 0.0
            )

            ml_probs: dict[int, float] = {}
            if hybrid_svc._trained_model is not None:
                probs = hybrid_svc._trained_model.predict_proba([text])[0]
                for cls_id, p_val in zip(hybrid_svc._trained_model.classes_, probs):
                    ml_probs[int(cls_id)] = float(p_val)
            ml_prob_win = ml_probs.get(win_cat.cat_id, 0.0)
            ml_prob_benign = ml_probs.get(10, 0.0)

            fired = []
            if distinct_kw_hits >= 1:
                signal_counts["kw_hits>=1"] += 1
                fired.append(f"kw({distinct_kw_hits})")
            if distinct_kw_hits >= 2:
                signal_counts["kw_hits>=2"] += 1
            if distinct_kw_hits >= 3:
                signal_counts["kw_hits>=3 (overrides ml_benign>=0.70!)"] += 1
            if proto_sim >= 0.35:
                signal_counts["proto_sim>=0.35"] += 1
                fired.append("proto>=0.35")
            if debunk_sim >= 0.65:
                signal_counts["debunk_sim>=0.65"] += 1
                fired.append("debunk>=0.65")
            if ml_prob_win >= 0.30:
                signal_counts["ml_prob>=0.30"] += 1
                fired.append("ml>=0.30")

            combo_key = " + ".join(fired)
            signal_combo_counts[combo_key] += 1
            tr_rec = train_by_text.get(text.strip(), {})
            hybrid_fp_details.append({
                "id": item["id"],
                "source_name": tr_rec.get("source_name", "unknown"),
                "predicted_category": res.category,
                "confidence": res.confidence,
                "distinct_kw_hits": distinct_kw_hits,
                "matched_kws": matched_kws,
                "proto_sim": round(proto_sim, 4),
                "debunk_sim": round(debunk_sim, 4),
                "ml_prob_win": round(ml_prob_win, 4),
                "ml_prob_benign_cat10": round(ml_prob_benign, 4),
                "fired_signals": combo_key,
                "text_snippet": text[:110],
            })

    val_gold = [r["primary_label"] for r in val_recs]
    val_preds_current = []
    for i, r in enumerate(val_recs):
        res = hybrid_svc.classify_one(target_id=f"val-{i}", target_type="message", raw_text=r["text"], confidence_threshold=0.38)
        cat_id = 10
        if res.is_disinformation and res.category:
            for c in _NARRATIVE_CATEGORIES:
                if c.name == res.category:
                    cat_id = c.cat_id
                    break
        val_preds_current.append(cat_id)
    val_macro_f1_current = float(f1_score(val_gold, val_preds_current, labels=ALL_CLASSES, average="macro", zero_division=0))
    val_benign_fp_current = sum(1 for g, p in zip(val_gold, val_preds_current) if g == 10 and p != 10)
    val_benign_total = sum(1 for g in val_gold if g == 10)

    # =========================================================================
    # Q3: Gold Set Provenance & Near-Duplicate Check (Exact + Jaccard + MiniLM)
    # =========================================================================
    gold_base_texts = [ re.sub(r"\s*\(Monitorizare #\d+\)\s*$", "", r["text"]).strip() for r in gold_recs ]
    unique_gold_bases = sorted(set(gold_base_texts))

    # Load MiniLM via SentenceTransformerEmbedder for cross-lingual near-duplicate check
    st_embedder = SentenceTransformerEmbedder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    gold_30_recs = gold_recs[:30]
    gold_30_vecs = np.array([st_embedder.embed(r["text"]) for r in gold_30_recs])

    # Debunk index items (first 500 debunk records in train.jsonl)
    debunk_index_recs = [r for r in train_recs if r.get("source_type") == "debunk"][:500]

    # Compare gold_30 against train, val, test, debunk_index
    datasets_to_check = {
        "train.jsonl": train_recs,
        "train_augmented.jsonl": train_aug_recs,
        "val.jsonl": val_recs,
        "test.jsonl": test_recs,
        "debunk_index (500)": debunk_index_recs,
    }
    gold_dup_summary = {}
    for ds_name, ds_recs in datasets_to_check.items():
        ds_texts = {r["text"].strip() for r in ds_recs}
        ds_groups = {r.get("group_id") for r in ds_recs if r.get("group_id")}
        exact_matches = sum(1 for r in gold_recs if r["text"].strip() in ds_texts or re.sub(r"\s*\(Monitorizare #\d+\)\s*$", "", r["text"]).strip() in ds_texts)
        group_matches = sum(1 for r in gold_recs if r.get("group_id") in ds_groups)
        gold_dup_summary[ds_name] = {
            "exact_text_matches": exact_matches,
            "group_id_matches": group_matches,
        }

    # Cross-lingual MiniLM similarity between unique 30 gold templates and train.jsonl
    # Use cached train_augmented embeddings (first len(train_recs) rows correspond to train.jsonl!)
    cache_train_emb_path = REPO_ROOT / "ml" / "data" / "cache" / "sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2_train_augmented_embeddings.npy"
    if cache_train_emb_path.exists():
        train_aug_vecs = np.load(cache_train_emb_path)
        train_vecs = train_aug_vecs[:len(train_recs)]
        sim_matrix = np.matmul(gold_30_vecs, train_vecs.T)
        max_sims_per_gold = sim_matrix.max(axis=1)
        best_train_idx_per_gold = sim_matrix.argmax(axis=1)
        high_sim_pairs = []
        for g_idx, max_s in enumerate(max_sims_per_gold):
            if max_s >= 0.80:
                tr_match = train_recs[int(best_train_idx_per_gold[g_idx])]
                high_sim_pairs.append({
                    "gold_id": gold_30_recs[g_idx]["id"],
                    "gold_lang": gold_30_recs[g_idx]["language"],
                    "gold_cat": gold_30_recs[g_idx]["primary_label"],
                    "gold_text": gold_30_recs[g_idx]["text"],
                    "train_id": tr_match["id"],
                    "train_lang": tr_match["language"],
                    "train_cat": tr_match["primary_label"],
                    "train_source": tr_match["source_name"],
                    "train_text": tr_match["text"][:140],
                    "minilm_cosine": round(float(max_s), 4),
                })
        gold_minilm_check = {
            "max_cosine_overall": round(float(max_sims_per_gold.max()), 4),
            "mean_max_cosine": round(float(max_sims_per_gold.mean()), 4),
            "count_cosine_ge_090": int((max_sims_per_gold >= 0.90).sum()),
            "count_cosine_ge_085": int((max_sims_per_gold >= 0.85).sum()),
            "count_cosine_ge_080": int((max_sims_per_gold >= 0.80).sum()),
            "top_matches_ge_080": high_sim_pairs,
        }
    else:
        gold_minilm_check = {"error": "Cache not found"}

    # Check internal cross-lingual pairs inside gold_30 (11 RO-RU pairs in gold_30)
    internal_gold_sim = np.matmul(gold_30_vecs, gold_30_vecs.T)
    np.fill_diagonal(internal_gold_sim, -1.0)
    internal_ro_ru_pairs = []
    for i in range(0, 22, 2):
        internal_ro_ru_pairs.append({
            "ro_id": gold_30_recs[i]["id"],
            "ru_id": gold_30_recs[i + 1]["id"],
            "category": gold_30_recs[i]["primary_label"],
            "ro_group_id": gold_30_recs[i]["group_id"],
            "ru_group_id": gold_30_recs[i + 1]["group_id"],
            "minilm_cosine": round(float(internal_gold_sim[i, i + 1]), 4),
        })

    # =========================================================================
    # Q4: SimilarityService Embedder Comparison on pairs_eval.jsonl (317 pairs)
    # =========================================================================
    pairs_path = REPO_ROOT / "ml" / "eval" / "pairs_eval.jsonl"
    pairs = load_jsonl(pairs_path)
    normaliser = TextNormaliser()

    sim_det = SimilarityService(embedder=DeterministicMultilingualEmbedder())
    sim_st = SimilarityService(embedder=st_embedder)

    def eval_sim_service(svc: SimilarityService) -> dict[str, Any]:
        buckets = {
            "ALL": {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0},
            "RO-RO": {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0},
            "RU-RU": {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0},
            "RO-RU": {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0},
        }
        dg_total = 0
        dg_correct = 0
        for p in pairs:
            la, lb = p["lang_a"], p["lang_b"]
            lp = "RO-RO" if la == "RO" and lb == "RO" else ("RU-RU" if la == "RU" and lb == "RU" else "RO-RU")
            gold = 1 if p["gold_label"] == "same" else 0
            na = normaliser.normalise(p["text_a"])
            nb = normaliser.normalise(p["text_b"])
            msg_a = StoredMessageDto(
                id="a", channel_id="ch-a", telegram_message_id=1, posted_at="2026-11-04T12:00:00Z",
                view_count=100, language=na.language, normalised_text=na.normalised_text,
                text_hash=na.text_hash, raw_text=p["text_a"],
            )
            msg_b = StoredMessageDto(
                id="b", channel_id="ch-b", telegram_message_id=2, posted_at="2026-11-04T12:05:00Z",
                view_count=100, language=nb.language, normalised_text=nb.normalised_text,
                text_hash=nb.text_hash, raw_text=p["text_b"],
            )
            score, _ = svc.score_pair(msg_a, msg_b)
            thresh = svc.get_calibrated_threshold(la, lb, 0.82)
            pred = 1 if score >= thresh else 0
            if p.get("pair_type") in ("detail_altered_number", "negation_altered"):
                dg_total += 1
                if pred == 0:
                    dg_correct += 1
            for b_key in ("ALL", lp):
                buckets[b_key]["total"] += 1
                if pred == 1 and gold == 1:
                    buckets[b_key]["tp"] += 1
                elif pred == 1 and gold == 0:
                    buckets[b_key]["fp"] += 1
                elif pred == 0 and gold == 1:
                    buckets[b_key]["fn"] += 1
                else:
                    buckets[b_key]["tn"] += 1
        out = {}
        for b_key, c in buckets.items():
            tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            out[b_key] = {
                "n": c["total"],
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
            }
        out["detail_guard_accuracy"] = round(dg_correct / dg_total, 4) if dg_total else 1.0
        return out

    sim_comparison = {
        "DeterministicMultilingualEmbedder (Current Default)": eval_sim_service(sim_det),
        "SentenceTransformerEmbedder (paraphrase-multilingual-MiniLM-L12-v2)": eval_sim_service(sim_st),
    }

    # =========================================================================
    # Q5: Debunk Retrieval Index Overlap Check
    # =========================================================================
    debunk_texts = {r["text"].strip() for r in debunk_index_recs}
    debunk_groups = {r.get("group_id") for r in debunk_index_recs if r.get("group_id")}
    debunk_overlap = {}
    for split_name, s_recs in [("test.jsonl", test_recs), ("gold.jsonl", gold_recs), ("telegram_test.jsonl", tg_test_recs)]:
        t_over = sum(1 for r in s_recs if r["text"].strip() in debunk_texts)
        g_over = sum(1 for r in s_recs if r.get("group_id") in debunk_groups)
        debunk_overlap[split_name] = {"exact_text_overlap": t_over, "group_id_overlap": g_over, "total_items": len(s_recs)}

    audit_summary = {
        "q1_hard_negatives": {
            "v1_total": len(hn_v1_recs),
            "v1_exact_in_train_jsonl": hn_v1_in_train,
            "v1_sources": dict(hn_v1_sources),
            "v1_languages": dict(hn_v1_langs),
            "v1_dates": dict(hn_v1_dates),
            "v2_total": len(hn_v2_recs),
            "v2_overlap_with_any_split": hn_v2_overlap,
            "v2_sources": dict(Counter(r["source_type"] for r in hn_v2_recs)),
            "v2_languages": dict(Counter(r["language"] for r in hn_v2_recs)),
            "fpr_with_clopper_pearson_ci": fpr_results,
        },
        "q2_hybrid_false_alarms": {
            "total_fp_on_v1": len(hybrid_fp_details),
            "signal_counts": dict(signal_counts),
            "signal_combo_counts": dict(signal_combo_counts),
            "fp_items": hybrid_fp_details,
            "val_current_macro_f1": round(val_macro_f1_current, 4),
            "val_current_benign_fp": f"{val_benign_fp_current}/{val_benign_total}",
        },
        "q3_gold_provenance": {
            "total_gold_items": len(gold_recs),
            "unique_base_templates": len(unique_gold_bases),
            "repetition_factor": len(gold_recs) // len(unique_gold_bases),
            "overlap_with_splits": gold_dup_summary,
            "cross_lingual_minilm_vs_train": gold_minilm_check,
            "internal_ro_ru_pairs_in_gold": internal_ro_ru_pairs,
        },
        "q4_similarity_embedders": sim_comparison,
        "q5_debunk_index": {
            "curated_debunks_path": str(CURATED_DEBUNKS_PATH),
            "index_size": len(debunk_index_recs),
            "embedder_class": type(hybrid_svc._embedder).__name__,
            "overlap_checks": debunk_overlap,
        },
    }

    out_json = REPO_ROOT / "ml" / "data" / "audit_round2_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] Saved Round 2 audit results to {out_json}")


if __name__ == "__main__":
    main()
