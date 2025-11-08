import os
import smtplib
import ssl
from email.message import EmailMessage


def _smtp_settings():
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user or "no-reply@example.com")
    use_tls = os.getenv("SMTP_USE_TLS", "1") in ("1", "true", "True", "TRUE")
    return host, port, user, password, sender, use_tls


def send_reset_email(to_email: str, reset_link: str):
    """
    Send a password reset email with the given link.
    Uses environment variables:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS
    """
    host, port, user, password, sender, use_tls = _smtp_settings()
    if not host:
        # SMTP not configured; skip silently (useful in local dev)
        return

    subject = "Zeno Password Reset"
    text = (
        "You requested a password reset for your Zeno account.\n\n"
        f"Click the link to reset your password: {reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(text)

    if use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            if user and password:
                server.login(user, password)
            server.send_message(msg)
