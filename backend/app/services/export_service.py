"""Export quota enforcement and data extraction service for channels and clusters."""

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.export_dto import (
    AccountTier,
    ExportFormat,
    ExportQuotaDto,
    ExportReceiptDto,
    ExportScope,
)
from app.services.clustering_service import IClusteringService
from app.services.scoring_service import IScoringService


class IExportService(Protocol):
    def get_quota(self, actor_key: str, role: str) -> ExportQuotaDto: ...

    def trigger_export(
        self,
        actor_key: str,
        role: str,
        scope: ExportScope,
        export_format: ExportFormat,
    ) -> tuple[ExportReceiptDto, str]: ...


class ExportService(IExportService):
    """Enforces daily export rate limits and generates CSV/JSON data payloads."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        scoring_service: IScoringService,
        clustering_service: IClusteringService,
    ) -> None:
        self._db = db_manager
        self._scoring_service = scoring_service
        self._clustering_service = clustering_service

    def _determine_tier(self, role: str) -> AccountTier:
        if role in ("journalist", "admin"):
            return "verified_researcher"
        return "new_account"

    def get_quota(self, actor_key: str, role: str) -> ExportQuotaDto:
        tier = self._determine_tier(role)
        daily_limit = 50 if tier == "verified_researcher" else 3
        max_rows = 5000 if tier == "verified_researcher" else 250

        today_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        conn = self._db.connection
        row = conn.execute(
            """
            SELECT COUNT(*) AS used_today
            FROM export_usage
            WHERE actor_key = ? AND exported_at LIKE ?
            """,
            (actor_key, f"{today_prefix}%"),
        ).fetchone()

        used_today = int(row["used_today"]) if row is not None else 0

        return ExportQuotaDto(
            accountTier=tier,
            maxRowsPerExport=max_rows,
            dailyExportsLimit=daily_limit,
            dailyExportsUsed=used_today,
        )

    def trigger_export(
        self,
        actor_key: str,
        role: str,
        scope: ExportScope,
        export_format: ExportFormat,
    ) -> tuple[ExportReceiptDto, str]:
        quota = self.get_quota(actor_key=actor_key, role=role)
        if quota.daily_exports_used >= quota.daily_exports_limit:
            msg = (
                f"Daily export quota ({quota.daily_exports_limit}) "
                f"exceeded for {quota.account_tier}."
            )
            raise AppError(
                code="EXPORT_QUOTA_EXCEEDED",
                message=msg,
                status_code=429,
                details={
                    "daily_limit": quota.daily_exports_limit,
                    "daily_used": quota.daily_exports_used,
                    "account_tier": quota.account_tier,
                },
            )

        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # Extract data according to scope
        if scope == "channels":
            channels = self._scoring_service.list_ranked_channels()
            sliced_channels = channels[: quota.max_rows_per_export]
            rows_count = len(sliced_channels)

            if export_format == "json":
                payload = json.dumps(
                    [ch.model_dump(by_alias=True) for ch in sliced_channels],
                    indent=2,
                )
            else:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "id",
                        "handle",
                        "title",
                        "language",
                        "score",
                        "risk_band",
                        "primary_narrative",
                        "dominant_factor",
                        "summary",
                    ]
                )
                for ch in sliced_channels:
                    writer.writerow(
                        [
                            ch.id,
                            ch.handle,
                            ch.title,
                            ch.language,
                            ch.score,
                            ch.risk_band,
                            ch.primary_narrative,
                            ch.explanation.breakdown.dominant_factor,
                            ch.explanation.summary,
                        ]
                    )
                payload = output.getvalue()
        else:
            clusters = self._clustering_service.list_clusters()
            sliced_clusters = clusters[: quota.max_rows_per_export]
            rows_count = len(sliced_clusters)

            if export_format == "json":
                payload = json.dumps(
                    [cl.model_dump(by_alias=True) for cl in sliced_clusters],
                    indent=2,
                )
            else:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(
                    [
                        "id",
                        "headline_summary",
                        "narrative_category",
                        "channels_count",
                        "messages_count",
                        "average_similarity",
                        "first_posted_at",
                        "last_posted_at",
                        "parameter_version",
                    ]
                )
                for cl in sliced_clusters:
                    writer.writerow(
                        [
                            cl.id,
                            cl.headline_summary,
                            cl.narrative_category,
                            cl.channels_count,
                            cl.messages_count,
                            cl.average_similarity,
                            cl.first_posted_at,
                            cl.last_posted_at,
                            cl.parameter_version,
                        ]
                    )
                payload = output.getvalue()

        # Log usage
        conn = self._db.connection
        conn.execute(
            """
            INSERT INTO export_usage (
                id, actor_key, account_tier, scope, format,
                rows_exported, exported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                actor_key,
                quota.account_tier,
                scope,
                export_format,
                rows_count,
                now.isoformat(),
            ),
        )
        conn.commit()

        receipt = ExportReceiptDto(
            fileName=f"scamguard_{scope}_{date_str}.{export_format}",
            format=export_format,
            scope=scope,
            rowsExported=rows_count,
            generatedAt=timestamp_str,
        )
        return receipt, payload
