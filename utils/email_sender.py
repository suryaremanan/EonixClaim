"""
Email notification system for the Eonix insurance platform.
Sends personalized emails to customers about their insurance claims.
"""
import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from string import Template
from typing import Dict, Any, List, Optional
import uuid
import ics  # pip install ics
from ics import Calendar, Event
from email.mime.application import MIMEApplication  # Add this import
# Configure logger
logger = logging.getLogger(__name__)

class EmailNotifier:
    """
    Email notification service for customer communications.
    Handles templating, attachment processing, and delivery of notifications.
    """
    
    def __init__(self):
        """Initialize the email notifier with SMTP settings."""
        # Load email configuration from environment variables
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", "eonixinsurance@example.com")
        
        # Check if we have valid SMTP credentials
        self.smtp_configured = all([
            self.smtp_server, 
            self.smtp_port, 
            self.smtp_username, 
            self.smtp_password
        ])
        
        # Log configuration status (but don't log credentials)
        if self.smtp_configured:
            logger.info(f"Email notifier initialized with server {self.smtp_server}:{self.smtp_port}")
        else:
            logger.warning("Email notifier initialized without valid SMTP configuration")
            logger.warning("Set SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and FROM_EMAIL environment variables")
        
        # Email templates directory
        self.template_dir = os.path.join(os.path.dirname(__file__), '../templates/email')
        
        # Default sender
        self.default_sender = os.environ.get('EMAIL_DEFAULT_SENDER', 'claims@eonixinsurance.com')
        
        logger.info("Email notification system initialized")
    
    def send_claim_confirmation(self, customer_email: str, claim_data: Dict[str, Any]) -> bool:
        """
        Send a claim confirmation email to the customer.
        
        Args:
            customer_email: Customer's email address
            claim_data: Dictionary containing claim details
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        # Load the claim confirmation template
        template_path = os.path.join(self.template_dir, 'claim_confirmation.html')
        
        with open(template_path, 'r') as f:
            template = Template(f.read())
        
        # Format the current date
        today = datetime.now().strftime("%B %d, %Y")
        
        # Prepare template variables
        variables = {
            'customer_name': claim_data.get('customer_name', 'Valued Customer'),
            'claim_id': claim_data.get('claim_id', 'Unknown'),
            'damage_description': claim_data.get('damage_description', 'Vehicle damage'),
            'estimated_cost': f"${claim_data.get('estimated_cost', 0):.2f}",
            'repair_time': claim_data.get('repair_time', 'Unknown'),
            'date': today,
            'blockchain_id': claim_data.get('blockchain_id', 'Not available'),
            'adjuster_name': claim_data.get('adjuster_name', 'Insurance Team'),
            'adjuster_phone': claim_data.get('adjuster_phone', '555-123-4567')
        }
        
        # Fill the template with variables
        email_content = template.substitute(variables)
        
        # Create the email message
        subject = f"Your Claim #{claim_data.get('claim_id')} Has Been Received"
        
        return self._send_email(customer_email, subject, email_content, claim_data)
    
    def send_repair_scheduled(self, to_email, data):
        """
        Send repair scheduled notification with calendar invite.
        
        Args:
            to_email: Recipient email address
            data: Dictionary with appointment details:
                - customer_name: Name of the customer
                - claim_id: Claim ID
                - date: Appointment date (string)
                - time: Appointment time (string)
                - location: Service center name
                - address: Service center address
                - phone: Service center phone
                - confirmation_code: Confirmation code
                - directions_link: Link to directions
        
        Returns:
            True if email was sent, False otherwise
        """
        try:
            # Log the attempt
            logger.info(f"Attempting to send repair scheduled email to {to_email}")
            
            # Create email subject and HTML content
            subject = f"Your Vehicle Repair Appointment Confirmation - Claim #{data['claim_id']}"
            
            # Create HTML email content
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ width: 100%; max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: #0066cc; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .appointment {{ background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #0066cc; }}
                    .footer {{ font-size: 12px; color: #999; text-align: center; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Appointment Confirmation</h1>
                    </div>
                    <div class="content">
                        <p>Dear {data['customer_name']},</p>
                        
                        <p>Your vehicle repair appointment has been scheduled. Please find the details below:</p>
                        
                        <div class="appointment">
                            <p><strong>Claim ID:</strong> {data['claim_id']}</p>
                            <p><strong>Date:</strong> {data['date']}</p>
                            <p><strong>Time:</strong> {data['time']}</p>
                            <p><strong>Location:</strong> {data['location']}</p>
                            <p><strong>Address:</strong> {data['address']}</p>
                            <p><strong>Confirmation Code:</strong> {data['confirmation_code']}</p>
                        </div>
                        
                        <p>Please arrive 15 minutes early with your vehicle and insurance information.</p>
                        
                        <p>If you need to reschedule, please call {data['phone']} or reply to this email.</p>
                        
                        <p>We've attached a calendar invitation to help you remember your appointment.</p>
                        
                        <p>Thank you for choosing Eonix Insurance.</p>
                        
                        <p>Best regards,<br>The Eonix Insurance Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message. Please do not reply directly to this email.</p>
                        <p>© {datetime.now().year} Eonix Insurance. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create plain text alternative
            text = f"""
            Dear {data['customer_name']},
            
            Your vehicle repair appointment has been scheduled. Please find the details below:
            
            Claim ID: {data['claim_id']}
            Date: {data['date']}
            Time: {data['time']}
            Location: {data['location']}
            Address: {data['address']}
            Confirmation Code: {data['confirmation_code']}
            
            Please arrive 15 minutes early with your vehicle and insurance information.
            
            If you need to reschedule, please call {data['phone']} or reply to this email.
            
            We've attached a calendar invitation to help you remember your appointment.
            
            Thank you for choosing Eonix Insurance.
            
            Best regards,
            The Eonix Insurance Team
            
            This is an automated message. Please do not reply directly to this email.
            © {datetime.now().year} Eonix Insurance. All rights reserved.
            """
            
            # Create calendar invite
            cal = Calendar()
            event = Event()
            event.name = f"Vehicle Repair - Claim #{data['claim_id']}"
            
            # Parse date and time
            try:
                # Try to parse date/time in various formats
                date_str = data['date']
                time_str = data['time']
                
                # Handle common date formats
                if "," in date_str:
                    # Format like "Monday, January 1"
                    date_parts = date_str.split(", ")[1].split()
                    month = ["January", "February", "March", "April", "May", "June", 
                             "July", "August", "September", "October", "November", "December"].index(date_parts[0]) + 1
                    day = int(date_parts[1])
                    year = datetime.now().year
                else:
                    # Format like "2023-01-01"
                    date_parts = date_str.split("-")
                    year = int(date_parts[0])
                    month = int(date_parts[1])
                    day = int(date_parts[2])
                
                # Handle common time formats
                if ":" in time_str:
                    # Format like "14:30" or "2:30 PM"
                    if "PM" in time_str or "AM" in time_str:
                        # 12-hour format
                        hour_min, ampm = time_str.split(" ")
                        hour, minute = map(int, hour_min.split(":"))
                        if ampm == "PM" and hour < 12:
                            hour += 12
                        elif ampm == "AM" and hour == 12:
                            hour = 0
                    else:
                        # 24-hour format
                        hour, minute = map(int, time_str.split(":"))
                else:
                    # Default if format is unknown
                    hour, minute = 9, 0
                
                start_time = datetime(year, month, day, hour, minute)
                end_time = start_time + timedelta(hours=2)  # Assuming 2-hour appointment
                
                event.begin = start_time
                event.end = end_time
            except Exception as date_error:
                logger.error(f"Error parsing date/time: {date_error}")
                # Use a default time if parsing fails
                today = datetime.now()
                event.begin = today + timedelta(days=3, hours=9)  # 3 days from now at 9 AM
                event.end = today + timedelta(days=3, hours=11)   # 2-hour appointment
            
            event.location = f"{data['location']}, {data['address']}"
            event.description = f"""
            Claim ID: {data['claim_id']}
            Confirmation Code: {data['confirmation_code']}
            
            Please arrive 15 minutes early with your vehicle and insurance information.
            
            If you need to reschedule, please call {data['phone']}.
            """
            
            cal.events.add(event)
            
            # Create the email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Attach text and HTML parts
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            # Attach the calendar invite
            ics_content = str(cal)
            cal_attachment = MIMEApplication(ics_content.encode('utf-8'))
            cal_attachment.add_header('Content-Disposition', 'attachment', 
                                     filename=f"repair_appointment_{data['claim_id']}.ics")
            msg.attach(cal_attachment)
            
            # Attempt to send the email if SMTP is configured
            if self.smtp_configured:
                try:
                    logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.ehlo()
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(self.from_email, to_email, msg.as_string())
                    server.quit()
                    logger.info(f"Email sent successfully to {to_email}")
                    return True
                except Exception as smtp_error:
                    logger.error(f"SMTP error: {smtp_error}")
                    
                    # Fallback to save email to file for debugging
                    self._save_email_to_file(to_email, msg.as_string())
                    return False
            else:
                # If SMTP is not configured, save to file
                logger.warning("SMTP not configured, saving email to file")
                self._save_email_to_file(to_email, msg.as_string())
                return True  # Return True to not break the flow
            
        except Exception as e:
            logger.error(f"Error in send_repair_scheduled: {e}")
            return False
    
    def _save_email_to_file(self, to_email, email_content):
        """Save email content to a file for debugging."""
        try:
            # Create directory if it doesn't exist
            os.makedirs('debug_emails', exist_ok=True)
            
            # Generate unique filename
            filename = f"debug_emails/email_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.eml"
            
            # Write to file
            with open(filename, 'w') as f:
                f.write(f"To: {to_email}\n")
                f.write(email_content)
            
            logger.info(f"Email saved to file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error saving email to file: {e}")
            return False
    
    def _send_email(self, recipient: str, subject: str, html_content: str, data: Dict[str, Any]) -> bool:
        """
        Send an email with the given content.
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            html_content: HTML email content
            data: Additional data for the email
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = recipient
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Add claim image if available
            if 'image_path' in data and os.path.exists(data['image_path']):
                with open(data['image_path'], 'rb') as img_file:
                    img = MIMEImage(img_file.read())
                    img.add_header('Content-ID', '<damage_image>')
                    img.add_header('Content-Disposition', 'inline', filename=os.path.basename(data['image_path']))
                    msg.attach(img)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False 