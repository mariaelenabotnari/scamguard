"""Planted-campaign simulator for end-to-end evaluation of the coordination pipeline.

Injects synthetic coordinated campaigns (exact copy, light rewrite, cross-lingual translation,
variable inter-post delays) into a background stream of benign uncoordinated posts.
Outputs messages and ground-truth metadata to benchmark clustering and channel risk ranking.
"""

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

@dataclass(frozen=True)
class PlantedCampaign:
    campaign_id: str
    narrative: str
    channel_ids: list[str]
    message_ids: list[str]
    variation_types: list[str]
    lead_channel: str
    span_minutes: int

@dataclass
class SimulatedPost:
    id: str
    channel_id: str
    telegram_message_id: int
    posted_at: str
    raw_text: str
    campaign_id: str | None = None
    is_coordinated: bool = False

BENIGN_TOPICS = [
    "Prognoza meteo pentru săptămâna viitoare: ploi slabe în nordul Moldovei și temperaturi de până la 16 grade.",
    "Comisia parlamentară a examinat astăzi proiectul de lege privind digitalizarea serviciilor publice.",
    "În capitală se desfășoară turneul republican de șah între elevi din peste 20 de raioane.",
    "Primăria municipiului Chișinău a lansat lucrări de amenajare a parcului din sectorul Rîșcani.",
    "Минздрав Молдовы напоминает о начале сезонной вакцинации против гриппа в поликлиниках.",
    "В Национальном музее истории открылась экспозиция старинных карт и архивных документов.",
    "Футбольный клуб Шериф Тирасполь завершил контрольный матч со счетом 2:1 перед выездом в Кишинев.",
    "Национальный банк Молдовы опубликовал ежедневный курс основных мировых валют.",
]

CAMPAIGN_PAYLOADS = [
    {
        "narrative": "Sanctions, energy prices and economy fear",
        "variants": [
            ("RO", "Tarifele la gaz și energia electrică explodează în Moldova din 1 decembrie din cauza incompetenței guvernului."),
            ("RO", "Atenție: Facturile la gazele naturale și curent vor crește cu peste 40% din cauza refuzului de a negocia!"),
            ("RU", "Тарифы на газ и электричество резко взлетят в Молдове с 1 декабря из-за провальной политики властей."),
            ("RU", "Внимание: Платежки за газ и свет станут неподъемными уже в следующем месяце для большинства граждан."),
        ],
    },
    {
        "narrative": "Moldova government and elections delegitimisation",
        "variants": [
            ("RO", "Alegerile au fost fraudate masiv prin secțiile de votare din diaspora fără niciun control independent."),
            ("RO", "Sute de mii de voturi din străinătate au fost adăugate artificial la Chișinău pentru a falsifica scrutinul."),
            ("RU", "Выборы были массово сфальсифицированы на зарубежных участках без присутствия независимых наблюдателей."),
            ("RU", "Тысячи фиктивных голосов из диаспоры были вброшены для удержания власти правящей партией."),
        ],
    },
    {
        "narrative": "Anti-NATO / anti-West",
        "variants": [
            ("RO", "Militarii NATO aduc tehnică grea și armament la poligonul Bulboaca încălcând neutralitatea Moldovei."),
            ("RO", "Exercițiile comune cu trupele Alianței Nord-Atlantice transformă Moldova în teatru de război regional."),
            ("RU", "Военные НАТО завозят тяжелую бронетехнику на полигон Бульбоака в нарушение конституции Молдовы."),
            ("RU", "Учения с иностранными войсками фактически ликвидируют постоянный нейтралитет Республики Молдова."),
        ],
    },
    {
        "narrative": 'Anti-EU / "Europe is falling apart"',
        "variants": [
            ("RO", "Bruxelles cere lichidarea fermelor locale și preluarea terenurilor agricole din Moldova de corporații străine."),
            ("RO", "Integrarea europeană distruge micii producători moldoveni și duce la vânzarea pământului către străini."),
            ("RU", "Евросоюз требует ликвидации молдавских ферм и скупки сельскохозяйственных земель иностранцами."),
            ("RU", "Европейские директивы окончательно добьют аграрный сектор Молдовы в угоду транснациональным корпорациям."),
        ],
    },
    {
        "narrative": "Transnistria / Gagauzia and separatism",
        "variants": [
            ("RO", "Chișinăul pregătește blocada totală a regiunii găgăuze și anularea statutului de autonomie."),
            ("RO", "Guvernarea impune sancțiuni ilegale împotriva locuitorilor din Comrat și Tiraspol."),
            ("RU", "Кишинев планирует полную финансовую блокаду Гагаузии и фактическую отмену статуса автономии."),
            ("RU", "Власти готовят карательные экономические меры против жителей Комрата и Приднестровья."),
        ],
    },
]

