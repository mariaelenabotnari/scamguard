import json
import logging

from app.api.routes.health_routes import get_health, get_v1_health, get_v1_meta
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import StructuredJsonFormatter
from app.db.database import DatabaseManager
from app.main import create_app
from app.services.health_service import HealthService


def test_health_service_returns_ok_and_meta_dtos() -> None:
    settings = Settings(app_name="Scamguard API", app_version="0.1.0")
    db_manager = DatabaseManager(":memory:")
    service = HealthService(settings=settings, db_manager=db_manager)

    health = service.check_health()
    assert health.status == "ok"
    assert health.service == "scamguard-backend"
    assert health.version == "0.1.0"

    meta = service.get_meta()
    assert meta.app_name == "Scamguard API"
    assert meta.schema_revision == "0008_live_telegram_collector"
    assert meta.active_parameter_version == "v1.4"
    assert meta.max_collection_interval_minutes == 10


def test_database_migrations_create_initial_tables_and_seed_parameters() -> None:
    db_manager = DatabaseManager(":memory:")
    revision = db_manager.run_migrations()
    assert revision == "0008_live_telegram_collector"

    cursor = db_manager.connection.cursor()
    cursor.execute("SELECT version, collection_interval_minutes FROM parameter_sets")
    row = cursor.fetchone()
    assert row is not None
    assert row["version"] == "v1.4"
    assert row["collection_interval_minutes"] == 5


def test_structured_logging_and_app_error_envelope() -> None:
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="scamguard.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Collector poll completed",
        args=(),
        exc_info=None,
    )
    formatted = json.loads(formatter.format(record))
    assert formatted["level"] == "INFO"
    assert formatted["message"] == "Collector poll completed"

    err = AppError(
        code="INVALID_INTERVAL",
        message="Collection interval cannot exceed 10 minutes.",
        status_code=422,
        details={"max_minutes": 10},
    )
    dto = err.to_dto()
    assert dto.error.code == "INVALID_INTERVAL"
    assert dto.error.details == {"max_minutes": 10}


def test_health_and_meta_routes_are_registered_and_delegate_to_service() -> None:
    application = create_app()
    openapi_schema = application.openapi()
    assert "/health" in openapi_schema["paths"]
    assert "/api/v1/health" in openapi_schema["paths"]
    assert "/api/v1/meta" in openapi_schema["paths"]

    db_manager = DatabaseManager(":memory:")
    service = HealthService(settings=Settings(), db_manager=db_manager)

    assert get_health(health_service=service).status == "ok"
    assert get_v1_health(health_service=service).status == "ok"
    meta = get_v1_meta(health_service=service)
    assert meta.schema_revision == "0008_live_telegram_collector"
