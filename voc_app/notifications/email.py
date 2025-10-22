"""Email notification channel."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from voc_app.config import get_settings

from .base import NotificationChannel, NotificationResult

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """Send notifications via email."""

    @property
    def channel_name(self) -> str:
        return "email"

    async def send(
        self,
        recipient: str,
        subject: str,
        message: str,
        **kwargs: Any,
    ) -> NotificationResult:
        """Send an email notification."""
        settings = get_settings()

        # Get SMTP configuration from environment
        smtp_host = kwargs.get("smtp_host", "localhost")
        smtp_port = kwargs.get("smtp_port", 587)
        smtp_user = kwargs.get("smtp_user")
        smtp_password = kwargs.get("smtp_password")
        from_email = kwargs.get("from_email", "noreply@voc-app.com")

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = recipient

            # Add HTML and plain text parts
            html_content = self._format_html(subject, message, kwargs)
            text_content = self._format_text(subject, message)

            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent to {recipient}: {subject}")

            return NotificationResult(
                success=True,
                channel=self.channel_name,
                recipient=recipient,
                metadata={"subject": subject},
            )

        except Exception as exc:
            logger.exception(f"Email notification failed to {recipient}: {exc}")
            return NotificationResult(
                success=False,
                channel=self.channel_name,
                recipient=recipient,
                error=str(exc),
            )

    def _format_html(self, subject: str, message: str, kwargs: dict) -> str:
        """Format HTML email content."""
        alert_url = kwargs.get("alert_url", "#")
        severity = kwargs.get("severity", "medium")

        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#0dcaf0",
        }
        color = severity_colors.get(severity, "#6c757d")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border-radius: 0 0 5px 5px; }}
        .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔔 {subject}</h2>
        </div>
        <div class="content">
            <p>{message.replace(chr(10), '<br>')}</p>
            <p><a href="{alert_url}" class="button">View Alert Details</a></p>
        </div>
    </div>
</body>
</html>
"""

    def _format_text(self, subject: str, message: str) -> str:
        """Format plain text email content."""
        return f"{subject}\n\n{message}\n"
