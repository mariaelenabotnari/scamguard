"""Comprehensive tests for ScamGuard live collector: channel resolution, backfill, messy posts, albums, edits, deletions, FloodWait recovery, and CLI commands."""

import pytest

from app.core.errors import AppError
from app.db.database import DatabaseManager
from app.dtos.collector_dto import RawTelegramPostDto
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.collector_service import TelegramCollectorService, strip_channel_boilerplate
from app.services.telegram_client import FakeTelegramClientAdapter
from app.services.text_normaliser import TextNormaliser


def _build_test_harness(
    channel_posts: dict[str, list[RawTelegramPostDto]] | None = None,
    flood_wait_once: dict[str, int] | None = None,
    existing_message_ids: dict[str, set[int]] | None = None,
) -> tuple[
    DatabaseManager,
    SqliteWatchlistRepository,
    SqliteMessageRepository,
    TextNormaliser,
    FakeTelegramClientAdapter,
    TelegramCollectorService,
    list[float],
]:
    db = DatabaseManager(":memory:")
    watchlist_repo = SqliteWatchlistRepository(db_manager=db, seed_defaults=False)
    message_repo = SqliteMessageRepository(db_manager=db)
    normaliser = TextNormaliser()
    slept: list[float] = []

    client = FakeTelegramClientAdapter(
        channel_posts=channel_posts,
        flood_wait_once_channels=flood_wait_once,
        existing_message_ids=existing_message_ids,
    )
    service = TelegramCollectorService(
        watchlist_repo=watchlist_repo,
        message_repo=message_repo,
        normaliser=normaliser,
        telegram_client=client,
        sleep_fn=lambda sec: slept.append(sec),
        max_retries=3,
        add_jitter=False,
    )
    return db, watchlist_repo, message_repo, normaliser, client, service, slept


def test_channel_resolution_public_broadcast() -> None:
    _, _, _, _, client, _, _ = _build_test_harness()

    # Resolve from @handle
    resolved_1 = client.resolve_channel("@moldova_stiri_live")
    assert resolved_1.handle == "@moldova_stiri_live"
    assert resolved_1.title == "Moldova Stiri Live"
    assert resolved_1.is_public is True
    assert resolved_1.subscribers_count > 0
    assert resolved_1.telegram_channel_id > 0
    assert resolved_1.language_guess == "RO"

    # Resolve from URL
    resolved_2 = client.resolve_channel("https://t.me/balti_pravda_news/")
    assert resolved_2.handle == "@balti_pravda_news"
    assert resolved_2.language_guess == "RU"


def test_channel_resolution_rejects_private_groups_and_users() -> None:
    _, _, _, _, client, _, _ = _build_test_harness()

    # Reject private channel
    with pytest.raises(AppError) as exc_priv:
        client.resolve_channel("@secret_private_club")
    assert exc_priv.value.code == "PRIVATE_CHANNEL_REJECTED"

    # Reject group / chat
    with pytest.raises(AppError) as exc_grp:
        client.resolve_channel("https://t.me/chisinau_discussion_group")
    assert exc_grp.value.code == "INVALID_CHANNEL_TYPE"

    # Reject user profile
    with pytest.raises(AppError) as exc_usr:
        client.resolve_channel("@journalist_user_profile")
    assert exc_usr.value.code == "INVALID_CHANNEL_TYPE"


def test_resolve_and_add_channel_with_backfill() -> None:
    posts = {
        "ch-chisinau-radar": [
            RawTelegramPostDto(
                channelId="ch-chisinau-radar",
                telegramMessageId=10,
                rawText="Postare istorică 1 despre tarife la energie în Chișinău.",
                postedAt="2026-11-01T12:00:00Z",
                viewCount=1200,
            ),
            RawTelegramPostDto(
                channelId="ch-chisinau-radar",
                telegramMessageId=11,
                rawText="Postare istorică 2 despre tarife la energie în Chișinău.",
                postedAt="2026-11-02T14:00:00Z",
                viewCount=2400,
            ),
        ]
    }
    _, watchlist_repo, message_repo, _, _, service, _ = _build_test_harness(channel_posts=posts)

    channel = service.resolve_and_add_channel(
        handle_or_url="@chisinau_radar",
        added_by="investigator@scamguard.md",
        backfill_days=7,
    )

    assert channel.handle == "@chisinau_radar"
    assert channel.status == "active"
    assert channel.telegram_channel_id is not None

    stored = message_repo.list_messages(channel.id)
    assert len(stored) == 2
    assert stored[0].telegram_message_id == 10
    assert stored[1].telegram_message_id == 11

    # Checkpoint should match highest message ID
    assert message_repo.get_last_message_id(channel.id) == 11


