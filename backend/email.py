"""Email delivery for account verification messages.

Configure via environment variables:
  SMTP_HOST       SMTP server hostname (required for email sending)
  SMTP_PORT       Default: 587 (STARTTLS)
  SMTP_USER       SMTP username / email address
  SMTP_PASSWORD   SMTP password
  SMTP_FROM       From address (default: noreply@stresslab.local)
  APP_URL         Public base URL of the app (default: http://localhost:8000)

If SMTP_HOST is not set, the verification URL is logged to the server console
instead of being emailed. This covers local development without any mail config.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@stresslab.local")
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")


def send_verification_email(email: str, token: str) -> None:
    verify_url = f"{APP_URL}/verify-email?token={token}"
    body = (
        f"Hello,\n\n"
        f"Click the link below to verify your StressLab account:\n\n"
        f"  {verify_url}\n\n"
        f"This link is valid indefinitely.\n\n"
        f"If you did not create an account, you can safely ignore this message."
    )

    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEText(body)
            msg["Subject"] = "Verify your StressLab account"
            msg["From"] = SMTP_FROM
            msg["To"] = email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [email], msg.as_string())
            logger.info("Verification email sent to %s", email)
        except Exception as exc:
            logger.error("Failed to send verification email to %s: %s", email, exc)
            logger.info("VERIFY URL (fallback) for %s: %s", email, verify_url)
    else:
        logger.info(
            "SMTP not configured -- verification URL for %s: %s",
            email,
            verify_url,
        )
