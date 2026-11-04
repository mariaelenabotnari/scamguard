import pytest

from app.api.routes.auth_routes import login_user
from app.api.routes.collector_routes import (
    get_collected_messages,
    get_collection_runs,
    purge_source_deleted_post,
    trigger_collection_run,
)
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.auth_dto import LoginInputDto
from app.dtos.collector_dto import (
    DetectedLanguage,
    PurgeDeletedPostInputDto,
    RawTelegramPostDto,
)
from app.main import create_app
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteUserRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.auth_service import AuthService
from app.services.collector_service import (
    TelegramCollectorService,
)
from app.services.telegram_client import FakeTelegramClientAdapter
from app.services.text_normaliser import TextNormaliser

NORMALISATION_EXAMPLES: list[tuple[str, str, DetectedLanguage]] = [
    (
        "URGENT! Preţurile la gaze în Chişinău cresc cu 50%! https://t.me/moldova_azi/10",
        "urgent prețurile la gaze în chișinău cresc cu 50",
        "RO",
    ),
    (
        "Prețurile la gaze în Chișinău cresc cu 50%...",
        "prețurile la gaze în chișinău cresc cu 50",
        "RO",
    ),
    (
        "Guvernul de la Chișinău pregătește noi taxe pentru cetățeni! 🔥🔥🔥",
        "guvernul de la chișinău pregătește noi taxe pentru cetățeni",
        "RO",
    ),
    (
        "România și Moldova semnează acordul energetic la București.",
        "românia și moldova semnează acordul energetic la bucurești",
        "RO",
    ),
    (
        "Alegeri în Moldova: secțiile de votare din Bălți și Orhei.",
        "alegeri în moldova secțiile de votare din bălți și orhei",
        "RO",
    ),
    (
        "Știri de ultimă oră din Cahul și Ungheni! www.stiri.md/cahul",
        "știri de ultimă oră din cahul și ungheni",
        "RO",
    ),
    (
        "Banca Națională a Moldovei anunță rata inflației pentru trimestrul IV.",
        "banca națională a moldovei anunță rata inflației pentru trimestrul iv",
        "RO",
    ),
    (
        "Protest în Piața Marii Adunări Naționale din Chișinău!",
        "protest în piața marii adunări naționale din chișinău",
        "RO",
    ),
    (
        "Fermierii din sudul Moldovei cer subvenții pentru motorină și semințe.",
        "fermierii din sudul moldovei cer subvenții pentru motorină și semințe",
        "RO",
    ),
    (
        "Tarifele la energie electrică în Moldova sunt analizate de ANRE.",
        "tarifele la energie electrică în moldova sunt analizate de anre",
        "RO",
    ),
    (
        "Cetăţenii din diaspora votează la secţiile din Uniunea Europeană.",
        "cetățenii din diaspora votează la secțiile din uniunea europeană",
        "RO",
    ),
    (
        "Spitalul Republican din Chișinău dezminte zvonurile false! t.me/sanatate_md/99",
        "spitalul republican din chișinău dezminte zvonurile false",
        "RO",
    ),
    (
        "Rețeaua de transport din Chișinău și suburbiile Durlești, Codru.",
        "rețeaua de transport din chișinău și suburbiile durlești codru",
        "RO",
    ),
    (
        "Avertizare meteo în toată Moldova: vânt puternic și ploi.",
        "avertizare meteo în toată moldova vânt puternic și ploi",
        "RO",
    ),
    (
        "Ministerul Educației din Moldova lansează programul pentru școli.",
        "ministerul educației din moldova lansează programul pentru școli",
        "RO",
    ),
    (
        "Exporturile de fructe din Moldova pe piața europeană au crescut.",
        "exporturile de fructe din moldova pe piața europeană au crescut",
        "RO",
    ),
    (
        "СРОЧНО! Тарифы на газ в Молдове вырастут в два раза! https://t.me/news_md/55",
        "срочно тарифы на газ в молдове вырастут в два раза",
        "RU",
    ),
    (
        "В Кишинёве пройдёт митинг против роста цен на электроэнергию!",
        "в кишиневе пройдет митинг против роста цен на электроэнергию",
        "RU",
    ),
    (
        "Приднестровье и Гагаузия требуют пересмотра пошлин на импорт.",
        "приднестровье и гагаузия требуют пересмотра пошлин на импорт",
        "RU",
    ),
    (
        "Санкции ЕС разрушают экономику Европы и бьют по фермерам!",
        "санкции ес разрушают экономику европы и бьют по фермерам",
        "RU",
    ),
    (
        "Молдавские аграрии перекрыли трассу у Кагула и Комрата.",
        "молдавские аграрии перекрыли трассу у кагула и комрата",
        "RU",
    ),
    (
        "НАТО готовит новые учения у границ Молдовы — источник t.me/inside_ru/12",
        "нато готовит новые учения у границ молдовы источник",
        "RU",
    ),
    (
        "Цены на отопление в Бельцах и Кишинёве побили рекорд.",
        "цены на отопление в бельцах и кишиневе побили рекорд",
        "RU",
    ),
    (
        "Выборы в Молдове: оппозиция заявляет о нарушениях на участках.",
        "выборы в молдове оппозиция заявляет о нарушениях на участках",
        "RU",
    ),
    (
        "В Тирасполе обсудили поставки газа и работу МГРЭС.",
        "в тирасполе обсудили поставки газа и работу мгрэс",
        "RU",
    ),
    (
        "Русский язык и традиционные ценности под угрозой закрытия школ!",
        "русский язык и традиционные ценности под угрозой закрытия школ",
        "RU",
    ),
    (
        "Евросоюз требует от Кишинёва ввести новые налоги с января.",
        "евросоюз требует от кишинева ввести новые налоги с января",
        "RU",
    ),
    (
        "Экстренное заявление депутатов Народного собрания Гагаузии!",
        "экстренное заявление депутатов народного собрания гагаузии",
        "RU",
    ),
    (
        "Экономический кризис в Европе: заводы закрываются из-за цен на газ.",
        "экономический кризис в европе заводы закрываются из за цен на газ",
        "RU",
    ),
    (
        "Всемирная организация здравоохранения и новые протоколы вакцинации.",
        "всемирная организация здравоохранения и новые протоколы вакцинации",
        "RU",
    ),
    (
        "Breaking news update from international wire 2026!",
        "breaking news update from international wire 2026",
        "OTHER",
    ),
    (
        "https://t.me/only_link_post/12345 !!! ...",
        "",
        "OTHER",
    ),
]


