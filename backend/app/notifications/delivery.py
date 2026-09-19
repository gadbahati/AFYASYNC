"""Deliver one-time codes via SMS or email.

Providers are selected by settings. Never log the plain code in production.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib import error, request

from app.config import settings

logger = logging.getLogger("afyasync.notifications")


def deliver_password_reset_code(
    *,
    channel: str,
    destination: str,
    code: str,
    destination_hint: str,
) -> bool:
    """Send reset code. Returns True if handoff to provider succeeded."""
    if not code or not destination:
        return False

    channel = (channel or "PHONE").upper()
    if channel == "EMAIL":
        return _send_email(destination=destination, code=code, hint=destination_hint)
    return _send_sms(destination=destination, code=code, hint=destination_hint)


def _send_sms(*, destination: str, code: str, hint: str) -> bool:
    provider = (settings.sms_provider or "console").lower()
    message = (
        f"AfyaSync: your password reset code is {code}. "
        f"It expires in 15 minutes. Do not share this code."
    )

    if provider == "console" or settings.environment != "production":
        # Dev/staging: log code only outside production
        if settings.environment != "production":
            logger.info(
                "SMS_CONSOLE channel=PHONE dest=%s code=%s (non-production)",
                hint,
                code,
            )
        else:
            logger.info("SMS_CONSOLE channel=PHONE dest=%s (code suppressed)", hint)
        if provider == "console":
            return True

    if provider == "http":
        return _http_post_sms(destination=destination, message=message, hint=hint)

    logger.error("Unknown SMS provider=%s", provider)
    return False


def _http_post_sms(*, destination: str, message: str, hint: str) -> bool:
    url = (settings.sms_http_url or "").strip()
    if not url:
        logger.error("SMS_HTTP_URL not configured")
        return False

    # Generic JSON payload — map fields at the gateway if needed
    body = (
        f'{{"to":"{_escape(destination)}","message":"{_escape(message)}",'
        f'"from":"{_escape(settings.sms_sender_id or "AfyaSync")}"}}'
    ).encode("utf-8")

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.sms_http_api_key:
        headers["Authorization"] = f"Bearer {settings.sms_http_api_key}"

    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=15) as resp:
            ok = 200 <= getattr(resp, "status", 200) < 300
            if ok:
                logger.info("SMS_HTTP delivered dest=%s", hint)
            else:
                logger.warning("SMS_HTTP non-success dest=%s status=%s", hint, resp.status)
            return ok
    except error.HTTPError as exc:
        logger.warning("SMS_HTTP failed dest=%s status=%s", hint, exc.code)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning("SMS_HTTP error dest=%s err=%s", hint, type(exc).__name__)
        return False


def _send_email(*, destination: str, code: str, hint: str) -> bool:
    provider = (settings.email_provider or "console").lower()
    subject = "AfyaSync password reset code"
    body = (
        f"Your AfyaSync patient portal password reset code is: {code}\n\n"
        f"This code expires in 15 minutes.\n"
        f"If you did not request this, ignore this email.\n\n"
        f"— AfyaSync\nDeveloped by BAHATI GAD WANGWE\n"
    )

    if provider == "console" or settings.environment != "production":
        if settings.environment != "production":
            logger.info(
                "EMAIL_CONSOLE dest=%s code=%s (non-production)",
                hint,
                code,
            )
        else:
            logger.info("EMAIL_CONSOLE dest=%s (code suppressed)", hint)
        if provider == "console":
            return True

    if provider == "smtp":
        return _smtp_send(
            destination=destination,
            subject=subject,
            body=body,
            hint=hint,
        )

    logger.error("Unknown email provider=%s", provider)
    return False


def _smtp_send(*, destination: str, subject: str, body: str, hint: str) -> bool:
    host = (settings.smtp_host or "").strip()
    if not host:
        logger.error("SMTP_HOST not configured")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or "noreply@afyasync.local"
    msg["To"] = destination
    msg.set_content(body)

    try:
        if settings.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, settings.smtp_port, timeout=20) as server:
                server.starttls(context=context)
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password or "")
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, settings.smtp_port, timeout=20) as server:
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password or "")
                server.send_message(msg)
        logger.info("EMAIL_SMTP delivered dest=%s", hint)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("EMAIL_SMTP error dest=%s err=%s", hint, type(exc).__name__)
        return False


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
