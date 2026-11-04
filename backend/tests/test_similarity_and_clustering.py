from app.api.routes.auth_routes import login_user
from app.api.routes.cluster_routes import (
    get_cluster_comparison,
    list_detected_clusters,
    run_cluster_detection,
)
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.auth_dto import LoginInputDto
from app.dtos.cluster_dto import DetectClustersInputDto
from app.dtos.collector_dto import RawTelegramPostDto, StoredMessageDto
from app.main import create_app
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.auth_service import AuthService
from app.services.clustering_service import ClusteringService
from app.services.similarity_service import SimilarityService
from app.services.text_normaliser import TextNormaliser


def _make_stored_msg(
    msg_id: str, channel_id: str, raw_text: str, posted_at: str = "2026-11-02T10:00:00Z"
) -> StoredMessageDto:
    norm = TextNormaliser().normalise(raw_text)
    return StoredMessageDto(
        id=msg_id,
        channelId=channel_id,
        telegramMessageId=1,
        postedAt=posted_at,
        forwardedFrom=None,
        viewCount=1000,
        language=norm.language,
        isDeletedAtSource=False,
        rawText=raw_text,
        normalisedText=norm.normalised_text,
        textHash=norm.text_hash,
    )


# 52 hand-crafted pairs: (text_a, text_b, expected_match)
# Includes exact duplicates, rewritten near-duplicates, cross-language RO<->RU, and different topics
SIMILARITY_BENCHMARK_PAIRS: list[tuple[str, str, bool]] = [
    # 1-10: Exact duplicates with varying links, punctuation, and cedilla/comma diacritics
    (
        (
            "URGENT! Tarifele la gaze în Chișinău vor exploda cu 300% "
            "după directiva de la Bruxelles! https://t.me/a/1"
        ),
        (
            "urgent: tarifele la gaze în chişinău vor exploda cu 300% "
            "după directiva de la bruxelles..."
        ),
        True,
    ),
    (
        "Guvernul din Moldova pregătește închiderea secțiilor de votare pentru alegeri!",
        "GUVERNUL din Moldova pregăteşte închiderea secţiilor de votare pentru alegeri! t.me/b/2",
        True,
    ),
    (
        "НАТО готовит военные учения у границ Молдовы и Приднестровья!",
        "нато готовит военные учения у границ молдовы и приднестровья https://t.me/c/3",
        True,
    ),
    (
        "Fermierii din Moldova cer subvenții pentru motorină și blochează traseul!",
        "Fermierii din Moldova cer subvenţii pentru motorină şi blochează traseul...",
        True,
    ),
    (
        "Banca Națională din Chișinău avertizează asupra inflației și creditelor!",
        "Banca Naţională din Chişinău avertizează asupra inflaţiei şi creditelor!",
        True,
    ),
    (
        "В Кишинёве и Бельцах вырастут тарифы на свет и газ в два раза!",
        "В Кишиневе и Бельцах вырастут тарифы на свет и газ в два раза!",
        True,
    ),
    (
        "Spitalul din Chișinău impune noi protocoale de vaccinare de la OMS!",
        "Spitalul din Chişinău impune noi protocoale de vaccinare de la OMS! 🔥",
        True,
    ),
    (
        "Găgăuzia și Transnistria contestă taxele vamale impuse de Chișinău.",
        "Găgăuzia şi Transnistria contestă taxele vamale impuse de Chişinău!",
        True,
    ),
    (
        "Școlile cu predare în limba rusă din Moldova sunt amenințate cu închiderea!",
        "Şcolile cu predare în limba rusă din Moldova sunt ameninţate cu închiderea!",
        True,
    ),
    (
        "Санкции Евросоюза разрушают экономику и ведут к росту цен на газ!",
        "санкции евросоюза разрушают экономику и ведут к росту цен на газ",
        True,
    ),
    # 11-20: Rewritten / paraphrased near-duplicates in the same language
    (
        "Tarifele la energie și gaze în Chișinău cresc cu 300 după directiva Bruxelles",
        (
            "Prețurile la gaze și energie în Moldova vor exploda cu 300 "
            "conform directivei de la Bruxelles"
        ),
        True,
    ),
    (
        "Exerciții militare NATO la granița Moldovei pregătite de armată",
        "Armata și NATO pregătesc exerciții militare în apropierea Moldovei",
        True,
    ),
    (
        "Alegerile din Moldova sunt marcate de fraudă la secțiile de votare din Chișinău",
        "Secțiile de votare pentru alegeri din Chișinău și Moldova acuzate de fraudă la vot",
        True,
    ),
    (
        "Тарифы на газ и электроэнергию в Кишинёве и Молдове взлетят на 300 по требованию ЕС",
        "Цены на свет и газ в Молдове и Кишинёве вырастут на 300 из-за директивы Евросоюза",
        True,
    ),
    (
        "Приднестровье и Гагаузия в Тирасполе и Комрате обсуждают автономию",
        "В Комрате и Тирасполе Гагаузия и Приднестровье заявили о правах региона",
        True,
    ),
    (
        "Fermierii și agricultorii din Moldova cer subvenții pentru motorină",
        "Agricultorii și fermierii cer subvenții la motorină în toată Moldova",
        True,
    ),
    (
        "Banca Națională anunță creșterea inflației și scumpirea creditelor în Chișinău",
        "Inflația și creditele mai scumpe anunțate de Banca Națională din Chișinău",
        True,
    ),
    (
        "Spitalul și medicii avertizează despre vaccin și sănătate conform OMS",
        "OMS și spitalul introduc reguli noi de sănătate și vaccin",
        True,
    ),
    (
        "Școli în limba rusă și tradiții discutate la Chișinău",
        "Limba rusă în școli și păstrarea tradițiilor în dezbatere la Chișinău",
        True,
    ),
    (
        "Cod galben de vânt și ploi anunțat de meteo în Moldova",
        "Avertizare meteo de ploi și vânt cu cod galben în Moldova",
        True,
    ),
    # 21-26: Cross-language Romanian <-> Russian coordinated equivalents
    (
        "Tarifele la gaze și energie în Chișinău Moldova cresc cu 300 după directiva Bruxelles UE",
        (
            "Тарифы на газ и электроэнергию в Кишиневе Молдове вырастут на 300 "
            "по директиве Брюсселя ЕС"
        ),
        True,
    ),
    (
        "NATO pregătește exerciții militare și război",
        "НАТО готовит военные учения и войну",
        True,
    ),
    (
        "Alegeri și secțiile de votare în Moldova",
        "Выборы и участки голосования в Молдове",
        True,
    ),
    (
        "Găgăuzia și Transnistria la Tiraspol și Comrat",
        "Гагаузия и Приднестровье в Тирасполе и Комрате",
        True,
    ),
    (
        "Banca Națională despre inflație și credite",
        "Банк о росте инфляции и кредитах",
        True,
    ),
    (
        "Spital și vaccin OMS pentru sănătate",
        "Больница и вакцина ВОЗ для здравоохранения",
        True,
    ),
    # 27-52: Unrelated / different news items (must NOT match at 0.85 threshold)
    (
        "Tarifele la gaze în Chișinău cresc cu 300% după directiva de la Bruxelles",
        "Meci de fotbal pe stadionul din Chișinău în campionatul național de sport",
        False,
    ),
    (
        "Tarifele la gaze în Chișinău cresc cu 300% după directiva de la Bruxelles",
        "Festival de cultură, teatru și concert simfonic la muzeul național",
        False,
    ),
    (
        "NATO pregătește exerciții militare la graniță",
        "Fermierii cer subvenții pentru motorină în agricultură",
        False,
    ),
    (
        "NATO pregătește exerciții militare la graniță",
        "Avertizare meteo cod galben de ploi și vânt puternic",
        False,
    ),
    (
        "Alegerile și secțiile de votare din diaspora",
        "Spitalul republican modernizează secția de chirurgie și vaccin",
        False,
    ),
    (
        "Alegerile și secțiile de votare din diaspora",
        "Banca Națională menține rata dobânzii la credite",
        False,
    ),
    (
        "Găgăuzia și Transnistria în negocieri la Tiraspol",
        "Meci de fotbal și campionat de sport pentru tineret",
        False,
    ),
    (
        "Găgăuzia și Transnistria în negocieri la Tiraspol",
        "Concert și festival de teatru și cultură în weekend",
        False,
    ),
    (
        "Banca Națională anunță rata inflației la credite",
        "Cod galben meteo de ploi și vânt la munte",
        False,
    ),
    (
        "Banca Națională anunță rata inflației la credite",
        "Școlile în limba rusă organizează serbarea de tradiții",
        False,
    ),
    (
        "Spitalul și OMS despre vaccin și sănătate",
        "Fermierii și agricultorii primesc subvenții la motorină",
        False,
    ),
    (
        "Spitalul și OMS despre vaccin și sănătate",
        "Festival de cultură și concert la teatru",
        False,
    ),
    (
        "Fermierii cer subvenții pentru motorină",
        "Meci de fotbal pe stadion în campionatul de sport",
        False,
    ),
    (
        "Fermierii cer subvenții pentru motorină",
        "NATO și armata în exerciții militare",
        False,
    ),
    (
        "Școli în limba rusă și tradiții culturale",
        "Tarifele la gaze și energie electrică cresc cu 300",
        False,
    ),
    (
        "Școli în limba rusă și tradiții culturale",
        "Cod galben meteo de vânt și ploi",
        False,
    ),
    (
        "Cod galben meteo de vânt și ploi",
        "Festival de teatru, muzeu și concert de cultură",
        False,
    ),
    (
        "Cod galben meteo de vânt și ploi",
        "Banca Națională și creditele afectate de inflație",
        False,
    ),
    (
        "Meci de fotbal pe stadion în campionatul de sport",
        "Festival de teatru, concert și muzeu de cultură",
        False,
    ),
    (
        "Meci de fotbal pe stadion în campionatul de sport",
        "Alegeri și secțiile de votare pentru președinte",
        False,
    ),
    (
        "Тарифы на газ и свет вырастут на 300 по директиве ЕС",
        "Футбольный матч на стадионе и чемпионат по спорту",
        False,
    ),
    (
        "Тарифы на газ и свет вырастут на 300 по директиве ЕС",
        "Фестиваль культуры, концерт и театр в выходные",
        False,
    ),
    (
        "НАТО готовит военные учения",
        "Прогноз погоды: сильный ветер и дождь",
        False,
    ),
    (
        "НАТО готовит военные учения",
        "Больница и вакцина ВОЗ для здравоохранения",
        False,
    ),
    (
        "Выборы и участки голосования",
        "Аграрии и фермеры требуют субсидии на трассе",
        False,
    ),
    (
        "Гагаузия и Приднестровье в Тирасполе и Комрате",
        "Банк сообщает о снижении инфляции по кредитам",
        False,
    ),
]