@pytest.mark.parametrize(("raw_text", "expected_norm", "expected_lang"), NORMALISATION_EXAMPLES)
def test_32_romanian_and_russian_normalisation_examples(
    raw_text: str, expected_norm: str, expected_lang: DetectedLanguage
) -> None:
    normaliser = TextNormaliser()
    result = normaliser.normalise(raw_text)
    assert result.normalised_text == expected_norm
    assert result.language == expected_lang
    assert len(result.text_hash) == 64


def test_cedilla_and_comma_romanian_diacritics_produce_identical_hash() -> None:
    normaliser = TextNormaliser()
    legacy_cedilla = normaliser.normalise("Preţurile în Chişinău cresc! https://t.me/ch1/10")
    modern_comma = normaliser.normalise("  PREȚURILE în CHIȘINĂU cresc... ")
    assert legacy_cedilla.normalised_text == modern_comma.normalised_text
    assert legacy_cedilla.text_hash == modern_comma.text_hash
    assert normaliser.normalise("Кишинёв").transliterated_text == "kishinev"


def test_collector_runs_on_5_public_channels_handles_floodwait_and_prevents_duplicates() -> None:
    db_manager = DatabaseManager(":memory:")
    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="collector-test-secret")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=hasher)
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager, seed_defaults=False)
    message_repo = SqliteMessageRepository(db_manager=db_manager)

    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )

    # Seed 5 active public channels
    channel_posts: dict[str, list[RawTelegramPostDto]] = {}
    for idx in range(1, 6):
        ch_id = f"ch-pub-{idx:02d}"
        watchlist_repo.create_channel(
            channel_id=ch_id,
            handle=f"@moldova_pub_{idx:02d}",
            title=f"Moldova Public {idx:02d}",
            language="RO" if idx <= 3 else "RU",
            added_by="elena.botnari@scamguard.md",
        )
        channel_posts[ch_id] = [
            RawTelegramPostDto(
                channelId=ch_id,
                telegramMessageId=100 + idx,
                rawText=f"Postare coordonată în Chișinău pe canalul {idx}!",
                postedAt="2026-11-02T11:00:00Z",
                viewCount=1500,
            ),
            RawTelegramPostDto(
                channelId=ch_id,
                telegramMessageId=200 + idx,
                rawText=f"A doua postare în Moldova pe canalul {idx}.",
                postedAt="2026-11-02T11:05:00Z",
                viewCount=1800,
            ),
        ]

    slept_durations: list[float] = []
    fake_client = FakeTelegramClientAdapter(
        channel_posts=channel_posts,
        flood_wait_once_channels={"ch-pub-02": 12},
    )
    collector_service = TelegramCollectorService(
        watchlist_repo=watchlist_repo,
        message_repo=message_repo,
        normaliser=TextNormaliser(),
        telegram_client=fake_client,
        sleep_fn=lambda sec: slept_durations.append(sec),
    )

    admin_session = login_user(
        payload=LoginInputDto(email="elena.botnari@scamguard.md", password="scamguard2026"),
        auth_service=auth_service,
    )
    token = admin_session.access_token

    # First collection run across 5 channels: 10 messages saved, 1 FloodWait handled
    run_1 = trigger_collection_run(
        token=token,
        auth_service=auth_service,
        collector_service=collector_service,
    )
    assert run_1.status == "completed"
    assert run_1.channels_polled == 5
    assert run_1.messages_saved == 10
    assert run_1.flood_waits_count == 1
    assert slept_durations == [12.0]

    # Second collection run on same data saves 0 duplicates because checkpoints advanced
    run_2 = trigger_collection_run(
        token=token,
        auth_service=auth_service,
        collector_service=collector_service,
    )
    assert run_2.messages_saved == 0

    stored_messages = get_collected_messages(collector_service=collector_service)
    assert len(stored_messages) == 10
    assert len(get_collection_runs(collector_service=collector_service)) == 2

    # Purge source-deleted post raw text while keeping normalised text and hash
    target_msg = stored_messages[0]
    receipt = purge_source_deleted_post(
        payload=PurgeDeletedPostInputDto(messageId=target_msg.id),
        token=token,
        auth_service=auth_service,
        collector_service=collector_service,
    )
    assert receipt.raw_text_purged is True
    assert receipt.retained_text_hash == target_msg.text_hash

    reloaded = message_repo.get_message_by_id(target_msg.id)
    assert reloaded is not None
    assert reloaded.is_deleted_at_source is True
    assert reloaded.raw_text is None
    assert reloaded.normalised_text == target_msg.normalised_text
    assert reloaded.text_hash == target_msg.text_hash

    openapi_paths = create_app().openapi()["paths"]
    assert "/api/v1/collector/run" in openapi_paths
    assert "/api/v1/collector/messages" in openapi_paths
    assert "/api/v1/collector/purge-deleted" in openapi_paths
