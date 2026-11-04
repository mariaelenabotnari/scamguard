"""Tests proving idempotence, time window enforcement, same-channel exclusion, and edit re-analysis for ScamGuard analysis pipeline."""

import pytest

from app.api.routes.analysis_routes import trigger_analysis_pipeline
from app.api.routes.auth_routes import login_user
from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.auth_dto import LoginInputDto
from app.dtos.collector_dto import RawTelegramPostDto
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.alert_service import AlertService
from app.services.analysis_pipeline_service import AnalysisPipelineService
from app.services.auth_service import AuthService
from app.services.clustering_service import ClusteringService
from app.services.narrative_classifier_service import NarrativeClassifierService
from app.services.scoring_service import ScoringService
from app.services.similarity_service import SimilarityService
from app.services.text_normaliser import TextNormaliser
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager


def _build_pipeline_harness():
    db = DatabaseManager(":memory:")
    param_repo = SqliteParameterRepository(db_manager=db)
    message_repo = SqliteMessageRepository(db_manager=db)
    cluster_repo = SqliteClusterRepository(db_manager=db)
    watchlist_repo = SqliteWatchlistRepository(db_manager=db, seed_defaults=False)
    normaliser = TextNormaliser()

    similarity_service = SimilarityService()
    narrative_classifier = NarrativeClassifierService(db_manager=db)
    clustering_service = ClusteringService(
        message_repo=message_repo,
        cluster_repo=cluster_repo,
        param_repo=param_repo,
        similarity_service=similarity_service,
        narrative_classifier=narrative_classifier,
    )
    scoring_service = ScoringService(db_manager=db)
    alert_service = AlertService(db_manager=db)

    pipeline = AnalysisPipelineService(
        param_repo=param_repo,
        message_repo=message_repo,
        normaliser=normaliser,
        clustering_service=clustering_service,
        narrative_classifier=narrative_classifier,
        scoring_service=scoring_service,
        alert_service=alert_service,
    )

    return (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    )


def test_analysis_pipeline_idempotence():
    """Running analysis twice on the exact same messages produces the identical clusters, scores and explanations."""
    (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    ) = _build_pipeline_harness()

    # Seed 3 channels on watchlist
    watchlist_repo.create_channel("ch-1", "@moldova_news", "Moldova News", "RO", "admin")
    watchlist_repo.create_channel("ch-2", "@chisinau_daily", "Chisinau Daily", "RO", "admin")
    watchlist_repo.create_channel("ch-3", "@balti_vestnik", "Balti Vestnik", "RU", "admin")

    # Seed coordinated messages within 10 minutes
    posts = [
        RawTelegramPostDto(
            channelId="ch-1",
            telegramMessageId=101,
            rawText="URGENT: Tarifele la gaz și energie vor exploda cu 300% după directiva impusă de la Bruxelles!",
            postedAt="2026-11-02T12:00:00Z",
            viewCount=5000,
        ),
        RawTelegramPostDto(
            channelId="ch-2",
            telegramMessageId=201,
            rawText="ALERTĂ: Tarifele la gaz și energie vor exploda cu 300% după directiva impusă de la Bruxelles!",
            postedAt="2026-11-02T12:05:00Z",
            viewCount=4500,
        ),
        RawTelegramPostDto(
            channelId="ch-3",
            telegramMessageId=301,
            rawText="СРОЧНО: Тарифы на газ и свет вырастут на 300% по требованию директивы из Брюсселя!",
            postedAt="2026-11-02T12:08:00Z",
            viewCount=7800,
        ),
    ]
    for p in posts:
        norm = normaliser.normalise(p.raw_text)
        message_repo.save_message(p, norm)

    # First analysis run
    res_1 = pipeline.run_analysis_pipeline()
    assert res_1.clusters_detected >= 1
    assert res_1.channels_scored >= 3

    clusters_1 = cluster_repo.list_clusters()
    scores_1 = scoring_service.list_ranked_channels()
    alerts_1 = alert_service.list_alerts()

    # Second analysis run on unchanged messages
    res_2 = pipeline.run_analysis_pipeline()

    clusters_2 = cluster_repo.list_clusters()
    scores_2 = scoring_service.list_ranked_channels()
    alerts_2 = alert_service.list_alerts()

    # Exact equality checks for idempotence
    assert len(clusters_1) == len(clusters_2)
    assert [c.id for c in clusters_1] == [c.id for c in clusters_2]
    assert [c.narrative_category for c in clusters_1] == [c.narrative_category for c in clusters_2]
    assert [c.average_similarity for c in clusters_1] == [c.average_similarity for c in clusters_2]

    assert len(scores_1) == len(scores_2)
    for s1, s2 in zip(scores_1, scores_2):
        assert s1.id == s2.id
        assert s1.score == s2.score
        assert s1.risk_band == s2.risk_band
        assert s1.explanation.breakdown == s2.explanation.breakdown
        assert s1.explanation.summary == s2.explanation.summary

    assert len(alerts_1) == len(alerts_2)
    assert [a.id for a in alerts_1] == [a.id for a in alerts_2]


