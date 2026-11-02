from app.api.routes.health_routes import get_health
from app.core.config import Settings
from app.main import create_app
from app.services.health_service import HealthService


def test_health_service_returns_ok_dto() -> None:
    settings = Settings(app_name="Scamguard API", app_version="0.1.0")
    service = HealthService(settings=settings)

    result = service.check_health()

    assert result.status == "ok"
    assert result.service == "scamguard-backend"
    assert result.version == "0.1.0"


def test_health_route_is_registered_and_delegates_to_service() -> None:
    application = create_app()
    openapi_schema = application.openapi()
    assert "/health" in openapi_schema["paths"]

    service = HealthService(settings=Settings())
    response = get_health(health_service=service)
    assert response.status == "ok"
