"""Tests for real dynamic timeline propagation, LCS diffs, timezone conversion, and clean unseeded database states."""

from pathlib import Path

import pytest

from app.db.database import DatabaseManager
from app.dtos.cluster_dto import (
    ClusterSummaryDto,
)
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.alert_service import AlertService
from app.services.clustering_service import ClusteringService
from app.services.dashboard_service import DashboardService
from app.services.scoring_service import ScoringService
from app.services.similarity_service import SimilarityService
from app.services.timeline_service import (
    build_dynamic_timeline,
    compute_lcs_word_diff,
    format_chisinau_datetime,
    format_chisinau_time,
    parse_utc_timestamp,
)


@pytest.fixture
def isolated_db(tmp_path: Path) -> DatabaseManager:
    db = DatabaseManager(str(tmp_path / "test_timeline.db"))
    db.run_migrations()
    return db


def test_utc_parsing_and_chisinau_timezone_conversion() -> None:
    # 2026-11-04 10:00:00 UTC is 12:00:00 in Europe/Chisinau (UTC+2 standard time in winter)
    utc_str = "2026-11-04T10:00:00Z"
    dt = parse_utc_timestamp(utc_str)
    assert dt.tzinfo is not None

    chisinau_str = format_chisinau_datetime(dt)
    assert chisinau_str == "2026-11-04 12:00:00"

    chisinau_time = format_chisinau_time(dt)
    assert chisinau_time == "12:00:00"


def test_lcs_word_level_diff_tokens() -> None:
    anchor = "Tarifele la gaze si energie electrica vor fi dublate dupa 15 noiembrie din cauza Bruxelles"
    copy_msg = "ALERTA: Tarifele la gaze si energie electrica vor fi majorate cu 100% dupa 15 noiembrie din cauza Bruxelles!"

    diff_tokens = compute_lcs_word_diff(anchor, copy_msg)
    assert len(diff_tokens) > 0

    # Words that were inserted/changed
    changed_texts = [t.text.strip() for t in diff_tokens if t.is_changed]
    assert any("ALERTA:" in txt for txt in changed_texts)
    assert any("majorate cu 100%" in txt for txt in changed_texts)

    # Common words that remained identical
    unchanged_texts = [t.text.strip() for t in diff_tokens if not t.is_changed]
    assert any("Tarifele la gaze si energie electrica vor fi" in txt for txt in unchanged_texts)

    # Reconstructed text should match copy_msg tokens
    reconstructed = "".join(t.text for t in diff_tokens).strip()
    assert reconstructed.replace("  ", " ") == copy_msg.replace("  ", " ")


