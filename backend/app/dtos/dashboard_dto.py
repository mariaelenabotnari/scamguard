"""DTOs for dashboard overview KPIs, timeline chart, and shell metadata."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TimeRangeOption = Literal["24h", "7d", "30d"]
StatCardTone = Literal["lavender", "cyan", "peach", "rose"]
TrendDirection = Literal["up", "down"]
UserRole = Literal["visitor", "journalist", "admin"]


class StatCardMetricDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    formatted_value: str = Field(..., alias="formattedValue")
    numeric_value: float = Field(..., alias="numericValue")
    delta_percent: float = Field(..., alias="deltaPercent")
    formatted_delta: str = Field(..., alias="formattedDelta")
    trend_direction: TrendDirection = Field(..., alias="trendDirection")
    icon: str
    tone: StatCardTone


class DashboardBannerDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    greeting_title: str = Field(..., alias="greetingTitle")
    subtitle: str
    active_channels_count: int = Field(..., alias="activeChannelsCount")
    parameter_version: str = Field(..., alias="parameterVersion")


class TimelinePointDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    axis_label: str = Field(..., alias="axisLabel")
    date_label: str = Field(..., alias="dateLabel")
    messages_count: int = Field(..., alias="messagesCount")
    flagged_clusters_count: int = Field(..., alias="flaggedClustersCount")
    formatted_headline: str = Field(..., alias="formattedHeadline")
    normalized_y: int = Field(..., alias="normalizedY")
    is_highlighted: bool = Field(default=False, alias="isHighlighted")


class ActivityTimelineDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    subtitle: str
    range: TimeRangeOption
    points: list[TimelinePointDto]


class DashboardOverviewDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    range: TimeRangeOption
    banner: DashboardBannerDto
    timeline: ActivityTimelineDto
    stats: list[StatCardMetricDto]


class SidebarPulseBarDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    height_percent: int = Field(..., alias="heightPercent")
    is_highlighted: bool = Field(default=False, alias="isHighlighted")
    tag: str | None = None


class QuickSummaryCardDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    value: str
    target_path: str = Field(..., alias="targetPath")


class CalendarDayDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    day_short: str = Field(..., alias="dayShort")
    date_number: int = Field(..., alias="dateNumber")
    is_active: bool = Field(default=False, alias="isActive")
    has_alert_dot: bool = Field(default=False, alias="hasAlertDot")


class AuditGaugeDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    period_label: str = Field(..., alias="periodLabel")
    primary_percentage: int = Field(..., alias="primaryPercentage")
    primary_label: str = Field(..., alias="primaryLabel")
    secondary_percentage: int = Field(..., alias="secondaryPercentage")
    secondary_label: str = Field(..., alias="secondaryLabel")


class UserProfileSummaryDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(..., alias="fullName")
    role_label: str = Field(..., alias="roleLabel")
    role: UserRole
    initials: str


class ShellSummaryDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    last_collection_label: str = Field(..., alias="lastCollectionLabel")
    unread_alerts_count: int = Field(..., alias="unreadAlertsCount")
    user: UserProfileSummaryDto
    pulse_bars: list[SidebarPulseBarDto] = Field(..., alias="pulseBars")
    quick_cards: list[QuickSummaryCardDto] = Field(..., alias="quickCards")
    calendar_days: list[CalendarDayDto] = Field(..., alias="calendarDays")
    audit: AuditGaugeDto
