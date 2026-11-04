"""Timeline service for dynamic propagation timeline, LCS token diffs, and local time conversion."""

import difflib
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.dtos.cluster_dto import (
    ClusterChannelAvatarDto,
    ClusterChannelParticipantDto,
    ClusterDetailDto,
    ClusterMessageComparisonDto,
    ClusterMessagePostDto,
    ClusterSummaryDto,
    DiffTokenDto,
)

logger = logging.getLogger(__name__)

CHISINAU_TZ = ZoneInfo("Europe/Chisinau")


def parse_utc_timestamp(ts_str: str) -> datetime:
    """Parses standard ISO or SQL UTC timestamps into a timezone-aware UTC datetime."""
    clean_ts = ts_str.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_ts)
    except ValueError:
        try:
            dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_chisinau_datetime(dt_utc: datetime) -> str:
    """Formats a UTC datetime in Europe/Chisinau timezone as YYYY-MM-DD HH:MM:SS."""
    return dt_utc.astimezone(CHISINAU_TZ).strftime("%Y-%m-%d %H:%M:%S")


def format_chisinau_time(dt_utc: datetime) -> str:
    """Formats a UTC datetime in Europe/Chisinau timezone as HH:MM:SS."""
    return dt_utc.astimezone(CHISINAU_TZ).strftime("%H:%M:%S")


def compute_lcs_word_diff(anchor_text: str, current_text: str) -> list[DiffTokenDto]:
    """Computes word-level Longest Common Subsequence (LCS) diff between anchor text and comparison text."""
    if not current_text:
        return []

    if not anchor_text or anchor_text.strip() == current_text.strip():
        return [DiffTokenDto(text=current_text, isChanged=False)]

    anchor_words = anchor_text.split()
    current_words = current_text.split()

    matcher = difflib.SequenceMatcher(None, anchor_words, current_words)
    tokens: list[DiffTokenDto] = []

    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if j1 == j2:
            continue
        chunk = " ".join(current_words[j1:j2])
        is_changed = tag in ("replace", "insert")
        tokens.append(DiffTokenDto(text=chunk, isChanged=is_changed))

    # Join tokens with space padding for natural reading
    result: list[DiffTokenDto] = []
    for idx, t in enumerate(tokens):
        text = t.text if idx == len(tokens) - 1 else t.text + " "
        result.append(DiffTokenDto(text=text, isChanged=t.is_changed))

    return result


