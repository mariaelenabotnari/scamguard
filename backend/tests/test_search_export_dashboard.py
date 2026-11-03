"""Tests for unified search, export quotas, and dashboard observability."""

from pathlib import Path

import pytest

from app.api.routes.dashboard_routes import get_dashboard_overview, get_shell_summary
from app.api.routes.export_routes import download_export, get_export_quota, trigger_export
from app.api.routes.search_routes import search_all
from app.core.errors import AppError
from app.core.security import LoginRateLimiter, PasswordHasher, TokenManager
from app.db.database import DatabaseManager
from app.dtos.export_dto import TriggerExportInputDto
from app.repositories.cluster_repository import SqliteClusterRepository
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.user_repository import SqliteParameterRepository, SqliteUserRepository
from app.services.auth_service import AuthService
from app.services.clustering_service import ClusteringService
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService
from app.services.scoring_service import ScoringService
from app.services.search_service import SearchService
from app.services.similarity_service import SimilarityService


@pytest.fixture()
def isolated_db(tmp_path: Path) -> DatabaseManager:
    db_file = tmp_path / "test_search_export.db"
    db = DatabaseManager(sqlite_path=str(db_file))
    db.run_migrations()
    return db


def test_search_service_attaches_complete_score_explanations(
    isolated_db: DatabaseManager,
) -> None:
    scoring_service = ScoringService(db_manager=isolated_db)
    msg_repo = SqliteMessageRepository(db_manager=isolated_db)
    cl_repo = SqliteClusterRepository(db_manager=isolated_db)
    param_repo = SqliteParameterRepository(db_manager=isolated_db)
    sim_service = SimilarityService()
    clustering_service = ClusteringService(
        message_repo=msg_repo,
        cluster_repo=cl_repo,
        param_repo=param_repo,
        similarity_service=sim_service,
    )
    search_service = SearchService(
        db_manager=isolated_db,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )

    results = search_service.search_all(query="")
    assert len(results.channels) >= 4
    assert len(results.messages) >= 3

    for msg in results.messages:
        assert msg.explanation.parameter_version
        assert msg.explanation.summary
        assert msg.explanation.breakdown.dominant_factor
        assert 0 <= msg.channel_score <= 100
        assert msg.risk_band in ("low", "medium", "high")

    filtered = search_service.search_all(query="gaze")
    assert any("gaze" in m.snippet.lower() for m in filtered.messages)


def test_export_service_rate_limiting_and_format_generation(
    isolated_db: DatabaseManager,
) -> None:
    scoring_service = ScoringService(db_manager=isolated_db)
    msg_repo = SqliteMessageRepository(db_manager=isolated_db)
    cl_repo = SqliteClusterRepository(db_manager=isolated_db)
    param_repo = SqliteParameterRepository(db_manager=isolated_db)
    sim_service = SimilarityService()
    clustering_service = ClusteringService(
        message_repo=msg_repo,
        cluster_repo=cl_repo,
        param_repo=param_repo,
        similarity_service=sim_service,
    )
    export_service = ExportService(
        db_manager=isolated_db,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )

    quota_new = export_service.get_quota(actor_key="user@test.md", role="visitor")
    assert quota_new.account_tier == "new_account"
    assert quota_new.daily_exports_limit == 3
    assert quota_new.max_rows_per_export == 250

    quota_verified = export_service.get_quota(actor_key="lead@test.md", role="journalist")
    assert quota_verified.account_tier == "verified_researcher"
    assert quota_verified.daily_exports_limit == 50

    receipt_csv, payload_csv = export_service.trigger_export(
        actor_key="user@test.md",
        role="visitor",
        scope="channels",
        export_format="csv",
    )
    assert receipt_csv.format == "csv"
    assert "handle" in payload_csv
    assert "score" in payload_csv

    receipt_json, payload_json = export_service.trigger_export(
        actor_key="user@test.md",
        role="visitor",
        scope="clusters",
        export_format="json",
    )
    assert receipt_json.format == "json"
    assert payload_json.startswith("[") or payload_json.startswith("{")

    export_service.trigger_export(
        actor_key="user@test.md",
        role="visitor",
        scope="channels",
        export_format="csv",
    )

    with pytest.raises(AppError) as exc_info:
        export_service.trigger_export(
            actor_key="user@test.md",
            role="visitor",
            scope="channels",
            export_format="csv",
        )
    assert exc_info.value.code == "EXPORT_QUOTA_EXCEEDED"
    assert exc_info.value.status_code == 429


