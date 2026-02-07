"""
Notification tools for sending alerts
"""

import os
from typing import Dict, Any, Optional
from loguru import logger
from rich.console import Console
from rich.panel import Panel

console = Console()


class NotificationTool:
    """Tool to send notifications via various channels"""

    name = "send_notification"
    description = "Send a notification message. Supports console, slack, and discord channels."

    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")

    def run(self, message: str, channel: str = "console", **kwargs) -> Dict[str, Any]:
        """
        Send notification

        Args:
            message: Message to send
            channel: Channel to send to (console, slack, discord)
            **kwargs: Additional channel-specific parameters

        Returns:
            Status of the notification
        """
        try:
            if channel == "console":
                return self._send_console(message)
            elif channel == "slack":
                return self._send_slack(message)
            elif channel == "discord":
                return self._send_discord(message)
            else:
                logger.warning(f"Unknown channel: {channel}, defaulting to console")
                return self._send_console(message)

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {
                "success": False,
                "channel": channel,
                "error": str(e),
            }

    def _send_console(self, message: str) -> Dict[str, Any]:
        """Send notification to console"""
        console.print(Panel(
            message,
            title="📢 Notification",
            border_style="green"
        ))

        return {
            "success": True,
            "channel": "console",
            "message": message,
        }

    def _send_slack(self, message: str) -> Dict[str, Any]:
        """Send notification to Slack"""
        if not self.slack_webhook:
            logger.warning("SLACK_WEBHOOK_URL not configured")
            return {
                "success": False,
                "channel": "slack",
                "error": "Webhook not configured",
            }

        try:
            import requests

            payload = {"text": message}
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Slack notification sent successfully")
            return {
                "success": True,
                "channel": "slack",
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return {
                "success": False,
                "channel": "slack",
                "error": str(e),
            }

    def _send_discord(self, message: str) -> Dict[str, Any]:
        """Send notification to Discord"""
        if not self.discord_webhook:
            logger.warning("DISCORD_WEBHOOK_URL not configured")
            return {
                "success": False,
                "channel": "discord",
                "error": "Webhook not configured",
            }

        try:
            import requests

            payload = {"content": message}
            response = requests.post(self.discord_webhook, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("Discord notification sent successfully")
            return {
                "success": True,
                "channel": "discord",
                "message": message,
            }

        except Exception as e:
            logger.error(f"Error sending Discord notification: {e}")
            return {
                "success": False,
                "channel": "discord",
                "error": str(e),
            }


class EmailNotificationTool:
    """Tool to send email notifications"""

    name = "send_email"
    description = "Send an email notification"

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")

    def run(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            from_email: Sender email (defaults to SMTP_USER)

        Returns:
            Status of the email
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("Email credentials not configured")
            return {
                "success": False,
                "error": "Email credentials not configured",
            }

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            from_email = from_email or self.smtp_user

            # Create message
            msg = MIMEMultipart()
            msg["From"] = from_email
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {to}")
            return {
                "success": True,
                "to": to,
                "subject": subject,
            }

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e),
            }


if __name__ == "__main__":
    # Test tool
    tool = NotificationTool()
    result = tool.run("Test notification", channel="console")
    print(result)
