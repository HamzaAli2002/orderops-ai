"""Real SMTP email dispatch (e.g. Gmail with an App Password, or any SMTP provider)."""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def _send_smtp_sync(to_email: str, subject: str, html_body: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        # No SMTP configured - fall back to printing, so the app still
        # works end-to-end (minus the actual email) without credentials.
        print(f"[EMAIL - SMTP not configured, printing instead]")
        print(f"To: {to_email}\nSubject: {subject}\n{html_body}\n")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_username
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(msg["From"], [to_email], msg.as_string())


async def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Runs the blocking smtplib call in a thread so it doesn't stall the event loop."""
    await asyncio.to_thread(_send_smtp_sync, to_email, subject, html_body)


async def send_sms(customer_id: str, message: str) -> None:
    """TODO: integrate an SMS provider (Twilio, etc.). Not used by the current flow."""
    print(f"[SMS -> customer {customer_id}] {message}")
