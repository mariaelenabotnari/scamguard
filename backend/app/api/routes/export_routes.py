"""Routes for exporting monitored channels and cluster coordination data."""

from typing import Annotated

from fastapi import APIRouter, Header, Query, Response

from app.core.dependencies import AuthServiceDep, BearerTokenDep, ExportServiceDep
from app.dtos.export_dto import (
    ExportFormat,
    ExportQuotaDto,
    ExportReceiptDto,
    ExportScope,
    TriggerExportInputDto,
)

router = APIRouter(prefix="/api/v1", tags=["export"])


@router.get("/export/quota", response_model=ExportQuotaDto)
def get_export_quota(
    export_service: ExportServiceDep,
    auth_service: AuthServiceDep,
    token: BearerTokenDep = None,
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> ExportQuotaDto:
    user = auth_service.get_current_user(token) if token else None
    actor_key = user.email if user else (x_forwarded_for or "anonymous-client")
    role = user.role if user else "visitor"
    return export_service.get_quota(actor_key=actor_key, role=role)


@router.post("/export", response_model=ExportReceiptDto)
def trigger_export(
    input_dto: TriggerExportInputDto,
    export_service: ExportServiceDep,
    auth_service: AuthServiceDep,
    token: BearerTokenDep = None,
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> ExportReceiptDto:
    user = auth_service.get_current_user(token) if token else None
    actor_key = user.email if user else (x_forwarded_for or "anonymous-client")
    role = user.role if user else "visitor"
    receipt, _ = export_service.trigger_export(
        actor_key=actor_key,
        role=role,
        scope=input_dto.scope,
        export_format=input_dto.format,
    )
    return receipt


@router.get("/export/download")
def download_export(
    scope: Annotated[ExportScope, Query()] = "clusters",
    format: Annotated[ExportFormat, Query()] = "csv",
    export_service: ExportServiceDep = None,  # type: ignore[assignment]
    auth_service: AuthServiceDep = None,  # type: ignore[assignment]
    token: BearerTokenDep = None,
    x_forwarded_for: Annotated[str | None, Header()] = None,
) -> Response:
    user = auth_service.get_current_user(token) if token else None
    actor_key = user.email if user else (x_forwarded_for or "anonymous-client")
    role = user.role if user else "visitor"
    receipt, payload = export_service.trigger_export(
        actor_key=actor_key,
        role=role,
        scope=scope,
        export_format=format,
    )

    media_type = "text/csv" if format == "csv" else "application/json"
    headers = {"Content-Disposition": f'attachment; filename="{receipt.file_name}"'}
    return Response(content=payload, media_type=media_type, headers=headers)
