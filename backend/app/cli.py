"""Command Line Interface (CLI) for ScamGuard maintenance, auth, and data tasks."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from app.core.config import get_settings


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
            resolved_phone = input("Enter your phone number in international format (+373...): ").strip()
        await client.start(phone=resolved_phone)
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


if __name__ == "__main__":
    main()
