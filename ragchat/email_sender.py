"""Sending the company profile by e-mail (SMTP, or logged to the console for demos)."""

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str, attachment: Path | None) -> None: ...


class ConsoleEmailSender:
    def __init__(self):
        self.outbox: list[dict] = []

    async def send(self, to: str, subject: str, body: str, attachment: Path | None) -> None:
        self.outbox.append({"to": to, "subject": subject, "body": body, "attachment": attachment})
        logger.info(
            "E-MAIL (console mode)\nTo: %s\nSubject: %s\nAttachment: %s\n\n%s",
            to, subject, attachment.name if attachment else "-", body,
        )  # fmt: skip


class SmtpEmailSender:
    def __init__(self, host: str, port: int, sender: str, username=None, password=None):
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password = username, password

    async def send(self, to: str, subject: str, body: str, attachment: Path | None) -> None:
        import asyncio

        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, to, subject
        message.set_content(body)
        if attachment is not None and attachment.exists():
            message.add_attachment(
                attachment.read_bytes(), maintype="application", subtype="pdf",
                filename=attachment.name,
            )  # fmt: skip
        await asyncio.to_thread(self._deliver, message)

    def _deliver(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def build_email_sender(settings) -> EmailSender:
    if settings.smtp_host:
        return SmtpEmailSender(
            settings.smtp_host,
            settings.smtp_port,
            settings.email_sender,
            settings.smtp_username,
            settings.smtp_password.get_secret_value() if settings.smtp_password else None,
        )
    return ConsoleEmailSender()
