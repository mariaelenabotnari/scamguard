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

    filtered = list_ranked_channels(scoring_service=scoring_service, min_score=70, narrative=None)
    assert all(ch.score >= 70 for ch in filtered)

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
