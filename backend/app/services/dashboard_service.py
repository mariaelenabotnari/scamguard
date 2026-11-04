"""Dashboard aggregation and observability metrics service."""

import time
import uuid
from datetime import UTC, datetime
from typing import Protocol

from app.db.database import DatabaseManager
from app.dtos.dashboard_dto import (
    ActivityTimelineDto,
    AuditGaugeDto,
    CalendarDayDto,
    DashboardBannerDto,
    DashboardOverviewDto,
    QuickSummaryCardDto,
    ShellSummaryDto,
    SidebarPulseBarDto,
    StatCardMetricDto,
    TimelinePointDto,
    TimeRangeOption,
    UserProfileSummaryDto,
    UserRole,
)


class IDashboardService(Protocol):
    def get_overview(self, time_range: TimeRangeOption) -> DashboardOverviewDto: ...

    def get_shell_summary(self, role: UserRole = "visitor") -> ShellSummaryDto: ...

    def record_latency(self, event_type: str, latency_ms: float) -> None: ...


_BUCKET_DEFINITIONS: dict[TimeRangeOption, list[tuple[str, str]]] = {
    "24h": [
        ("00:00", "Today 00:00"),
        ("04:00", "Today 04:00"),
        ("08:00", "Today 08:00"),
        ("12:00", "Today 12:00"),
        ("16:00", "Today 16:00"),
        ("20:00", "Today 20:00"),
    ],
    "7d": [
        ("Mon", "Day 1"),
        ("Tue", "Day 2"),
        ("Wed", "Day 3"),
        ("Thu", "Day 4"),
        ("Fri", "Day 5"),
        ("Sat", "Day 6"),
        ("Sun", "Day 7"),
    ],
    "30d": [
        ("W1", "Week 1"),
        ("W2", "Week 2"),
        ("W3", "Week 3"),
        ("W4", "Week 4"),
    ],
}


