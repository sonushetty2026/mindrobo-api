"""Email notification service using SendGrid."""

import os
import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Try to import SendGrid, but don't crash if it's not installed
try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logger.warning("SendGrid not installed. Email notifications will be disabled.")

from app.utils.usage_tracker import log_api_usage


class EmailService:
    """Email service for sending notifications."""
    
    def __init__(self):
        """Initialize email service."""
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@mindrobo.com")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "MindRobo")
        
        if not SENDGRID_AVAILABLE:
            logger.warning("SendGrid library not available. Emails will not be sent.")
            self.enabled = False
        elif not self.api_key:
            logger.warning("SENDGRID_API_KEY not configured. Emails will not be sent.")
            self.enabled = False
        else:
            self.client = SendGridAPIClient(self.api_key)
            self.enabled = True
            logger.info("Email service initialized successfully")
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
        db: AsyncSession | None = None,
        user_id: UUID | None = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML body content
            plain_body: Plain text body (optional)
            db: Optional database session for usage logging
            user_id: Optional user ID for usage logging
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Email service disabled. Would have sent to {to}: {subject}")
            return False
        
        try:
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to,
                subject=subject,
                html_content=html_body,
            )
            
            if plain_body:
                message.plain_text_content = plain_body
            
            response = self.client.send(message)
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to}: {subject}")
                
                # Log API usage ($0.001 per email)
                if db and user_id:
                    await log_api_usage(
                        db=db,
                        user_id=user_id,
                        service="sendgrid",
                        endpoint="email",
                        cost_cents=0,  # Less than 1 cent, so we'll track as 0
                        request_data={"to": to, "subject": subject}
                    )
                
                return True
            else:
                logger.error(f"Failed to send email to {to}: {response.status_code} {response.body}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending email to {to}: {str(e)}")
            return False
    
    async def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """
        Send welcome email after verification.
        
        Args:
            user_email: User's email address
            user_name: User's name
        
        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Welcome to MindRobo!"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">Welcome to MindRobo, {user_name}!</h2>
                    
                    <p>Your account has been verified successfully. You're all set to start using MindRobo's AI-powered phone assistant for your business.</p>
                    
                    <p>Here's what you can do next:</p>
                    <ul>
                        <li>Set up your business profile</li>
                        <li>Configure your phone number</li>
                        <li>Customize your AI assistant's responses</li>
                        <li>Start capturing leads automatically</li>
                    </ul>
                    
                    <p>
                        <a href="http://52.159.104.87:8000/dashboard" 
                           style="display: inline-block; padding: 12px 24px; background-color: #4A90E2; 
                                  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">
                            Go to Dashboard
                        </a>
                    </p>
                    
                    <p>If you have any questions, feel free to reach out to our support team.</p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 40px;">
                        Best regards,<br>
                        The MindRobo Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_body = f"""
        Welcome to MindRobo, {user_name}!
        
        Your account has been verified successfully. You're all set to start using MindRobo's AI-powered phone assistant for your business.
        
        Here's what you can do next:
        - Set up your business profile
        - Configure your phone number
        - Customize your AI assistant's responses
        - Start capturing leads automatically
        
        Visit your dashboard: http://52.159.104.87:8000/dashboard
        
        If you have any questions, feel free to reach out to our support team.
        
        Best regards,
        The MindRobo Team
        """
        
        return await self.send_email(user_email, subject, html_body, plain_body)
    
    async def send_lead_notification(
        self,
        owner_email: str,
        business_name: str,
        lead_name: str,
        lead_phone: str,
        service_needed: Optional[str] = None,
        db: AsyncSession | None = None,
        user_id: UUID | None = None,
    ) -> bool:
        """
        Send lead notification to business owner.
        
        Args:
            owner_email: Business owner's email
            business_name: Business name
            lead_name: Lead's name
            lead_phone: Lead's phone number
            service_needed: Service requested
        
        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"New Lead for {business_name}"
        
        service_text = f"<p><strong>Service Needed:</strong> {service_needed}</p>" if service_needed else ""
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">New Lead Alert!</h2>
                    
                    <p>You have a new lead for {business_name}:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Name:</strong> {lead_name}</p>
                        <p><strong>Phone:</strong> {lead_phone}</p>
                        {service_text}
                    </div>
                    
                    <p>
                        <a href="http://52.159.104.87:8000/leads" 
                           style="display: inline-block; padding: 12px 24px; background-color: #4A90E2; 
                                  color: white; text-decoration: none; border-radius: 5px;">
                            View Lead Details
                        </a>
                    </p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 40px;">
                        This lead was automatically captured by your MindRobo AI assistant.
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_body = f"""
        New Lead Alert!
        
        You have a new lead for {business_name}:
        
        Name: {lead_name}
        Phone: {lead_phone}
        {f'Service Needed: {service_needed}' if service_needed else ''}
        
        View lead details: http://52.159.104.87:8000/leads
        
        This lead was automatically captured by your MindRobo AI assistant.
        """
        
        return await self.send_email(owner_email, subject, html_body, plain_body, db, user_id)
    
    async def send_appointment_confirmation(
        self,
        customer_email: str,
        customer_name: str,
        business_name: str,
        appointment_date: str,
        appointment_time: str,
        service: str,
    ) -> bool:
        """
        Send appointment confirmation to customer.
        
        Args:
            customer_email: Customer's email
            customer_name: Customer's name
            business_name: Business name
            appointment_date: Appointment date (formatted)
            appointment_time: Appointment time (formatted)
            service: Service being provided
        
        Returns:
            True if sent successfully, False otherwise
        """
        subject = f"Appointment Confirmed with {business_name}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4A90E2;">Appointment Confirmed</h2>
                    
                    <p>Hi {customer_name},</p>
                    
                    <p>Your appointment with {business_name} has been confirmed.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Date:</strong> {appointment_date}</p>
                        <p><strong>Time:</strong> {appointment_time}</p>
                        <p><strong>Service:</strong> {service}</p>
                    </div>
                    
                    <p>We look forward to seeing you!</p>
                    
                    <p style="color: #666; font-size: 14px; margin-top: 40px;">
                        If you need to reschedule or have any questions, please call us.
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_body = f"""
        Appointment Confirmed
        
        Hi {customer_name},
        
        Your appointment with {business_name} has been confirmed.
        
        Date: {appointment_date}
        Time: {appointment_time}
        Service: {service}
        
        We look forward to seeing you!
        
        If you need to reschedule or have any questions, please call us.
        """
        
        return await self.send_email(customer_email, subject, html_body, plain_body)


# Global email service instance
email_service = EmailService()
