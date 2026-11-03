"""Coordination alert generation, persistence, and dismissal service."""

import hashlib
from datetime import UTC, datetime
from typing import Protocol

from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.scoring_dto import AlertItemDto, AlertSeverity, AlertStatus

DEFAULT_ALERT_PARAMETER_VERSION = "v1.4.2-alerts"


class IAlertService(Protocol):
    def list_alerts(
        self,
        *,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[AlertItemDto]: ...

    def dismiss_alert(self, alert_id: str) -> AlertItemDto: ...

    def evaluate_cluster_alert(
        self,
        *,
        cluster_id: str,
        channel_count: int,
        time_span_seconds: int,
        avg_similarity: float,
        narrative_tag: str,
        parameter_version: str = DEFAULT_ALERT_PARAMETER_VERSION,
    ) -> AlertItemDto | None: ...


_SEED_ALERTS: tuple[dict[str, str], ...] = (
    {
        "id": "ALT-20261102-01",
        "severity": "high",
        "status": "new",
        "triggered_at": "2026-11-02T14:25:00Z",
        "title": "4 channels reposted commercial bank withdrawal freeze claim within 115s",
        "summary": (
            "Synchronized narrative propagation detected across @moldova_puls_actual, "
            "@gagauzia_info_live, @chisinau_radar24, and @balti_expres_ro (mean similarity 0.93)."
        ),
        "narrative_tag": "Economic Collapse & Banking Panic",
        "target_route": "/clusters/CL-20261102-01",
        "parameter_version": DEFAULT_ALERT_PARAMETER_VERSION,
    },
    {
        "id": "ALT-20261102-02",
        "severity": "medium",
        "status": "new",
        "triggered_at": "2026-11-02T11:10:00Z",
        "title": "3 channels amplified emergency winter gas rationing narrative within 240s",
        "summary": (
            "Near-duplicate Russian and Romanian posts appeared across 3 monitored "
            "channels with 0.89 semantic similarity."
        ),
        "narrative_tag": "Energy Grid & Gas Sabotage Rumors",
        "target_route": "/clusters/CL-20261101-04",
        "parameter_version": DEFAULT_ALERT_PARAMETER_VERSION,
    },
    {
        "id": "ALT-20261101-03",
        "severity": "low",
        "status": "seen",
        "triggered_at": "2026-11-01T17:45:00Z",
        "title": "Risk score spike (+8 pts) on @moldova_puls_actual",
        "summary": (
            "Channel coordination risk score crossed 90/100 following repeated "
            "co-movement with @gagauzia_info_live."
        ),
        "narrative_tag": "EU Integration & Sovereignty Myths",
        "target_route": "/channels/ch-md-puls",
        "parameter_version": DEFAULT_ALERT_PARAMETER_VERSION,
    },
)


def _normalize_severity(raw: str) -> AlertSeverity:
    lowered = raw.lower()
    if lowered == "high":
        return "high"
    if lowered == "medium":
        return "medium"
    return "low"


def _normalize_status(raw: str) -> AlertStatus:
    lowered = raw.lower()
    if lowered == "dismissed":
        return "dismissed"
    if lowered == "seen":
        return "seen"
    return "new"


class AlertService(IAlertService):
    """Evaluates deterministic coordination alert thresholds and manages alert lifecycle."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        conn = self._db.connection
        row = conn.execute("SELECT COUNT(*) AS cnt FROM alerts").fetchone()
        count = int(row["cnt"]) if row is not None else 0
        if count > 0:
            return

        for alert in _SEED_ALERTS:
            conn.execute(
                """
                INSERT OR IGNORE INTO alerts (
                    id, severity, status, triggered_at, title,
                    summary, narrative_tag, target_route, parameter_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["id"],
                    alert["severity"],
                    alert["status"],
                    alert["triggered_at"],
                    alert["title"],
                    alert["summary"],
                    alert["narrative_tag"],
                    alert["target_route"],
                    alert["parameter_version"],
                ),
            )
        conn.commit()

    def list_alerts(
        self,
        *,
        severity: str | None = None,
        status: str | None = None,
    ) -> list[AlertItemDto]:
        query = """
            SELECT id, severity, status, triggered_at, title, summary,
                   narrative_tag, target_route, parameter_version
            FROM alerts
            WHERE 1 = 1
        """
        params: list[object] = []
        if severity:
            query += " AND LOWER(severity) = ?"
            params.append(severity.lower())
        if status:
            query += " AND LOWER(status) = ?"
            params.append(status.lower())
        else:
            query += " AND LOWER(status) != 'dismissed'"

        query += " ORDER BY triggered_at DESC, id ASC"

        conn = self._db.connection
        rows = conn.execute(query, tuple(params)).fetchall()

        return [
            AlertItemDto(
                id=str(row["id"]),
                severity=_normalize_severity(str(row["severity"])),
                status=_normalize_status(str(row["status"])),
                triggeredAt=str(row["triggered_at"]),
                title=str(row["title"]),
                summary=str(row["summary"]),
                narrativeTag=str(row["narrative_tag"]),
                targetRoute=str(row["target_route"]),
                parameterVersion=str(row["parameter_version"]),
            )
            for row in rows
        ]

    def dismiss_alert(self, alert_id: str) -> AlertItemDto:
        conn = self._db.connection
        row = conn.execute(
            """
            SELECT id, severity, status, triggered_at, title, summary,
                   narrative_tag, target_route, parameter_version
            FROM alerts
            WHERE id = ?
            """,
            (alert_id,),
        ).fetchone()
        if row is None:
            raise AppError(
                code="RESOURCE_NOT_FOUND",
                message=f"Alert '{alert_id}' was not found.",
                status_code=404,
                details={"alert_id": alert_id},
            )

        conn.execute(
            "UPDATE alerts SET status = 'dismissed' WHERE id = ?",
            (alert_id,),
        )
        conn.commit()

        return AlertItemDto(
            id=str(row["id"]),
            severity=_normalize_severity(str(row["severity"])),
            status="dismissed",
            triggeredAt=str(row["triggered_at"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            narrativeTag=str(row["narrative_tag"]),
            targetRoute=str(row["target_route"]),
            parameterVersion=str(row["parameter_version"]),
        )

    def evaluate_cluster_alert(
        self,
        *,
        cluster_id: str,
        channel_count: int,
        time_span_seconds: int,
        avg_similarity: float,
        narrative_tag: str,
        parameter_version: str = DEFAULT_ALERT_PARAMETER_VERSION,
    ) -> AlertItemDto | None:
        if channel_count < 2 or avg_similarity < 0.78:
            return None

        if channel_count >= 4 and time_span_seconds <= 180 and avg_similarity >= 0.88:
            severity: AlertSeverity = "high"
        elif channel_count >= 3 and time_span_seconds <= 600 and avg_similarity >= 0.82:
            severity = "medium"
        else:
            severity = "low"

        seed_bytes = f"{cluster_id}:{parameter_version}".encode()
        digest = hashlib.sha256(seed_bytes).hexdigest()[:8].upper()
        alert_id = f"ALT-{digest}"
        now_iso = datetime.now(UTC).isoformat()
        title = (
            f"{channel_count} channels propagated '{narrative_tag}' "
            f"cluster within {time_span_seconds}s"
        )
        summary = (
            f"Cluster {cluster_id} spanned {channel_count} distinct channels "
            f"in {time_span_seconds}s with {avg_similarity:.2f} average similarity."
        )
        target_route = f"/clusters/{cluster_id}"

        conn = self._db.connection
        conn.execute(
            """
            INSERT OR REPLACE INTO alerts (
                id, severity, status, triggered_at, title,
                summary, narrative_tag, target_route, parameter_version
            ) VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                severity,
                now_iso,
                title,
                summary,
                narrative_tag,
                target_route,
                parameter_version,
            ),
        )
        conn.commit()

        return AlertItemDto(
            id=alert_id,
            severity=severity,
            status="new",
            triggeredAt=now_iso,
            title=title,
            summary=summary,
            narrativeTag=narrative_tag,
            targetRoute=target_route,
            parameterVersion=parameter_version,
        )