def test_similarity_benchmark_52_pairs_achieves_precision_above_90_percent() -> None:
    assert len(SIMILARITY_BENCHMARK_PAIRS) == 52
    similarity_service = SimilarityService()
    threshold = 0.85

    true_positives = 0
    false_positives = 0

    for idx, (text_a, text_b, expected_match) in enumerate(SIMILARITY_BENCHMARK_PAIRS):
        msg_a = _make_stored_msg(f"m-a-{idx}", "ch-a", text_a)
        msg_b = _make_stored_msg(f"m-b-{idx}", "ch-b", text_b)
        score, _ = similarity_service.score_pair(msg_a, msg_b)
        predicted_match = score >= threshold

        if predicted_match and expected_match:
            true_positives += 1
        elif predicted_match and not expected_match:
            false_positives += 1

    precision = true_positives / max(1, true_positives + false_positives)
    assert precision >= 0.90
    assert true_positives >= 22


def test_same_channel_messages_are_never_compared_and_clustering_is_reproducible() -> None:
    db_manager = DatabaseManager(":memory:")
    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="cluster-test-secret")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db_manager, hasher=hasher)
    param_repo = SqliteParameterRepository(db_manager=db_manager)
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager, seed_defaults=False)
    for c_id, h, t, l in [
        ("ch-01", "@moldova_azi_info", "Moldova Azi Info", "RO"),
        ("ch-02", "@chisinau_express", "Chișinău Express", "RO"),
        ("ch-03", "@pridnestrovie_pulse", "Приднестровье Пульс", "RU"),
    ]:
        watchlist_repo.create_channel(
            channel_id=c_id,
            handle=h,
            title=t,
            language=l,
            added_by="admin",
        )
    message_repo = SqliteMessageRepository(db_manager=db_manager)
    cluster_repo = SqliteClusterRepository(db_manager=db_manager)
    normaliser = TextNormaliser()

    # Save 2 identical messages on the SAME channel (ch-01) -> must NOT form a cluster alone
    for tg_id in (10, 11):
        post = RawTelegramPostDto(
            channelId="ch-01",
            telegramMessageId=tg_id,
            rawText="Postare internă repetată doar pe același canal.",
            postedAt="2026-11-02T09:00:00Z",
        )
        message_repo.save_message(post, normaliser.normalise(post.raw_text))

    # Save a coordinated 3-channel energy narrative cluster (ch-01, ch-02, ch-03 within 4 minutes)
    coordinated_posts = [
        RawTelegramPostDto(
            channelId="ch-01",
            telegramMessageId=101,
            rawText=(
                "URGENT! Tarifele la gaze și energie în Chișinău Moldova cresc cu 300% "
                "după directiva de la Bruxelles UE! https://t.me/moldova_azi_info/101"
            ),
            postedAt="2026-11-02T10:00:00Z",
        ),
        RawTelegramPostDto(
            channelId="ch-02",
            telegramMessageId=201,
            rawText=(
                "URGENT: Tarifele la gaze şi energie în Chişinău Moldova cresc cu 300% "
                "după directiva de la Bruxelles UE! Exclusiv pe canal."
            ),
            postedAt="2026-11-02T10:02:00Z",
        ),
        RawTelegramPostDto(
            channelId="ch-03",
            telegramMessageId=301,
            rawText=(
                "Тарифы на газ и электроэнергию в Кишиневе Молдове вырастут на 300% "
                "по директиве Брюсселя ЕС!"
            ),
            postedAt="2026-11-02T10:04:00Z",
        ),
    ]
    for post in coordinated_posts:
        message_repo.save_message(post, normaliser.normalise(post.raw_text))

    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )
    clustering_service = ClusteringService(
        message_repo=message_repo,
        cluster_repo=cluster_repo,
        param_repo=param_repo,
        similarity_service=SimilarityService(),
    )

    admin_session = login_user(
        payload=LoginInputDto(email="elena.botnari@scamguard.md", password="scamguard2026"),
        auth_service=auth_service,
    )
    token = admin_session.access_token

    # Run 1
    run_1 = run_cluster_detection(
        payload=DetectClustersInputDto(similarityThreshold=0.85, timeWindowMinutes=60),
        token=token,
        auth_service=auth_service,
        clustering_service=clustering_service,
    )
    # Run 2 on the exact same data must produce the exact same cluster IDs and structure
    run_2 = run_cluster_detection(
        payload=DetectClustersInputDto(similarityThreshold=0.85, timeWindowMinutes=60),
        token=token,
        auth_service=auth_service,
        clustering_service=clustering_service,
    )

    assert len(run_1) == 1
    assert len(run_2) == 1
    assert run_1[0].id == run_2[0].id
    assert run_1[0].channels_count == 3
    assert run_1[0].messages_count == 3
    assert run_1[0].window_minutes == 4
    assert "3 channels in 4 minutes" in run_1[0].headline_summary

    summaries = list_detected_clusters(clustering_service=clustering_service)
    assert len(summaries) == 1

    detail = get_cluster_comparison(cluster_id=run_1[0].id, clustering_service=clustering_service)
    assert len(detail.messages) == 3
    assert any("exclusiv" in m.changed_phrases for m in detail.messages)
    assert watchlist_repo.get_by_id("ch-01") is not None

    openapi_paths = create_app().openapi()["paths"]
    assert "/api/v1/clusters" in openapi_paths
    assert "/api/v1/clusters/{cluster_id}" in openapi_paths
    assert "/api/v1/clusters/detect" in openapi_paths