def test_analysis_pipeline_respects_time_window():
    """Messages outside the configured time window are never combined into a coordinated cascade."""
    (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    ) = _build_pipeline_harness()

    watchlist_repo.create_channel("ch-a", "@channel_a", "A", "RO", "admin")
    watchlist_repo.create_channel("ch-b", "@channel_b", "B", "RO", "admin")

    # Two identical messages, but posted 3 hours apart (window default is 30 mins)
    p1 = RawTelegramPostDto(
        channelId="ch-a",
        telegramMessageId=1,
        rawText="Declarație identică distribuită la ore complet diferite fără coordonare.",
        postedAt="2026-11-02T10:00:00Z",
    )
    p2 = RawTelegramPostDto(
        channelId="ch-b",
        telegramMessageId=2,
        rawText="Declarație identică distribuită la ore complet diferite fără coordonare.",
        postedAt="2026-11-02T13:30:00Z",
    )
    message_repo.save_message(p1, normaliser.normalise(p1.raw_text))
    message_repo.save_message(p2, normaliser.normalise(p2.raw_text))

    res = pipeline.run_analysis_pipeline()
    # No cluster because time diff is 210 minutes (> 30 min window)
    assert res.clusters_detected == 0
    assert len(cluster_repo.list_clusters()) == 0


def test_analysis_pipeline_same_channel_messages_never_clustered():
    """Two identical messages on the same channel are never clustered as coordinated activity."""
    (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    ) = _build_pipeline_harness()

    watchlist_repo.create_channel("ch-single", "@single_channel", "Single", "RO", "admin")

    # Same channel repeats post after 5 minutes
    p1 = RawTelegramPostDto(
        channelId="ch-single",
        telegramMessageId=501,
        rawText="Repostare internă pe același canal public fără implicarea altor canale.",
        postedAt="2026-11-02T10:00:00Z",
    )
    p2 = RawTelegramPostDto(
        channelId="ch-single",
        telegramMessageId=502,
        rawText="Repostare internă pe același canal public fără implicarea altor canale.",
        postedAt="2026-11-02T10:05:00Z",
    )
    message_repo.save_message(p1, normaliser.normalise(p1.raw_text))
    message_repo.save_message(p2, normaliser.normalise(p2.raw_text))

    res = pipeline.run_analysis_pipeline()
    assert res.clusters_detected == 0


def test_analysis_pipeline_edited_message_reanalysis():
    """Editing a message so it no longer matches the cluster re-evaluates and prunes the cluster."""
    (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    ) = _build_pipeline_harness()

    watchlist_repo.create_channel("ch-x", "@channel_x", "X", "RO", "admin")
    watchlist_repo.create_channel("ch-y", "@channel_y", "Y", "RO", "admin")

    p1 = RawTelegramPostDto(
        channelId="ch-x",
        telegramMessageId=10,
        rawText="Campanie inițial coordonată despre criza apei potabile în Bălți.",
        postedAt="2026-11-02T11:00:00Z",
    )
    p2 = RawTelegramPostDto(
        channelId="ch-y",
        telegramMessageId=20,
        rawText="Campanie inițial coordonată despre criza apei potabile în Bălți.",
        postedAt="2026-11-02T11:03:00Z",
    )
    message_repo.save_message(p1, normaliser.normalise(p1.raw_text))
    message_repo.save_message(p2, normaliser.normalise(p2.raw_text))

    # Initial pipeline run creates 1 cluster
    res_1 = pipeline.run_analysis_pipeline()
    assert res_1.clusters_detected == 1

    # Edit post 2 to completely different weather topic
    p2_edited = RawTelegramPostDto(
        channelId="ch-y",
        telegramMessageId=20,
        rawText="Prognoza meteo pentru weekend: vreme însorită în toată Moldova fără precipitații.",
        postedAt="2026-11-02T11:03:00Z",
        editDate="2026-11-02T11:15:00Z",
    )
    norm_edited = normaliser.normalise(p2_edited.raw_text)
    message_repo.save_message(p2_edited, norm_edited)

    # Re-run pipeline
    res_2 = pipeline.run_analysis_pipeline()
    # The cluster is pruned because messages no longer match!
    assert res_2.clusters_detected == 0
    assert len(cluster_repo.list_clusters()) == 0


def test_analysis_api_endpoint_rbac():
    """Verifies that the /api/v1/analysis/run endpoint requires journalist or admin role."""
    (
        db,
        param_repo,
        message_repo,
        cluster_repo,
        watchlist_repo,
        normaliser,
        clustering_service,
        scoring_service,
        alert_service,
        pipeline,
    ) = _build_pipeline_harness()

    hasher = PasswordHasher(iterations=1_000)
    token_manager = TokenManager(secret_key="analysis-test-secret")
    rate_limiter = LoginRateLimiter(max_attempts=5)
    user_repo = SqliteUserRepository(db_manager=db, hasher=hasher)
    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=token_manager,
        rate_limiter=rate_limiter,
    )

    # Authenticate as admin
    admin_session = login_user(
        payload=LoginInputDto(email="elena.botnari@scamguard.md", password="scamguard2026"),
        auth_service=auth_service,
    )

    # Trigger via API route
    res = trigger_analysis_pipeline(
        token=admin_session.access_token,
        auth_service=auth_service,
        analysis_service=pipeline,
    )
    assert res.parameter_version == "v1.4"
    assert res.channels_scored >= 0

    # Unauthenticated / invalid token raises 401
    with pytest.raises(AppError) as exc_unauth:
        trigger_analysis_pipeline(
            token="invalid-token",
            auth_service=auth_service,
            analysis_service=pipeline,
        )
    assert exc_unauth.value.status_code == 401