def test_dynamic_propagation_timeline_builds_t0_anchor_and_delays() -> None:
    summary = ClusterSummaryDto(
        id="cl-test-real",
        headlineSummary="Same claim across 3 channels",
        narrativeCategory="Energy panic",
        narrativeConfidence=0.94,
        channelsCount=3,
        messagesCount=3,
        windowMinutes=10,
        spanMinutes=10,
        averageSimilarity=0.93,
        matchType="semantic",
        firstPostedAt="2026-11-04 10:00:00",
        lastPostedAt="2026-11-04 10:08:00",
        representativeSnippet="Tarifele la gaze vor creste",
        channels=[],
        participants=[],
        parameterVersion="v1.4",
    )

    records = [
        {
            "message_id": "msg-01",
            "channel_id": "ch-alpha",
            "handle": "@alpha_news",
            "title": "Alpha News",
            "posted_at": "2026-11-04T10:00:00Z",
            "similarity_score": 1.0,
            "raw_text": "Tarifele la gaze vor creste cu 100% de la 15 noiembrie.",
            "normalised_text": "tarifele la gaze vor creste cu 100% de la 15 noiembrie",
            "text_hash": "hash-alpha",
            "is_deleted_at_source": 0,
            "telegram_message_id": 101,
        },
        {
            "message_id": "msg-02",
            "channel_id": "ch-beta",
            "handle": "@beta_channel",
            "title": "Beta Channel",
            "posted_at": "2026-11-04T10:04:15Z",  # +255s after alpha
            "similarity_score": 0.94,
            "raw_text": "URGENT: Tarifele la gaze vor creste cu 100% de la 15 noiembrie conform UE.",
            "normalised_text": "urgent tarifele la gaze vor creste cu 100% de la 15 noiembrie conform ue",
            "text_hash": "hash-beta",
            "is_deleted_at_source": 0,
            "telegram_message_id": 202,
        },
        {
            "message_id": "msg-03",
            "channel_id": "ch-gamma",
            "handle": "@gamma_live",
            "title": "Gamma Live",
            "posted_at": "2026-11-04T10:08:30Z",  # +510s after alpha
            "similarity_score": 0.91,
            "raw_text": "Tarifele la gaze vor creste cu 100% de la 15 noiembrie conform directivei.",
            "normalised_text": "tarifele la gaze vor creste cu 100% de la 15 noiembrie conform directivei",
            "text_hash": "hash-gamma",
            "is_deleted_at_source": 1,
            "telegram_message_id": 303,
        },
    ]

    detail = build_dynamic_timeline(summary, records)

    assert detail.id == "cl-test-real"
    assert len(detail.posts) == 3
    assert len(detail.participants) == 3

    # Anchor checks
    anchor_post = detail.posts[0]
    assert anchor_post.id == "msg-01"
    assert anchor_post.channel_id == "ch-alpha"
    assert anchor_post.delay_seconds == 0
    assert anchor_post.similarity_to_anchor == 1.0
    assert not anchor_post.is_deleted_at_source

    # Copy post 1 checks
    copy_1 = detail.posts[1]
    assert copy_1.id == "msg-02"
    assert copy_1.delay_seconds == 255
    assert copy_1.similarity_to_anchor == 0.94
    assert any(t.is_changed and "URGENT:" in t.text for t in copy_1.diff_tokens)

    # Copy post 2 checks (deleted at source)
    copy_2 = detail.posts[2]
    assert copy_2.id == "msg-03"
    assert copy_2.delay_seconds == 510
    assert copy_2.is_deleted_at_source is True

    # Summary propagation
    assert detail.summary is not None
    assert detail.summary.channels_count == 3
    assert detail.summary.span_minutes in (8, 9)  # 510s ~ 8.5 min


def test_clean_unseeded_database_all_services_return_empty(
    isolated_db: DatabaseManager,
) -> None:
    """Verifies that with all mock seed data purged, unseeded database returns clean empty states."""
    watchlist_repo = SqliteWatchlistRepository(db_manager=isolated_db, seed_defaults=False)
    channels, count = watchlist_repo.list_paginated(page=1, page_size=20)
    assert channels == []
    assert count == 0

    message_repo = SqliteMessageRepository(db_manager=isolated_db)
    cluster_repo = SqliteClusterRepository(db_manager=isolated_db)
    param_repo = SqliteParameterRepository(db_manager=isolated_db)
    similarity_service = SimilarityService()
    clustering_service = ClusteringService(
        message_repo=message_repo,
        cluster_repo=cluster_repo,
        param_repo=param_repo,
        similarity_service=similarity_service,
    )
    clusters = clustering_service.list_clusters()
    assert clusters == []

    scoring_service = ScoringService(db_manager=isolated_db)
    ranked = scoring_service.list_ranked_channels()
    assert ranked == []

    groups = scoring_service.get_channel_coordination_groups()
    assert groups == []

    alert_service = AlertService(db_manager=isolated_db)
    alerts = alert_service.list_alerts()
    assert alerts == []

    dashboard_service = DashboardService(db_manager=isolated_db)
    overview = dashboard_service.get_overview("7d")
    assert overview.banner.active_channels_count == 0
    assert overview.timeline.points[0].messages_count == 0
    assert overview.timeline.points[0].flagged_clusters_count == 0
    assert overview.stats[0].numeric_value == 0.0
    assert overview.stats[1].numeric_value == 0.0
    assert overview.stats[2].numeric_value == 0.0