def generate_simulation(
    num_background_posts: int = 150,
    num_campaigns: int = 5,
    seed: int = 42,
) -> tuple[list[SimulatedPost], list[PlantedCampaign]]:
    random.seed(seed)
    base_time = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    posts: list[SimulatedPost] = []
    campaigns: list[PlantedCampaign] = []

    # 1. Background normal traffic across 25 background channels
    for i in range(num_background_posts):
        ch_idx = (i % 25) + 1
        delta_m = random.randint(1, 600)
        post_time = (base_time + timedelta(minutes=delta_m)).isoformat()
        posts.append(
            SimulatedPost(
                id=f"msg-bg-{i:04d}",
                channel_id=f"channel_md_bg_{ch_idx:02d}",
                telegram_message_id=1000 + i,
                posted_at=post_time,
                raw_text=random.choice(BENIGN_TOPICS),
                campaign_id=None,
                is_coordinated=False,
            )
        )

    # 2. Planted Campaigns across dedicated coordinating channel groups
    for c_idx in range(num_campaigns):
        payload_data = CAMPAIGN_PAYLOADS[c_idx % len(CAMPAIGN_PAYLOADS)]
        narrative = payload_data["narrative"]
        variants = payload_data["variants"]
        c_channels = [f"channel_md_coord_{c_idx}_{j}" for j in range(len(variants))]
        lead_channel = c_channels[0]
        c_post_ids: list[str] = []
        c_start_offset = 60 + (c_idx * 75)
        c_start_time = base_time + timedelta(minutes=c_start_offset)

        # First post (origin in watchlist)
        first_post_id = f"msg-coord-{c_idx}-0"
        c_post_ids.append(first_post_id)
        posts.append(
            SimulatedPost(
                id=first_post_id,
                channel_id=lead_channel,
                telegram_message_id=2000 + (c_idx * 10),
                posted_at=c_start_time.isoformat(),
                raw_text=variants[0][1],
                campaign_id=f"camp-{c_idx:02d}",
                is_coordinated=True,
            )
        )

        # Subsequent copies with short coordinated delay (2 to 14 minutes)
        for j in range(1, len(variants)):
            delay_min = j * random.randint(2, 6)
            post_time = (c_start_time + timedelta(minutes=delay_min)).isoformat()
            pid = f"msg-coord-{c_idx}-{j}"
            c_post_ids.append(pid)
            posts.append(
                SimulatedPost(
                    id=pid,
                    channel_id=c_channels[j],
                    telegram_message_id=2000 + (c_idx * 10) + j,
                    posted_at=post_time,
                    raw_text=variants[j][1],
                    campaign_id=f"camp-{c_idx:02d}",
                    is_coordinated=True,
                )
            )

        campaigns.append(
            PlantedCampaign(
                campaign_id=f"camp-{c_idx:02d}",
                narrative=narrative,
                channel_ids=c_channels,
                message_ids=c_post_ids,
                variation_types=["exact" if j == 0 else "multilingual_rewrite" for j in range(len(variants))],
                lead_channel=lead_channel,
                span_minutes=len(variants) * 6,
            )
        )

    posts.sort(key=lambda p: p.posted_at)
    return posts, campaigns

def export_simulation(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    posts, campaigns = generate_simulation()
    with open(output_dir / "simulated_stream.jsonl", "w", encoding="utf-8") as f:
        for p in posts:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
    with open(output_dir / "simulated_campaigns.json", "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in campaigns], f, indent=2, ensure_ascii=False)
    print(f"Exported {len(posts)} simulated posts and {len(campaigns)} planted campaigns to {output_dir}")

if __name__ == "__main__":
    export_simulation(Path(__file__).resolve().parent)

