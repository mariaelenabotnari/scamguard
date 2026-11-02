"""FastAPI entry point for Scamguard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    application = FastAPI(
        title="Scamguard API",
        version="0.1.0",
        description="Detects coordinated activity and narrative propagation across Telegram channels.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
