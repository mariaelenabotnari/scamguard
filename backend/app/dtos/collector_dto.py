"""DTOs for Telegram message collection, text normalisation, and data minimisation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DetectedLanguage = Literal["RO", "RU", "MIXED", "OTHER"]
CollectionRunStatus = Literal["completed", "partial", "failed"]


class RawTelegramPostDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    channel_id: str = Field(..., alias="channelId")
    telegram_message_id: int = Field(..., alias="telegramMessageId")
    raw_text: str = Field(..., alias="rawText")
    posted_at: str = Field(..., alias="postedAt")
    forwarded_from: str | None = Field(default=None, alias="forwardedFrom")
    view_count: int = Field(default=0, alias="viewCount")
    has_media: bool = Field(default=False, alias="hasMedia")
    media_type: str | None = Field(default=None, alias="mediaType")
    forwards: int = Field(default=0, alias="forwards")
    edit_date: str | None = Field(default=None, alias="editDate")
    grouped_id: str | None = Field(default=None, alias="groupedId")
    is_forward: bool = Field(default=False, alias="isForward")
    forward_source_channel_id: str | None = Field(default=None, alias="forwardSourceChannelId")
    forward_source_name: str | None = Field(default=None, alias="forwardSourceName")
    forward_source_date: str | None = Field(default=None, alias="forwardSourceDate")
    reply_to_id: int | None = Field(default=None, alias="replyToId")
    post_link: str | None = Field(default=None, alias="postLink")
    first_seen_at: str | None = Field(default=None, alias="firstSeenAt")
    last_seen_at: str | None = Field(default=None, alias="lastSeenAt")


class NormalisedTextDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    normalised_text: str = Field(..., alias="normalisedText")
    transliterated_text: str = Field(default="", alias="transliteratedText")
    text_hash: str = Field(..., alias="textHash")
    text_model: str = Field(default="", alias="textModel")
    text_display: str = Field(default="", alias="textDisplay")
    language: DetectedLanguage
    is_mixed_script: bool = Field(default=False, alias="isMixedScript")


class StoredMessageDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    channel_id: str = Field(..., alias="channelId")
    telegram_message_id: int = Field(..., alias="telegramMessageId")
    posted_at: str = Field(..., alias="postedAt")
    forwarded_from: str | None = Field(default=None, alias="forwardedFrom")
    view_count: int = Field(..., alias="viewCount")
    language: DetectedLanguage
    is_deleted_at_source: bool = Field(default=False, alias="isDeletedAtSource")
    raw_text: str | None = Field(default=None, alias="rawText")
    normalised_text: str = Field(..., alias="normalisedText")
    text_hash: str = Field(..., alias="textHash")
    text_model: str | None = Field(default=None, alias="textModel")
    text_display: str | None = Field(default=None, alias="textDisplay")
    is_mixed_script: bool = Field(default=False, alias="isMixedScript")
    has_media: bool = Field(default=False, alias="hasMedia")
    media_type: str | None = Field(default=None, alias="mediaType")
    forwards: int = Field(default=0, alias="forwards")
    edit_date: str | None = Field(default=None, alias="editDate")
    grouped_id: str | None = Field(default=None, alias="groupedId")
    is_forward: bool = Field(default=False, alias="isForward")
    forward_source_channel_id: str | None = Field(default=None, alias="forwardSourceChannelId")
    forward_source_name: str | None = Field(default=None, alias="forwardSourceName")
    forward_source_date: str | None = Field(default=None, alias="forwardSourceDate")
    reply_to_id: int | None = Field(default=None, alias="replyToId")
    post_link: str | None = Field(default=None, alias="postLink")
    first_seen_at: str | None = Field(default=None, alias="firstSeenAt")
    last_seen_at: str | None = Field(default=None, alias="lastSeenAt")
    deleted_at: str | None = Field(default=None, alias="deletedAt")
    skip_similarity: bool = Field(default=False, alias="skipSimilarity")


class CollectionRunDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    channel_id: str | None = Field(default=None, alias="channelId")
    started_at: str = Field(..., alias="startedAt")
    finished_at: str = Field(..., alias="finishedAt")
    status: CollectionRunStatus
    channels_polled: int = Field(..., alias="channelsPolled")
    messages_saved: int = Field(..., alias="messagesSaved")
    flood_waits_count: int = Field(default=0, alias="floodWaitsCount")
    error_message: str | None = Field(default=None, alias="errorMessage")


class ResolvedChannelDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    telegram_channel_id: int = Field(..., alias="telegramChannelId")
    handle: str
    title: str
    subscribers_count: int = Field(default=0, alias="subscribersCount")
    language_guess: str = Field(default="RO", alias="languageGuess")
    is_public: bool = Field(default=True, alias="isPublic")


class PurgeDeletedPostInputDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(..., alias="messageId")


class PurgeDeletedPostReceiptDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str = Field(..., alias="messageId")
    raw_text_purged: bool = Field(..., alias="rawTextPurged")
    retained_text_hash: str = Field(..., alias="retainedTextHash")
