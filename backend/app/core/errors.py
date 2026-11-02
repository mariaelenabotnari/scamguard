"""Standardized API error DTOs, domain exceptions, and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorBodyDto(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: dict[str, object] | None = Field(
        default=None, description="Optional structured validation or context details"
    )


class ErrorResponseDto(BaseModel):
    error: ErrorBodyDto


class AppError(Exception):
    """Domain-level exception converted into a standardized ErrorResponseDto."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dto(self) -> ErrorResponseDto:
        return ErrorResponseDto(
            error=ErrorBodyDto(
                code=self.code,
                message=self.message,
                details=self.details,
            )
        )


async def handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dto().model_dump(),
        )
    fallback = ErrorResponseDto(
        error=ErrorBodyDto(code="INTERNAL_ERROR", message="Unexpected server error.")
    )
    return JSONResponse(status_code=500, content=fallback.model_dump())


def register_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(AppError, handle_app_error)
