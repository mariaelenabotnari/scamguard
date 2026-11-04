"""Unit and route tests for channel coordination risk scoring, explanations, and alerts."""

from pathlib import Path

import pytest

from app.api.routes.scoring_routes import (
    dismiss_alert,
    get_channel_detail,
    list_alerts,
    list_ranked_channels,
)
from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.services.alert_service import AlertService
from app.services.scoring_service import ScoringService


@pytest.fixture()
def isolated_db(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_scoring.db"
    db = DatabaseManager(sqlite_path=str(db_file))
    db.run_migrations()
    return db


def test_compute_channel_score_is_deterministic_and_always_has_explanation(
    isolated_db: DatabaseManager,
) -> None:
    service = ScoringService(db_manager=isolated_db)

    first = service.compute_channel_score(
        channel_id="ch-test-01",
        cluster_participation_share=90,
        copy_delay_factor=85,
        co_movement_repetition=80,
        narrative_weight=88,
        linked_clusters_count=11,
        co_moving_channels=["@peer_alpha", "@peer_beta"],
        median_lead_lag_seconds=95,
        primary_narrative="Economic Collapse & Banking Panic",
    )
    second = service.compute_channel_score(
        channel_id="ch-test-01",
        cluster_participation_share=90,
        copy_delay_factor=85,
        co_movement_repetition=80,
        narrative_weight=88,
        linked_clusters_count=11,
        co_moving_channels=["@peer_alpha", "@peer_beta"],
        median_lead_lag_seconds=95,
        primary_narrative="Economic Collapse & Banking Panic",
    )

    assert first == second
    score, risk_band, explanation = first
    assert 0 <= score <= 100
    assert score == 86
    assert risk_band == "high"
    assert explanation.parameter_version == "v2.0.0-scoring"
    assert explanation.linked_clusters_count == 11
    assert explanation.co_moving_channels == ["@peer_alpha", "@peer_beta"]
    assert explanation.median_lead_lag_seconds == 95
    assert explanation.primary_narrative == "Economic Collapse & Banking Panic"
    assert (
        explanation.breakdown.dominant_factor
        == "frequent co-publication across coordinated clusters"
    )
    assert "86/100" in explanation.summary


def test_risk_band_thresholds_and_clamping(isolated_db: DatabaseManager) -> None:
    service = ScoringService(db_manager=isolated_db)

    low_score, low_band, _ = service.compute_channel_score(
        channel_id="ch-low",
        cluster_participation_share=20,
        copy_delay_factor=15,
        co_movement_repetition=10,
        narrative_weight=20,
        linked_clusters_count=1,
        co_moving_channels=[],
        median_lead_lag_seconds=500,
        primary_narrative="Healthcare & Public Safety Hoaxes",
    )
    assert low_score < 40
    assert low_band == "low"

    med_score, med_band, _ = service.compute_channel_score(
        channel_id="ch-med",
        cluster_participation_share=55,
        copy_delay_factor=50,
        co_movement_repetition=45,
        narrative_weight=50,
        linked_clusters_count=4,
        co_moving_channels=["@peer_one"],
        median_lead_lag_seconds=220,
        primary_narrative="EU Integration & Sovereignty Myths",
    )
    assert 40 <= med_score < 70
    assert med_band == "medium"


def test_evaluate_cluster_alert_severity_tiers(isolated_db: DatabaseManager) -> None:
    alert_service = AlertService(db_manager=isolated_db)

    high_alert = alert_service.evaluate_cluster_alert(
        cluster_id="CL-HIGH-01",
        channel_count=5,
        time_span_seconds=120,
        avg_similarity=0.92,
        narrative_tag="Economic Collapse & Banking Panic",
    )
    assert high_alert is not None
    assert high_alert.severity == "high"
    assert high_alert.target_route == "/clusters/CL-HIGH-01"

    med_alert = alert_service.evaluate_cluster_alert(
        cluster_id="CL-MED-01",
        channel_count=3,
        time_span_seconds=420,
        avg_similarity=0.85,
        narrative_tag="Energy Grid & Gas Sabotage Rumors",
    )
    assert med_alert is not None
    assert med_alert.severity == "medium"

    ignored_alert = alert_service.evaluate_cluster_alert(
        cluster_id="CL-SINGLE-01",
        channel_count=1,
        time_span_seconds=60,
        avg_similarity=0.95,
        narrative_tag="Foreign Military Intervention Alarms",
    )
    assert ignored_alert is None


def test_ranking_channel_detail_and_alerts_routes(isolated_db: DatabaseManager) -> None:
    scoring_service = ScoringService(db_manager=isolated_db)
    alert_service = AlertService(db_manager=isolated_db)

    # Clean unseeded database verification
    initial_items = list_ranked_channels(scoring_service=scoring_service, min_score=0, narrative=None)
    assert initial_items == []
    initial_alerts = list_alerts(alert_service=alert_service, severity=None, status=None)
    assert initial_alerts == []

    # Populate test channels and cluster coordination
    conn = isolated_db.connection
    conn.execute(
        """
        INSERT INTO watchlist_channels (id, handle, title, language, subscribers_count, status, added_at, added_by)
        VALUES ('ch-test-1', '@test1', 'Test Channel 1', 'RO', 10000, 'active', '2026-11-01', 'admin'),
               ('ch-test-2', '@test2', 'Test Channel 2', 'RO', 20000, 'active', '2026-11-01', 'admin'),
               ('ch-test-3', '@test3', 'Test Channel 3', 'RU', 15000, 'active', '2026-11-01', 'admin'),
               ('ch-test-4', '@test4', 'Test Channel 4', 'RO', 5000, 'active', '2026-11-01', 'admin')
        """
    )
    conn.execute(
        """
        INSERT INTO clusters (id, headline_summary, narrative_category, channels_count, messages_count,
                              window_minutes, average_similarity, first_posted_at, last_posted_at,
                              representative_snippet, parameter_version)
        VALUES ('cl-test-1', 'Test Energy Disinfo', 'Energy crisis and tariffs', 3, 3, 4, 0.94,
                '2026-11-02 10:00:00', '2026-11-02 10:04:00', 'Tarifele la gaze cresc', 'v1.4'),
               ('cl-test-2', 'Second Cascade', 'Energy crisis and tariffs', 2, 2, 3, 0.92,
                '2026-11-02 11:00:00', '2026-11-02 11:03:00', 'Second cascade text', 'v1.4')
        """
    )
    conn.execute(
        """
        INSERT INTO cluster_messages (cluster_id, message_id, channel_id, delay_seconds, similarity_to_centroid)
        VALUES ('cl-test-1', 'm1', 'ch-test-1', 0, 1.0),
               ('cl-test-1', 'm2', 'ch-test-2', 60, 0.95),
               ('cl-test-1', 'm3', 'ch-test-3', 180, 0.90),
               ('cl-test-2', 'm4', 'ch-test-1', 0, 1.0),
               ('cl-test-2', 'm5', 'ch-test-2', 90, 0.92)
        """
    )
    conn.commit()

    scoring_service.recalculate_all_scores()
    alert_service.evaluate_cluster_alert(
        cluster_id="cl-test-1",
        channel_count=3,
        time_span_seconds=240,
        avg_similarity=0.94,
        narrative_tag="Energy crisis and tariffs",
    )

    items = list_ranked_channels(scoring_service=scoring_service, min_score=0, narrative=None)
    assert len(items) >= 4
    scores = [item.score for item in items]
    assert scores == sorted(scores, reverse=True)
    for item in items:
        assert item.explanation.summary
        assert item.explanation.breakdown.dominant_factor
        assert 0 <= item.coordination_score <= 100
        assert item.narrative_risk in ("low", "medium", "high")
        assert isinstance(item.has_sufficient_data, bool)

    filtered = list_ranked_channels(scoring_service=scoring_service, min_score=50, narrative=None)
    assert all(ch.score >= 50 for ch in filtered)

    channel_id = items[0].id
    detail = get_channel_detail(channel_id=channel_id, scoring_service=scoring_service)
    assert detail.id == channel_id
    assert detail.explanation.summary
    assert 0 <= detail.coordination_score <= 100
    assert detail.narrative_risk in ("low", "medium", "high")
    assert isinstance(detail.has_sufficient_data, bool)
    assert len(detail.score_history) >= 2
    assert len(detail.co_moving_channels) >= 1
    assert len(detail.joined_clusters) >= 1

    coord_groups = scoring_service.get_channel_coordination_groups()
    assert len(coord_groups) >= 1
    assert len(coord_groups[0].channel_ids) >= 2

    with pytest.raises(AppError) as exc_info:
        get_channel_detail(channel_id="non-existent-channel", scoring_service=scoring_service)
    assert exc_info.value.code == "RESOURCE_NOT_FOUND"
    assert exc_info.value.status_code == 404

    alerts = list_alerts(alert_service=alert_service, severity=None, status=None)
    assert len(alerts) >= 1

    target_alert_id = alerts[0].id
    dismissed = dismiss_alert(alert_id=target_alert_id, alert_service=alert_service)
    assert dismissed.status == "dismissed"


def test_syndication_wire_detection_and_discount(isolated_db: DatabaseManager) -> None:
    from app.services.scoring_service import ScoringService, detect_syndication_wire

    # Test wire detection
    is_wire, agency = detect_syndication_wire("Conform agenției Moldpres, Comisia Electorală a anunțat rezultatele.")
    assert is_wire is True
    assert agency == "Moldpres"

    is_wire2, agency2 = detect_syndication_wire("Potrivit agenției IPN, traficul a fost reluat.")
    assert is_wire2 is True
    assert agency2 == "Ipn"

    is_wire_none, _ = detect_syndication_wire("Mesaj anonim despre sabotaj și panică totală!")
    assert is_wire_none is False

    service = ScoringService(db_manager=isolated_db)

    # Coordinated disinfo channel
    disinfo_score, disinfo_band, _ = service.compute_channel_score(
        channel_id="ch-disinfo",
        cluster_participation_share=85,
        copy_delay_factor=90,
        co_movement_repetition=80,
        narrative_weight=85,
        linked_clusters_count=5,
        co_moving_channels=["@peer1", "@peer2"],
        median_lead_lag_seconds=60,
        primary_narrative="Anti-EU / Europe is falling apart",
        is_syndicated_agency=False,
    )
    assert disinfo_score >= 70
    assert disinfo_band == "high"

    # Syndicated news agency reposting (same raw metrics, but accredited wire)
    syndicated_score, syndicated_band, explanation = service.compute_channel_score(
        channel_id="ch-syndicated",
        cluster_participation_share=85,
        copy_delay_factor=90,
        co_movement_repetition=80,
        narrative_weight=85,
        linked_clusters_count=5,
        co_moving_channels=["@peer1", "@peer2"],
        median_lead_lag_seconds=60,
        primary_narrative="Other / not disinformation",
        is_syndicated_agency=True,
    )
    # The syndication discount ensures it does NOT trigger false high risk alert
    assert syndicated_score < 70
    assert syndicated_band != "high"
    assert "syndicated news agency reporting detected" in explanation.summary
