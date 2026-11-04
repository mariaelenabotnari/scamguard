# Telegram MTProto Credentials & Ingestion Setup Guide

> Project: ScamGuard  
> Branch: `chore/telegram-credentials`  
> Purpose: Detailed instructions for provisioning a dedicated Telegram account, obtaining official MTProto credentials, and authenticating the live collector session.

---

## 1. Security & Account Requirements

> [!IMPORTANT]
> **Use a Dedicated Telegram Account**  
> Do not use your personal Telegram account for automated data collection. Telegram may apply rate limits or temporary flood-wait bans to accounts polling hundreds of public channels. Create or dedicate an independent phone number for this project.

1. Obtain a dedicated SIM card / mobile number (Moldovan or international format, e.g. `+373...`).
2. Log in once on official Telegram mobile/desktop to ensure the account is active.

---

## 2. Obtain Telegram API Credentials

1. Open your browser and go to: [https://my.telegram.org](https://my.telegram.org).
2. Log in using your dedicated Telegram phone number. Enter the confirmation code sent to your Telegram app.
3. Click on **API development tools**.
4. Fill in the application form:
   * **App title**: `ScamGuard Collector` (or your chosen project title).
   * **Short name**: `scamguard`
   * **Platform**: `Web` or `Other`
   * **URL**: can be left blank or `http://localhost`.
5. Submit the form to generate your keys:
   * `api_id`: An integer (e.g. `35433900`).
   * `api_hash`: A 32-character hexadecimal string (e.g. `2701a5b7d59c3f7ed849819b3fff526a`).

---

## 3. Configure Local Environment (`.env`)

Add your credentials to your local `.env` file at the repository root.

```ini
# Telegram Collector (MTProto API - never commit to git)
TELEGRAM_API_ID=35433900
TELEGRAM_API_HASH=2701a5b7d59c3f7ed849819b3fff526a
TELEGRAM_PHONE=+373XXXXXXXX
TELEGRAM_SESSION_PATH=./sessions/scamguard_collector
COLLECTION_INTERVAL_MINUTES=5
```

> [!CAUTION]
> The `.env` file and `./sessions/*.session` files are strictly git-ignored. Never commit credentials, phone numbers, or `.session` files to Git!

---

## 4. Complete Interactive One-Time Login

To establish an authenticated session with Telegram MTProto, execute the interactive login CLI command on your host:

```bash
# From repository root:
cmd /c "set PYTHONPATH=backend && backend\.venv\Scripts\python.exe -m app.cli telegram-login"
```

*Or inside PowerShell:*
```powershell
$env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe -m app.cli telegram-login
```

### What Happens During Login:
1. Telethon connects to Telegram servers using your `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
2. Telegram sends a 5-digit login verification code directly to your Telegram app (or SMS).
3. The CLI prompts: `Please enter the code you received: `
4. If you have Two-Factor Authentication (2FA) enabled, it prompts for your 2FA password.
5. On success, a persistent binary session file is created at:
   `sessions/scamguard_collector.session`
6. The CLI displays:
   ```text
   ✅ Successfully authenticated as Your Name (@your_username)
   Session file saved: .../sessions/scamguard_collector.session
   ```

---

## 5. Verify Session Status

You can verify whether the session is authorized at any time:

```bash
cmd /c "set PYTHONPATH=backend && backend\.venv\Scripts\python.exe -m app.cli session-status"
```

Expected output:
```text
[OK] Telegram MTProto session authorized (...\sessions\scamguard_collector.session)
```

---

## 6. Docker Volume & Startup Check

* **Docker Persistence**: The `docker-compose.yml` mounts `./sessions:/app/sessions`. Once created on the host, the session is immediately available to the `scamguard-backend` container across rebuilds and restarts.
* **Non-Crashing Startup Check**: When the backend starts up, it logs the session status:
  * If valid: `[INFO] Telegram MTProto session file found at ... Collector initialized.`
  * If missing or unauthenticated: `[WARN] Telegram session is missing or unauthenticated (...). Collector will fall back to simulated adapter until configured.`
  The API remains up and accessible even if the session is temporarily missing or needs re-authentication.