def test_dashboard_service_overview_and_observability_logging(
    isolated_db: DatabaseManager,
) -> None:
    dashboard_service = DashboardService(db_manager=isolated_db)

    overview_7d = dashboard_service.get_overview("7d")
    assert overview_7d.range == "7d"
    assert len(overview_7d.timeline.points) == 7
    assert len(overview_7d.stats) == 4
    assert overview_7d.banner.active_channels_count >= 12

    overview_24h = dashboard_service.get_overview("24h")
    assert overview_24h.range == "24h"
    assert len(overview_24h.timeline.points) == 6

    shell = dashboard_service.get_shell_summary(role="journalist")
    assert shell.user.role == "journalist"
    assert len(shell.pulse_bars) == 7
    assert len(shell.quick_cards) == 3

    conn = isolated_db.connection
    events = conn.execute("SELECT COUNT(*) AS cnt FROM observability_events").fetchone()
    assert events is not None
    assert int(events["cnt"]) >= 2


def test_search_export_dashboard_route_functions(isolated_db: DatabaseManager) -> None:
    scoring_service = ScoringService(db_manager=isolated_db)
    msg_repo = SqliteMessageRepository(db_manager=isolated_db)
    cl_repo = SqliteClusterRepository(db_manager=isolated_db)
    param_repo = SqliteParameterRepository(db_manager=isolated_db)
    sim_service = SimilarityService()
    clustering_service = ClusteringService(
        message_repo=msg_repo,
        cluster_repo=cl_repo,
        param_repo=param_repo,
        similarity_service=sim_service,
    )
    search_service = SearchService(
        db_manager=isolated_db,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )
    export_service = ExportService(
        db_manager=isolated_db,
        scoring_service=scoring_service,
        clustering_service=clustering_service,
    )
    dashboard_service = DashboardService(db_manager=isolated_db)
    hasher = PasswordHasher()
    user_repo = SqliteUserRepository(db_manager=isolated_db, hasher=hasher)
    auth_service = AuthService(
        user_repo=user_repo,
        hasher=hasher,
        token_manager=TokenManager(),
        rate_limiter=LoginRateLimiter(),
    )

    search_data = search_all(search_service=search_service, q="tarife")
    assert len(search_data.channels) >= 0
    assert len(search_data.messages) >= 1

    quota_data = get_export_quota(
        export_service=export_service,
        auth_service=auth_service,
        token=None,
        x_forwarded_for="127.0.0.1",
    )
    assert quota_data.account_tier == "new_account"
    assert quota_data.daily_exports_limit == 3

    receipt_data = trigger_export(
        input_dto=TriggerExportInputDto(scope="channels", format="json"),
        export_service=export_service,
        auth_service=auth_service,
        token=None,
        x_forwarded_for="127.0.0.1",
    )
    assert receipt_data.format == "json"

    download_resp = download_export(
        scope="channels",
        format="csv",
        export_service=export_service,
        auth_service=auth_service,
        token=None,
        x_forwarded_for="127.0.0.1",
    )
    assert download_resp.media_type == "text/csv"

    overview_data = get_dashboard_overview(dashboard_service=dashboard_service, range="30d")
    assert overview_data.range == "30d"

    shell_data = get_shell_summary(
        dashboard_service=dashboard_service,
        auth_service=auth_service,
        token=None,
    )
    assert shell_data.user.role == "visitor"
