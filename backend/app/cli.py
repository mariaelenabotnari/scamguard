"""Command Line Interface (CLI) for ScamGuard maintenance, auth, and data tasks."""

import argparse
import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.dependencies import get_analysis_pipeline_service
from app.db.database import get_database_manager
from app.repositories.message_repository import SqliteMessageRepository
from app.repositories.watchlist_repository import SqliteWatchlistRepository
from app.services.collector_service import TelegramCollectorService
from app.services.telegram_client import (
    FakeTelegramClientAdapter,
    ITelegramClientAdapter,
    TelethonClientAdapter,
)
from app.services.text_normaliser import TextNormaliser

reconfig_stdout = getattr(sys.stdout, "reconfigure", None)
if callable(reconfig_stdout):
    try:
        reconfig_stdout(encoding="utf-8")
    except Exception:
        pass

reconfig_stderr = getattr(sys.stderr, "reconfigure", None)
if callable(reconfig_stderr):
    try:
        reconfig_stderr(encoding="utf-8")
    except Exception:
        pass


async def run_telegram_login(
    api_id: int | None = None,
    api_hash: str | None = None,
    phone: str | None = None,
    session_path: str | None = None,
) -> None:
    """Interactively log in to Telegram via Telethon and persist session."""
    try:
        from telethon import TelegramClient
    except ImportError:
        print("❌ Telethon is not installed. Install with: pip install 'telethon>=1.36.0'")
        sys.exit(1)

    settings = get_settings()
    resolved_api_id = api_id or settings.telegram_api_id
    resolved_api_hash = api_hash or settings.telegram_api_hash
    resolved_phone = phone or settings.telegram_phone
    resolved_session_path = session_path or settings.telegram_session_path

    if not resolved_api_id:
        val = input("Enter your Telegram API ID (from my.telegram.org): ").strip()
        if not val.isdigit():
            print("❌ Invalid API ID. Must be an integer.")
            sys.exit(1)
        resolved_api_id = int(val)

    if not resolved_api_hash:
        resolved_api_hash = input("Enter your Telegram API Hash: ").strip()
        if not resolved_api_hash:
            print("❌ API Hash cannot be empty.")
            sys.exit(1)

    # Ensure session directory exists
    session_file_path = Path(resolved_session_path).resolve()
    session_file_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n------------------------------------------------------------")
    print("🔒 ScamGuard Telegram MTProto Client Authentication")
    print(f"Session path: {session_file_path}.session")
    print("------------------------------------------------------------\n")

    client = TelegramClient(str(session_file_path), resolved_api_id, resolved_api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        if not resolved_phone:
            resolved_phone = input("Enter your phone number in international format (e.g. +37362005858): ").strip()
        if not resolved_phone.startswith("+"):
            if len(resolved_phone) == 8 and resolved_phone.startswith(("6", "7", "2")):
                resolved_phone = f"+373{resolved_phone}"
            else:
                resolved_phone = f"+{resolved_phone}"
        print(f"Connecting with phone number: {resolved_phone}")
        try:
            await client.start(phone=resolved_phone)
        except Exception as exc:
            print(f"\n❌ Telegram authentication error: {exc}")
            print("Please ensure your number includes the full country code (e.g. +373 for Moldova, +40 for Romania).\n")
            sys.exit(1)
    else:
        print("ℹ️ Existing session is already authorized.")

    me = await client.get_me()
    username = f"@{me.username}" if me.username else me.phone
    name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    print("\n------------------------------------------------------------")
    print(f"✅ Successfully authenticated as {name} ({username})")
    print(f"Session file saved: {session_file_path}.session")
    print("ScamGuard collector can now ingest public channels in real-time.")
    print("------------------------------------------------------------\n")
    await client.disconnect()


async def check_session_status() -> tuple[bool, str]:
    """Inspects the Telegram session file and returns its connectivity status."""
    settings = get_settings()
    session_path = Path(settings.telegram_session_path).resolve()
    full_session_file = session_path.with_suffix(".session")

    if not settings.telegram_api_id or not settings.telegram_api_hash:
        return False, "TELEGRAM_API_ID or TELEGRAM_API_HASH not configured in environment"

    if not full_session_file.exists():
        return False, f"Session file not found at {full_session_file}. Run 'python -m app.cli telegram-login'"

    try:
        from telethon import TelegramClient

        client = TelegramClient(
            str(session_path), settings.telegram_api_id, settings.telegram_api_hash, timeout=5
        )
        await asyncio.wait_for(client.connect(), timeout=4.0)
        is_auth = await client.is_user_authorized()
        await client.disconnect()
        if is_auth:
            return True, f"Telegram MTProto session authorized ({full_session_file})"
        return False, f"Telegram session at {full_session_file} has expired. Re-run 'python -m app.cli telegram-login'"
    except TimeoutError:
        return False, f"Session file exists at {full_session_file}, but connection to Telegram timed out"
    except Exception as exc:
        return False, f"Error verifying Telegram session: {exc}"


def _get_collector() -> TelegramCollectorService:
    settings = get_settings()
    db_manager = get_database_manager()
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    message_repo = SqliteMessageRepository(db_manager=db_manager)
    normaliser = TextNormaliser()

    session_file = Path(settings.telegram_session_path).resolve().with_suffix(".session")
    client: ITelegramClientAdapter
    if settings.telegram_api_id and settings.telegram_api_hash and session_file.exists():
        client = TelethonClientAdapter(
            session_path=settings.telegram_session_path,
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
        )
    else:
        client = FakeTelegramClientAdapter()

    analysis_service = get_analysis_pipeline_service(db_manager=db_manager)

    return TelegramCollectorService(
        watchlist_repo=watchlist_repo,
        message_repo=message_repo,
        normaliser=normaliser,
        telegram_client=client,
        analysis_pipeline=analysis_service,
    )


def run_analyse() -> None:
    db_manager = get_database_manager()
    analysis_service = get_analysis_pipeline_service(db_manager=db_manager)
    print(
        "[*] Running analysis pipeline (normalise -> similarity -> clustering -> narrative -> scoring -> alerts)..."
    )
    res = analysis_service.run_analysis_pipeline()
    print(
        f"[OK] Pipeline {res.pipeline_run_id} completed: "
        f"{res.clusters_detected} clusters detected, {res.channels_scored} channels scored, "
        f"{res.alerts_generated} alerts generated (parameters: {res.parameter_version})."
    )


def run_collect(channel_handle: str, days: int = 7) -> None:
    collector = _get_collector()
    clean_handle = channel_handle.strip()
    if not clean_handle.startswith("@") and "t.me" not in clean_handle:
        clean_handle = f"@{clean_handle}"

    db_manager = get_database_manager()
    watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
    channel = watchlist_repo.get_by_handle(clean_handle)

    if channel is None:
        print(f"[*] Channel {clean_handle} not on watch list. Resolving and adding...")
        try:
            channel = collector.resolve_and_add_channel(
                clean_handle, added_by="admin-cli", backfill_days=days
            )
            print(
                f"[OK] Added channel '{channel.title}' ({channel.handle}) with {channel.subscribers_count} subscribers."
            )
        except Exception as exc:
            print(f"[ERROR] Failed to add channel {clean_handle}: {exc}")
            sys.exit(1)
    else:
        print(f"[*] Backfilling channel '{channel.title}' ({channel.handle}) for last {days} days...")
        run = collector.backfill_channel(channel.id, days=days)
        print(
            f"[OK] Collection status: {run.status} | Messages saved: {run.messages_saved} | Flood waits: {run.flood_waits_count}"
        )
        if run.error_message:
            print(f"[WARN] Errors: {run.error_message}")


def run_collect_all() -> None:
    collector = _get_collector()
    print("[*] Running collection across all active channels...")
    run = collector.poll_active_channels()
    print(
        f"[OK] Collection status: {run.status} | Channels polled: {run.channels_polled} | Messages saved: {run.messages_saved} | Flood waits: {run.flood_waits_count}"
    )
    if run.error_message:
        print(f"[WARN] Errors: {run.error_message}")


def run_check_deleted(channel_handle: str | None = None) -> None:
    collector = _get_collector()
    channel_id = None
    if channel_handle:
        clean_handle = channel_handle.strip()
        if not clean_handle.startswith("@") and "t.me" not in clean_handle:
            clean_handle = f"@{clean_handle}"
        db_manager = get_database_manager()
        watchlist_repo = SqliteWatchlistRepository(db_manager=db_manager)
        channel = watchlist_repo.get_by_handle(clean_handle)
        if not channel:
            print(f"[ERROR] Channel {clean_handle} not found in database.")
            sys.exit(1)
        channel_id = channel.id

    print("[*] Checking for messages deleted at source on Telegram...")
    purged = collector.check_and_purge_deleted_posts(channel_id=channel_id)
    print(f"[OK] Check completed. Purged raw text for {purged} deleted post(s).")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="ScamGuard Administrative and Ingestion CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # telegram-login command
    login_parser = subparsers.add_parser(
        "telegram-login", help="Authenticate with Telegram MTProto API and save session"
    )
    login_parser.add_argument("--api-id", type=int, help="Telegram API ID")
    login_parser.add_argument("--api-hash", type=str, help="Telegram API Hash")
    login_parser.add_argument("--phone", type=str, help="Telegram Account Phone Number")
    login_parser.add_argument("--session-path", type=str, help="Output path for session file")

    # session-status command
    subparsers.add_parser("session-status", help="Check if Telegram session is authorized")

    # collect command
    collect_parser = subparsers.add_parser(
        "collect", help="Collect messages from a single Telegram channel"
    )
    collect_parser.add_argument("--channel", type=str, required=True, help="Channel handle or URL (@name)")
    collect_parser.add_argument("--days", type=int, default=7, help="Number of past days to backfill (default: 7)")

    # collect-all command
    subparsers.add_parser(
        "collect-all", help="Poll new messages from all active channels on the watch list"
    )

    # check-deleted command
    del_parser = subparsers.add_parser(
        "check-deleted", help="Check if recent posts were deleted on Telegram and purge raw text"
    )
    del_parser.add_argument("--channel", type=str, default=None, help="Optional channel handle to check")

    # analyse command
    subparsers.add_parser(
        "analyse",
        help="Run analysis pipeline (similarity, clustering, narratives, scoring, alerts) on collected messages",
    )

    args = parser.parse_args()

    if args.command == "telegram-login":
        asyncio.run(
            run_telegram_login(
                api_id=args.api_id,
                api_hash=args.api_hash,
                phone=args.phone,
                session_path=args.session_path,
            )
        )
    elif args.command == "session-status":
        valid, msg = asyncio.run(check_session_status())
        if valid:
            print(f"[OK] {msg}")
        else:
            print(f"[WARN] {msg}")
            sys.exit(1)
    elif args.command == "collect":
        run_collect(channel_handle=args.channel, days=args.days)
    elif args.command == "collect-all":
        run_collect_all()
    elif args.command == "check-deleted":
        run_check_deleted(channel_handle=args.channel)
    elif args.command == "analyse":
        run_analyse()


if __name__ == "__main__":
    main()