def build_dynamic_timeline(
    summary: ClusterSummaryDto,
    raw_message_records: list[dict[str, object]],
) -> ClusterDetailDto:
    """Calculates propagation timeline, anchor offsets, and word diffs for a cluster.

    Anchor t_0 is the earliest message by posted_at timestamp.
    All delaySeconds are computed dynamically relative to t_0.
    """
    if not raw_message_records:
        return ClusterDetailDto(
            **summary.model_dump(by_alias=True),
            summary=summary,
            posts=[],
            messages=[],
        )

    # Sort messages chronologically
    sorted_records = sorted(
        raw_message_records,
        key=lambda r: (
            parse_utc_timestamp(str(r["posted_at"])),
            str(r["message_id"]),
        ),
    )

    anchor_rec = sorted_records[0]
    t0_dt = parse_utc_timestamp(str(anchor_rec["posted_at"]))
    last_dt = parse_utc_timestamp(str(sorted_records[-1]["posted_at"]))

    span_minutes = max(1, int(round((last_dt - t0_dt).total_seconds() / 60)))

    anchor_norm = str(anchor_rec.get("normalised_text", ""))
    anchor_raw = anchor_rec.get("raw_text")
    anchor_base_text = str(anchor_raw) if anchor_raw is not None else anchor_norm

    posts: list[ClusterMessagePostDto] = []
    messages: list[ClusterMessageComparisonDto] = []
    participants: list[ClusterChannelParticipantDto] = []
    seen_channels: set[str] = set()
    avatars: list[ClusterChannelAvatarDto] = []

    for idx, rec in enumerate(sorted_records):
        msg_id = str(rec["message_id"])
        ch_id = str(rec["channel_id"])
        handle = str(rec.get("handle") or f"@{ch_id}")
        title = str(rec.get("title") or ch_id)
        posted_str = str(rec["posted_at"])
        dt_utc = parse_utc_timestamp(posted_str)

        delay_sec = max(0, int((dt_utc - t0_dt).total_seconds())) if idx > 0 else 0
        similarity = float(str(rec.get("similarity_score", 1.0)))
        if idx == 0:
            similarity = 1.0

        is_deleted = bool(int(str(rec.get("is_deleted_at_source", 0))))
        raw_val = rec.get("raw_text")
        raw_text = str(raw_val) if raw_val is not None else None
        norm_text = str(rec.get("normalised_text", ""))
        text_hash = str(rec.get("text_hash", ""))
        tg_id = rec.get("telegram_message_id", 1)

        comp_text = raw_text if raw_text is not None else norm_text
        diff_tokens = (
            [DiffTokenDto(text=comp_text, isChanged=False)]
            if idx == 0
            else compute_lcs_word_diff(anchor_base_text, comp_text)
        )

        display_posted_at = format_chisinau_datetime(dt_utc)
        clean_handle = handle.lstrip("@")
        telegram_url = f"https://t.me/{clean_handle}/{tg_id}"

        # Build post DTO for frontend ClusterComparePage
        posts.append(
            ClusterMessagePostDto(
                id=msg_id,
                channelId=ch_id,
                handle=handle,
                channelTitle=title,
                postedAt=display_posted_at,
                delaySeconds=delay_sec,
                similarityToAnchor=similarity,
                isDeletedAtSource=is_deleted,
                originalUrl=telegram_url,
                rawText=raw_text,
                normalizedText=norm_text,
                textHash=text_hash,
                diffTokens=diff_tokens,
            )
        )

        # Build legacy message comparison DTO
        diff_words = [
            w for w in norm_text.split() if w not in set(anchor_norm.split()) and len(w) > 2
        ]
        messages.append(
            ClusterMessageComparisonDto(
                messageId=msg_id,
                channelId=ch_id,
                handle=handle,
                title=title,
                postedAt=posted_str,
                delaySeconds=delay_sec,
                similarityScore=similarity,
                isDeleted=is_deleted,
                rawText=raw_text,
                normalisedText=norm_text,
                normalisedHash=text_hash,
                telegramUrl=telegram_url,
                changedPhrases=diff_words[:5],
            )
        )

        # Build participant DTO for clusters list
        words = [w for w in title.replace("@", "").split() if w]
        initials = (
            (words[0][0] + (words[1][0] if len(words) > 1 else words[0][-1])).upper()
            if words
            else "CH"
        )

        participants.append(
            ClusterChannelParticipantDto(
                channelId=ch_id,
                handle=handle,
                title=title,
                initials=initials,
                postedAt=format_chisinau_time(dt_utc),
                delaySeconds=delay_sec,
                similarityScore=similarity,
            )
        )

        if ch_id not in seen_channels:
            seen_channels.add(ch_id)
            avatars.append(
                ClusterChannelAvatarDto(
                    channelId=ch_id,
                    handle=handle,
                    title=title,
                    initials=initials,
                )
            )

    # Update summary with computed dynamic timeline metrics
    first_display = format_chisinau_datetime(t0_dt)
    last_display = format_chisinau_datetime(last_dt)

    updated_summary = summary.model_copy(
        update={
            "span_minutes": span_minutes,
            "window_minutes": span_minutes,
            "first_posted_at": first_display,
            "last_posted_at": last_display,
            "channels_count": len(seen_channels),
            "messages_count": len(posts),
            "channels": avatars,
            "participants": participants,
        }
    )

    return ClusterDetailDto(
        **updated_summary.model_dump(by_alias=True),
        summary=updated_summary,
        posts=posts,
        messages=messages,
    )