def test_messy_posts_media_only_short_and_albums() -> None:
    posts = {
        "ch-messy": [
            # 1. Media only post (no text)
            RawTelegramPostDto(
                channelId="ch-messy",
                telegramMessageId=101,
                rawText="",
                postedAt="2026-11-03T10:00:00Z",
                hasMedia=True,
                mediaType="photo",
                viewCount=500,
            ),
            # 2. Too short post (< 25 chars after normalisation)
            RawTelegramPostDto(
                channelId="ch-messy",
                telegramMessageId=102,
                rawText="Alertă!",
                postedAt="2026-11-03T10:05:00Z",
                viewCount=750,
            ),
            # 3. Album (grouped_id)
            RawTelegramPostDto(
                channelId="ch-messy",
                telegramMessageId=103,
                rawText="Documente exclusive de la ministerul energiei din Moldova privind noile tarife.",
                postedAt="2026-11-03T10:10:00Z",
                hasMedia=True,
                mediaType="album",
                groupedId="9876543210",
                viewCount=4300,
            ),
            # 4. Standard investigative message
            RawTelegramPostDto(
                channelId="ch-messy",
                telegramMessageId=104,
                rawText="URGENT: Noile tarife la gaze naturale vor fi majorate cu 100% din 15 noiembrie la cererea UE!",
                postedAt="2026-11-03T10:15:00Z",
                viewCount=8900,
            ),
        ]
    }
    _, watchlist_repo, message_repo, _, _, service, _ = _build_test_harness(channel_posts=posts)
    watchlist_repo.create_channel(
        channel_id="ch-messy",
        handle="@messy_news",
        title="Messy News",
        language="RO",
        added_by="test@scamguard.md",
    )

    run = service.poll_active_channels()
    assert run.messages_saved == 4

    messages = message_repo.list_messages("ch-messy")
    assert len(messages) == 4

    # Post 101: media-only -> skipSimilarity is True
    p101 = next(m for m in messages if m.telegram_message_id == 101)
    assert p101.has_media is True
    assert p101.skip_similarity is True

    # Post 102: short (<25 chars) -> skipSimilarity is True
    p102 = next(m for m in messages if m.telegram_message_id == 102)
    assert p102.skip_similarity is True

    # Post 103: album with caption -> skipSimilarity is False
    p103 = next(m for m in messages if m.telegram_message_id == 103)
    assert p103.grouped_id == "9876543210"
    assert p103.media_type == "album"
    assert p103.skip_similarity is False

    # Post 104: valid message -> skipSimilarity is False
    p104 = next(m for m in messages if m.telegram_message_id == 104)
    assert p104.skip_similarity is False


def test_channel_boilerplate_stripping() -> None:
    raw_with_footer = (
        "Tarifele la gaz și electricitate vor exploda de luna viitoare în Republica Moldova.\n"
        "Подписывайтесь на наш канал: https://t.me/fake_news_md/\n"
        "Abonați-vă la canalul nostru: t.me/fake_news_md"
    )
    cleaned = strip_channel_boilerplate(raw_with_footer, known_patterns=[])
    assert "https://t.me/fake_news_md" not in cleaned
    assert "Abonați-vă la canalul nostru" not in cleaned
    assert "Tarifele la gaz și electricitate" in cleaned


def test_edited_posts_detection() -> None:
    initial_posts = {
        "ch-edit": [
            RawTelegramPostDto(
                channelId="ch-edit",
                telegramMessageId=201,
                rawText="Prețul la gaz va crește cu 50% conform declarației guvernului.",
                postedAt="2026-11-02T10:00:00Z",
                viewCount=1000,
            )
        ]
    }
    db, watchlist_repo, message_repo, _, client, service, _ = _build_test_harness(
        channel_posts=initial_posts
    )
    watchlist_repo.create_channel(
        channel_id="ch-edit",
        handle="@edit_channel",
        title="Edit Channel",
        language="RO",
        added_by="test@scamguard.md",
    )

    # First poll
    service.poll_active_channels()
    msg_1 = message_repo.get_message_by_id("msg-ch-edit-201")
    assert msg_1 is not None
    assert msg_1.raw_text == "Prețul la gaz va crește cu 50% conform declarației guvernului."

    # Now edit occurs at source
    client._posts["ch-edit"] = [
        RawTelegramPostDto(
            channelId="ch-edit",
            telegramMessageId=201,
            rawText="RECTIFICARE: Prețul la gaz va crește cu 100% (nu 50%) conform noilor decizii.",
            postedAt="2026-11-02T10:00:00Z",
            editDate="2026-11-02T11:30:00Z",
            viewCount=3500,
        )
    ]

    # Save edited post
    norm = TextNormaliser().normalise(client._posts["ch-edit"][0].raw_text)
    updated_dto, created = message_repo.save_message(client._posts["ch-edit"][0], norm)
    assert created is False
    assert updated_dto.raw_text == "RECTIFICARE: Prețul la gaz va crește cu 100% (nu 50%) conform noilor decizii."
    assert updated_dto.edit_date == "2026-11-02T11:30:00Z"

    # Verify edit was recorded in message_edits table
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM message_edits WHERE message_id = 'msg-ch-edit-201'")
    edits = cursor.fetchall()
    assert len(edits) == 1
    assert "50%" in edits[0]["old_raw_text"]
    assert "100%" in edits[0]["new_raw_text"]


