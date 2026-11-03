"""FastAPI entry point and application factory for Scamguard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin_routes import router as admin_router
from app.api.routes.auth_routes import router as auth_router
from app.api.routes.cluster_routes import router as cluster_router
from app.api.routes.collector_routes import router as collector_router
from app.api.routes.dashboard_routes import router as dashboard_router
from app.api.routes.export_routes import router as export_router
from app.api.routes.health_routes import router as health_router
from app.api.routes.health_routes import v1_system_router
from app.api.routes.narrative_routes import router as narrative_router
from app.api.routes.scoring_routes import scoring_router
from app.api.routes.search_routes import router as search_router
from app.api.routes.watchlist_routes import router as watchlist_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Detects coordinated activity and narrative propagation across Telegram channels."
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(v1_system_router)
    application.include_router(auth_router)
    application.include_router(admin_router)
    application.include_router(watchlist_router)
    application.include_router(collector_router)
    application.include_router(cluster_router)
    application.include_router(narrative_router)
    application.include_router(scoring_router)
    application.include_router(search_router)
    application.include_router(dashboard_router)
    application.include_router(export_router)

    return application


app = create_app()
