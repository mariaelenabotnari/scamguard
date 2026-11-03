"""Email delivery service with SMTP support and local logging fallback."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings, get_settings

logger = logging.getLogger("scamguard.email")


class EmailService:
    """Sends verification and notification emails via SMTP, falling back to local logging."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def send_verification_email(self, to_email: str, code: str) -> bool:
        """Sends an activation code to the requested email.

        If SMTP credentials are not configured in environment, the code is logged
        to stdout/logger so the user can verify in development or staging.
        """
        host = self._settings.smtp_host
        if not host:
            logger.info(
                "[AUTH EMAIL DISPATCH] Verification code for %s: %s (No SMTP configured)",
                to_email,
                code,
            )
            return False

        try:
            msg = EmailMessage()
            msg["Subject"] = f"Your ScamGuard Verification Code: {code}"
            msg["From"] = self._settings.smtp_from
            msg["To"] = to_email

            text_content = (
                f"Welcome to ScamGuard.\n\n"
                f"Your 6-digit email verification code is: {code}\n\n"
                f"This code will expire in 15 minutes. Enter this code to activate your account."
            )
            msg.set_content(text_content)

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; padding: 24px; color: #1e293b;">
              <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px;">
                <h2 style="color: #4f46e5; margin-top: 0;">ScamGuard Verification</h2>
                <p>Welcome to ScamGuard. Use the verification code below to activate your account and start your investigation workspace:</p>
                <div style="background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 8px; padding: 16px; text-align: center; margin: 24px 0;">
                  <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #4338ca; font-family: monospace;">{code}</span>
                </div>
                <p style="font-size: 13px; color: #64748b;">This code will expire in 15 minutes. If you did not request this account, please ignore this email.</p>
              </div>
            </body>
            </html>
            """
            msg.add_alternative(html_content, subtype="html")

            port = self._settings.smtp_port
            with smtplib.SMTP(host, port, timeout=10) as server:
                if self._settings.smtp_tls:
                    server.starttls()
                if self._settings.smtp_user and self._settings.smtp_password:
                    server.login(self._settings.smtp_user, self._settings.smtp_password)
                server.send_message(msg)

            logger.info("[AUTH EMAIL DISPATCH] Sent verification email to %s via SMTP", to_email)
            return True
        except Exception as exc:
            logger.warning(
                "[AUTH EMAIL DISPATCH] Failed to send email to %s via SMTP (%s). Code is: %s",
                to_email,
                exc,
                code,
            )
            return False
