"""Email delivery for account verification messages.

Priority order for sending:
  1. Resend API  (set RESEND_API_KEY)
  2. SMTP        (set SMTP_HOST + SMTP_USER + SMTP_PASSWORD)
  3. Log to console (development fallback — no emails sent)

Environment variables:
  RESEND_API_KEY  API key from resend.com (recommended)
  RESEND_FROM     From address for Resend (default: onboarding@resend.dev)
  APP_URL         Public base URL of the app (default: http://localhost:8000)

  SMTP_HOST       SMTP server hostname
  SMTP_PORT       Default: 587 (STARTTLS)
  SMTP_USER       SMTP username / email address
  SMTP_PASSWORD   SMTP password
  SMTP_FROM       From address (default: noreply@stresslab.local)
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "StressLab <onboarding@resend.dev>")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@stresslab.local")

APP_URL = os.environ.get("APP_URL", "http://localhost:8000")


def _send_via_resend(to: str, subject: str, text: str) -> None:
    import resend
    resend.api_key = RESEND_API_KEY
    resend.Emails.send({
        "from": RESEND_FROM,
        "to": [to],
        "subject": subject,
        "text": text,
    })


def _send_via_smtp(to: str, subject: str, text: str) -> None:
    msg = MIMEText(text)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to], msg.as_string())


def send_verification_email(email: str, token: str) -> None:
    verify_url = f"{APP_URL}/verify-email?token={token}"
    subject = "Verify your StressLab account"
    body = (
        f"Hello,\n\n"
        f"Click the link below to verify your StressLab account:\n\n"
        f"  {verify_url}\n\n"
        f"This link is valid indefinitely.\n\n"
        f"If you did not create an account, you can safely ignore this message."
    )

    if RESEND_API_KEY:
        try:
            _send_via_resend(email, subject, body)
            logger.info("Verification email sent via Resend to %s", email)
            return
        except Exception as exc:
            logger.error("Resend failed for %s: %s", email, exc)

    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            _send_via_smtp(email, subject, body)
            logger.info("Verification email sent via SMTP to %s", email)
            return
        except Exception as exc:
            logger.error("SMTP failed for %s: %s", email, exc)

    logger.info("No email provider configured -- verification URL for %s: %s", email, verify_url)
