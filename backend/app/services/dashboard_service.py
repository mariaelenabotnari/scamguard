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


_TIMELINE_PRESETS: dict[TimeRangeOption, list[dict[str, object]]] = {
    "24h": [
        {"axis": "00:00", "date": "Today 00:00", "msgs": 620, "clusters": 2, "norm_y": 0.36},
        {"axis": "04:00", "date": "Today 04:00", "msgs": 890, "clusters": 4, "norm_y": 0.48},
        {"axis": "08:00", "date": "Today 08:00", "msgs": 740, "clusters": 3, "norm_y": 0.32},
        {"axis": "12:00", "date": "Today 12:00", "msgs": 1380, "clusters": 6, "norm_y": 0.62},
        {"axis": "16:00", "date": "Today 16:00", "msgs": 1120, "clusters": 5, "norm_y": 0.52},
        {"axis": "20:00", "date": "Today 20:00", "msgs": 1640, "clusters": 7, "norm_y": 0.74},
    ],
    "7d": [
        {"axis": "Mon", "date": "Oct 28", "msgs": 2900, "clusters": 8, "norm_y": 0.40},
        {"axis": "Tue", "date": "Oct 29", "msgs": 3400, "clusters": 11, "norm_y": 0.52},
        {"axis": "Wed", "date": "Oct 30", "msgs": 4200, "clusters": 14, "norm_y": 0.68},
        {"axis": "Thu", "date": "Oct 31", "msgs": 3800, "clusters": 9, "norm_y": 0.58},
        {"axis": "Fri", "date": "Nov 01", "msgs": 5100, "clusters": 18, "norm_y": 0.82},
        {"axis": "Sat", "date": "Nov 02", "msgs": 4600, "clusters": 15, "norm_y": 0.72},
        {"axis": "Sun", "date": "Nov 03", "msgs": 3900, "clusters": 12, "norm_y": 0.60},
    ],
    "30d": [
        {"axis": "W1", "date": "Oct 06 - 12", "msgs": 18500, "clusters": 42, "norm_y": 0.45},
        {"axis": "W2", "date": "Oct 13 - 19", "msgs": 22100, "clusters": 56, "norm_y": 0.60},
        {"axis": "W3", "date": "Oct 20 - 26", "msgs": 28400, "clusters": 71, "norm_y": 0.78},
        {"axis": "W4", "date": "Oct 27 - Nov 03", "msgs": 31200, "clusters": 84, "norm_y": 0.88},
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
        channels_count = int(row_ch["cnt"]) if row_ch else 312

        row_cl = conn.execute("SELECT COUNT(*) AS cnt FROM clusters").fetchone()
        clusters_count = int(row_cl["cnt"]) if row_cl else 48

        raw_points = _TIMELINE_PRESETS.get(time_range, _TIMELINE_PRESETS["7d"])
        timeline_points = [
            TimelinePointDto(
                id=f"{time_range}-{idx + 1}",
                axisLabel=str(pt["axis"]),
                dateLabel=str(pt["date"]),
                messagesCount=int(str(pt["msgs"])),
                flaggedClustersCount=int(str(pt["clusters"])),
                formattedHeadline=f"{pt['msgs']:,} msgs • {pt['clusters']} clusters",
                normalizedY=float(str(pt["norm_y"])),
                isHighlighted=(idx == len(raw_points) // 2),
            )
            for idx, pt in enumerate(raw_points)
        ]

        total_msgs = sum(pt.messages_count for pt in timeline_points)

        subtitle_msg = (
            f"Have a nice Day to Work ! • {time_range} coordination scan active across Moldova"
        )
        banner = DashboardBannerDto(
            greetingTitle="Hello Elena Botnari",
            subtitle=subtitle_msg,
            activeChannelsCount=max(channels_count, 12),
            parameterVersion="v1.4",
        )

        timeline = ActivityTimelineDto(
            title="Profile Growth",
            subtitle=f"Overall Information • Coordinated Messages & Clusters ({time_range})",
            range=time_range,
            points=timeline_points,
        )

        stats = [
            StatCardMetricDto(
                id="monitored-channels",
                label="Monitored Channels",
                formattedValue=str(channels_count),
                numericValue=float(channels_count),
                deltaPercent=4.8,
                formattedDelta="+4.8%",
                trendDirection="up",
                icon="user",
                tone="lavender",
            ),
            StatCardMetricDto(
                id="clusters-detected",
                label="Coordinated Clusters",
                formattedValue=str(clusters_count),
                numericValue=float(clusters_count),
                deltaPercent=12.5,
                formattedDelta="+12.5%",
                trendDirection="up",
                icon="briefcase",
                tone="cyan",
            ),
            StatCardMetricDto(
                id="coordinated-messages",
                label="Coordinated Messages",
                formattedValue=f"{total_msgs:,}",
                numericValue=float(total_msgs),
                deltaPercent=8.1,
                formattedDelta="+8.1%",
                trendDirection="up",
                icon="envelope",
                tone="peach",
            ),
            StatCardMetricDto(
                id="median-delay",
                label="Median Propagation",
                formattedValue="142s",
                numericValue=142.0,
                deltaPercent=-6.4,
                formattedDelta="-6.4%",
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
