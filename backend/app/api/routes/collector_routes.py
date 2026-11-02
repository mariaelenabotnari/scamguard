"""HTTP routes for triggering Telegram collection runs and NFR-11 deleted-post purging."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import AuthServiceDep, BearerTokenDep, CollectorServiceDep
from app.dtos.collector_dto import (
    CollectionRunDto,
    PurgeDeletedPostInputDto,
    PurgeDeletedPostReceiptDto,
    StoredMessageDto,
)

router = APIRouter(prefix="/api/v1/collector", tags=["collector"])


@router.post("/run", response_model=CollectionRunDto)
def trigger_collection_run(
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    collector_service: CollectorServiceDep,
) -> CollectionRunDto:
    auth_service.require_roles(token, ("journalist", "admin"))
    return collector_service.poll_active_channels()


@router.get("/runs", response_model=list[CollectionRunDto])
def get_collection_runs(
    collector_service: CollectorServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[CollectionRunDto]:
    return collector_service.list_runs(limit=limit)


@router.get("/messages", response_model=list[StoredMessageDto])
def get_collected_messages(
    collector_service: CollectorServiceDep,
    channel_id: Annotated[str | None, Query(alias="channelId")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[StoredMessageDto]:
    return collector_service.list_messages(channel_id=channel_id, limit=limit)


@router.post("/purge-deleted", response_model=PurgeDeletedPostReceiptDto)
def purge_source_deleted_post(
    payload: PurgeDeletedPostInputDto,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    collector_service: CollectorServiceDep,
) -> PurgeDeletedPostReceiptDto:
    auth_service.require_roles(token, ("journalist", "admin"))
    return collector_service.purge_deleted_post(payload.message_id)