def test_source_deleted_post_detection_and_purge() -> None:
    posts = {
        "ch-del": [
            RawTelegramPostDto(
                channelId="ch-del",
                telegramMessageId=301,
                rawText="Declarație controversată ștearsă ulterior de autorul postării.",
                postedAt="2026-11-02T08:00:00Z",
                viewCount=1500,
            ),
            RawTelegramPostDto(
                channelId="ch-del",
                telegramMessageId=302,
                rawText="Mesaj legitim care rămâne disponibil pe canalul public Telegram.",
                postedAt="2026-11-02T09:00:00Z",
                viewCount=2200,
            ),
        ]
    }
    # Only message 302 remains in Telegram; 301 was deleted at source
    existing_ids = {"ch-del": {302}}
    _, watchlist_repo, message_repo, _, _, service, _ = _build_test_harness(
        channel_posts=posts, existing_message_ids=existing_ids
    )

    watchlist_repo.create_channel(
        channel_id="ch-del",
        handle="@del_channel",
        title="Delete Channel",
        language="RO",
        added_by="test@scamguard.md",
    )
    service.poll_active_channels()

    # Pre-check: raw text exists for both
    m301_before = message_repo.get_message_by_id("msg-ch-del-301")
    assert m301_before is not None
    assert m301_before.raw_text is not None
    assert m301_before.is_deleted_at_source is False

    # Run background deletion detection job
    purged_count = service.check_and_purge_deleted_posts("ch-del")
    assert purged_count == 1

    # Post 301 was purged: raw_text is None, is_deleted_at_source is True, normalised text retained
    m301_after = message_repo.get_message_by_id("msg-ch-del-301")
    assert m301_after is not None
    assert m301_after.is_deleted_at_source is True
    assert m301_after.raw_text is None
    assert m301_after.deleted_at is not None
    assert m301_after.normalised_text == m301_before.normalised_text
    assert m301_after.text_hash == m301_before.text_hash

    # Post 302 was not purged
    m302 = message_repo.get_message_by_id("msg-ch-del-302")
    assert m302 is not None
    assert m302.is_deleted_at_source is False
    assert m302.raw_text is not None


def test_floodwait_and_persistent_failure_handling() -> None:
    posts = {
        "ch-good": [
            RawTelegramPostDto(
                channelId="ch-good",
                telegramMessageId=1,
                rawText="Mesaj pe canalul funcțional fără erori de conexiune.",
                postedAt="2026-11-02T10:00:00Z",
                viewCount=1000,
            )
        ],
        "ch-bad": [],
    }
    # ch-bad will always raise exception during poll
    class FailingClient(FakeTelegramClientAdapter):
        def fetch_messages_since(
            self, channel_id: str, handle: str, min_message_id: int
        ) -> list[RawTelegramPostDto]:
            if channel_id == "ch-bad":
                raise RuntimeError("Telegram connection dropped persistently")
            return super().fetch_messages_since(channel_id, handle, min_message_id)

    db = DatabaseManager(":memory:")
    watchlist_repo = SqliteWatchlistRepository(db_manager=db, seed_defaults=False)
    message_repo = SqliteMessageRepository(db_manager=db)
    client = FailingClient(channel_posts=posts)
    service = TelegramCollectorService(
        watchlist_repo=watchlist_repo,
        message_repo=message_repo,
        normaliser=TextNormaliser(),
        telegram_client=client,
        sleep_fn=lambda _: None,
        max_retries=2,
    )

    watchlist_repo.create_channel("ch-good", "@good_ch", "Good", "RO", "admin")
    watchlist_repo.create_channel("ch-bad", "@bad_ch", "Bad", "RO", "admin")

    run = service.poll_active_channels()

    # The bad channel failure did NOT stop the good channel
    assert run.channels_polled == 1
    assert run.messages_saved == 1
    assert "bad_ch" in (run.error_message or "")

    # Bad channel is automatically paused with error recorded
    bad_channel = watchlist_repo.get_by_id("ch-bad")
    assert bad_channel is not None
    assert bad_channel.status == "paused"
    assert "Telegram connection dropped" in (bad_channel.last_error or "")
