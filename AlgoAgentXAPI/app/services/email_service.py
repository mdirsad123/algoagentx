from typing import List, Optional
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.models.users import User
from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_email = settings.smtp_email
        self.smtp_password = settings.smtp_password
        self.admin_notify_emails = self._parse_admin_emails(settings.admin_notify_emails)

    def _parse_admin_emails(self, admin_emails_str: str) -> List[str]:
        """Parse comma-separated admin emails string into list"""
        if not admin_emails_str:
            return []
        return [email.strip() for email in admin_emails_str.split(',') if email.strip()]

    def _is_smtp_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_email,
            self.smtp_password
        ])

    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> bool:
        """
        Send email to a specific address
        Returns True if successful, False otherwise
        """
        if not self._is_smtp_configured():
            logger.warning("SMTP not configured - skipping email to %s", to_email)
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Add body to email
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            # Create SMTP session
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Enable security
                server.login(self.smtp_email, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.smtp_email, to_email, text)
            
            logger.info("Email sent successfully to %s", to_email)
            return True

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, str(e))
            return False

    async def send_to_admins(
        self, 
        subject: str, 
        body: str, 
        is_html: bool = False
    ) -> bool:
        """
        Send email to all admin email addresses
        Returns True if at least one email was sent successfully
        """
        if not self.admin_notify_emails:
            logger.warning("No admin emails configured - skipping admin notification")
            return False

        success_count = 0
        for admin_email in self.admin_notify_emails:
            if await self.send_email(admin_email, subject, body, is_html):
                success_count += 1

        if success_count > 0:
            logger.info("Admin notification sent successfully to %d recipients", success_count)
            return True
        else:
            logger.error("Failed to send admin notification to any recipients")
            return False

    async def send_strategy_request_notification(
        self, 
        user_email: str, 
        user_name: str, 
        request_title: str
    ) -> bool:
        """
        Send strategy request notification email to admins
        """
        subject = "New Strategy Request Submitted"
        body = f"""
        A new strategy request has been submitted.

        Request Details:
        - Title: {request_title}
        - Submitted by: {user_name} ({user_email})
        - Submitted at: {self._get_current_time_str()}

        Please review the request in the admin panel.
        """

        return await self.send_to_admins(subject, body)

    async def send_strategy_deployed_notification(
        self, 
        user_email: str, 
        user_name: str, 
        strategy_title: str
    ) -> bool:
        """
        Send strategy deployed notification email to user
        """
        subject = "Your Strategy Has Been Deployed"
        body = f"""
        Great news! Your strategy has been deployed and is now ready to use.

        Strategy Details:
        - Title: {strategy_title}
        - Deployed for: {user_name}
        - Deployed at: {self._get_current_time_str()}

        You can now access your deployed strategy in your dashboard.
        """

        return await self.send_email(user_email, subject, body)

    def _get_current_time_str(self) -> str:
        """Get current time as formatted string"""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# Global email service instance
email_service = EmailService()