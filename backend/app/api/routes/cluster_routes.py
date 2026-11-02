"""HTTP routes for coordinated clusters list, side-by-side comparison, and detection trigger."""

from fastapi import APIRouter

from app.core.dependencies import AuthServiceDep, BearerTokenDep, ClusteringServiceDep
from app.dtos.cluster_dto import (
    ClusterDetailDto,
    ClusterSummaryDto,
    DetectClustersInputDto,
)

router = APIRouter(prefix="/api/v1/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterSummaryDto])
def list_detected_clusters(
    clustering_service: ClusteringServiceDep,
) -> list[ClusterSummaryDto]:
    return clustering_service.list_clusters()


@router.get("/{cluster_id}", response_model=ClusterDetailDto)
def get_cluster_comparison(
    cluster_id: str,
    clustering_service: ClusteringServiceDep,
) -> ClusterDetailDto:
    return clustering_service.get_cluster_detail(cluster_id)


@router.post("/detect", response_model=list[ClusterDetailDto])
def run_cluster_detection(
    payload: DetectClustersInputDto,
    token: BearerTokenDep,
    auth_service: AuthServiceDep,
    clustering_service: ClusteringServiceDep,
) -> list[ClusterDetailDto]:
    auth_service.require_roles(token, ("journalist", "admin"))
    return clustering_service.detect_and_store_clusters(
        similarity_threshold=payload.similarity_threshold,
        time_window_minutes=payload.time_window_minutes,
    )