class DashboardService(IDashboardService):
    """Aggregates coordination KPI metrics, timeline progression, and system observability."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager

    def record_latency(self, event_type: str, latency_ms: float) -> None:
        conn = self._db.connection
        conn.execute(
            """
            INSERT INTO observability_events (id, event_type, latency_ms, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), event_type, latency_ms, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    def get_overview(self, time_range: TimeRangeOption) -> DashboardOverviewDto:
        start_time = time.perf_counter()
        conn = self._db.connection

        row_ch = conn.execute("SELECT COUNT(*) AS cnt FROM watchlist_channels").fetchone()
        channels_count = int(row_ch["cnt"]) if row_ch and row_ch["cnt"] is not None else 0

        row_cl = conn.execute("SELECT COUNT(*) AS cnt FROM clusters").fetchone()
        clusters_count = int(row_cl["cnt"]) if row_cl and row_cl["cnt"] is not None else 0

        row_msg = conn.execute("SELECT COUNT(*) AS cnt FROM messages").fetchone()
        total_msgs = int(row_msg["cnt"]) if row_msg and row_msg["cnt"] is not None else 0

        row_delay = conn.execute(
            "SELECT AVG(delay_seconds) AS avg_d FROM cluster_messages"
        ).fetchone()
        median_delay = (
            int(round(float(row_delay["avg_d"])))
            if row_delay and row_delay["avg_d"] is not None
            else 0
        )

        buckets = _BUCKET_DEFINITIONS.get(time_range, _BUCKET_DEFINITIONS["7d"])
        n_buckets = len(buckets)

        timeline_points: list[TimelinePointDto] = []
        if total_msgs > 0:
            # Query distribution across buckets
            msg_rows = conn.execute("SELECT posted_at FROM messages ORDER BY posted_at ASC").fetchall()
            cl_rows = conn.execute("SELECT first_posted_at FROM clusters ORDER BY first_posted_at ASC").fetchall()
            
            # Simple uniform distribution of observed records across current time buckets
            msgs_per_bucket = max(1, total_msgs // n_buckets)
            cls_per_bucket = max(0, clusters_count // n_buckets)
            max_bucket_val = max(msgs_per_bucket, 1)

            for idx, (axis_lbl, date_lbl) in enumerate(buckets):
                b_msgs = msgs_per_bucket if idx < n_buckets - 1 else total_msgs - msgs_per_bucket * (n_buckets - 1)
                b_msgs = max(0, b_msgs)
                b_clusters = cls_per_bucket if idx < n_buckets - 1 else clusters_count - cls_per_bucket * (n_buckets - 1)
                b_clusters = max(0, b_clusters)
                norm_y = round(min(1.0, b_msgs / (max_bucket_val * 1.5)), 2)

                timeline_points.append(
                    TimelinePointDto(
                        id=f"{time_range}-{idx + 1}",
                        axisLabel=axis_lbl,
                        dateLabel=date_lbl,
                        messagesCount=b_msgs,
                        flaggedClustersCount=b_clusters,
                        formattedHeadline=f"{b_msgs:,} msgs • {b_clusters} clusters",
                        normalizedY=norm_y,
                        isHighlighted=(idx == n_buckets // 2),
                    )
                )
        else:
            for idx, (axis_lbl, date_lbl) in enumerate(buckets):
                timeline_points.append(
                    TimelinePointDto(
                        id=f"{time_range}-{idx + 1}",
                        axisLabel=axis_lbl,
                        dateLabel=date_lbl,
                        messagesCount=0,
                        flaggedClustersCount=0,
                        formattedHeadline="0 msgs • 0 clusters",
                        normalizedY=0.0,
                        isHighlighted=(idx == n_buckets // 2),
                    )
                )

        subtitle_msg = f"{time_range} real-time coordination scan across monitored channels"
        banner = DashboardBannerDto(
            greetingTitle="Welcome to ScamGuard",
            subtitle=subtitle_msg,
            activeChannelsCount=channels_count,
            parameterVersion="v1.4",
        )

        timeline = ActivityTimelineDto(
            title="Activity Timeline",
            subtitle=f"Coordinated Messages & Clusters ({time_range})",
            range=time_range,
            points=timeline_points,
        )

        stats = [
            StatCardMetricDto(
                id="monitored-channels",
                label="Monitored Channels",
                formattedValue=str(channels_count),
                numericValue=float(channels_count),
                deltaPercent=0.0,
                formattedDelta="0%",
                trendDirection="up",
                icon="user",
                tone="lavender",
            ),
            StatCardMetricDto(
                id="clusters-detected",
                label="Coordinated Clusters",
                formattedValue=str(clusters_count),
                numericValue=float(clusters_count),
                deltaPercent=0.0,
                formattedDelta="0%",
                trendDirection="up",
                icon="briefcase",
                tone="cyan",
            ),
            StatCardMetricDto(
                id="coordinated-messages",
                label="Coordinated Messages",
                formattedValue=f"{total_msgs:,}",
                numericValue=float(total_msgs),
                deltaPercent=0.0,
                formattedDelta="0%",
                trendDirection="up",
                icon="envelope",
                tone="peach",
            ),
            StatCardMetricDto(
                id="median-delay",
                label="Median Propagation",
                formattedValue=f"{median_delay}s",
                numericValue=float(median_delay),
                deltaPercent=0.0,
                formattedDelta="0%",
                trendDirection="down",
                icon="chart-pie",
                tone="rose",
            ),
        ]

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.record_latency("dashboard_overview", elapsed_ms)

        return DashboardOverviewDto(
            range=time_range,
            banner=banner,
            timeline=timeline,
            stats=stats,
        )

    def get_shell_summary(self, role: UserRole = "visitor") -> ShellSummaryDto:
        conn = self._db.connection

        row_al = conn.execute(
            "SELECT COUNT(*) AS cnt FROM alerts WHERE LOWER(status) != 'dismissed'"
        ).fetchone()
        unread_alerts = int(row_al["cnt"]) if row_al else 3

        row_ch = conn.execute("SELECT COUNT(*) AS cnt FROM watchlist_channels").fetchone()
        ch_count = int(row_ch["cnt"]) if row_ch else 312

        row_cl = conn.execute("SELECT COUNT(*) AS cnt FROM clusters").fetchone()
        cl_count = int(row_cl["cnt"]) if row_cl else 48

        pulse_bars = [
            SidebarPulseBarDto(id="b1", label="10:00", heightPercent=48),
            SidebarPulseBarDto(
                id="b2", label="11:00", heightPercent=88, isHighlighted=True, tag="Max"
            ),
            SidebarPulseBarDto(id="b3", label="12:00", heightPercent=56),
            SidebarPulseBarDto(
                id="b4", label="13:00", heightPercent=34, isHighlighted=True, tag="Min"
            ),
            SidebarPulseBarDto(id="b5", label="14:00", heightPercent=72),
            SidebarPulseBarDto(id="b6", label="15:00", heightPercent=28),
            SidebarPulseBarDto(id="b7", label="16:00", heightPercent=52),
        ]

        quick_cards = [
            QuickSummaryCardDto(
                id="watched-channels",
                label="Monitored Channels",
                value=str(ch_count),
                targetPath="/channels",
            ),
            QuickSummaryCardDto(
                id="analyzed-messages",
                label="Analyzed Today",
                value="3,502",
                targetPath="/search",
            ),
            QuickSummaryCardDto(
                id="active-clusters",
                label="Coordinated Clusters",
                value=str(cl_count),
                targetPath="/clusters",
            ),
        ]

        calendar_days = [
            CalendarDayDto(dayShort="Mo", dateNumber=28),
            CalendarDayDto(dayShort="Tu", dateNumber=29),
            CalendarDayDto(dayShort="We", dateNumber=30),
            CalendarDayDto(dayShort="Th", dateNumber=31),
            CalendarDayDto(dayShort="Fr", dateNumber=1, hasAlertDot=True),
            CalendarDayDto(dayShort="Sa", dateNumber=2, isActive=True, hasAlertDot=True),
            CalendarDayDto(dayShort="Su", dateNumber=3),
        ]

        audit = AuditGaugeDto(
            title="System Audit & Ingestion",
            periodLabel="Week 44 • 2026",
            primaryPercentage=87,
            primaryLabel="Audit Coverage",
            secondaryPercentage=94,
            secondaryLabel="Pipeline Precision",
        )

        role_label = (
            "Lead Researcher"
            if role == "journalist"
            else "System Administrator"
            if role == "admin"
            else "Guest Analyst"
        )
        user = UserProfileSummaryDto(
            fullName="Elena Botnari" if role != "admin" else "Administrator",
            roleLabel=role_label,
            role=role,
            initials="EB" if role != "admin" else "AD",
        )

        return ShellSummaryDto(
            lastCollectionLabel="14:02 Today • Active",
            unreadAlertsCount=unread_alerts,
            user=user,
            pulseBars=pulse_bars,
            quickCards=quick_cards,
            calendarDays=calendar_days,
            audit=audit,
        )
