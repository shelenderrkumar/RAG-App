from typing import Dict, Any, List

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from langchain_google_community.gmail.send_message import GmailSendMessage as OriginalGmailSendMessage
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)



credentials = get_gmail_credentials(
    token_file="token.json",
    scopes=["https://mail.google.com/"],
    client_secrets_file="credentials.json",
)

api_resource = build_resource_service(credentials=credentials)
toolkit = GmailToolkit(api_resource=api_resource)




class GmailSendMessageWithAttachment(OriginalGmailSendMessage):
    def send_message_with_attachments(
        self, sender: str, to: str, subject: str, body_text: str, cc: List[str] = None
    ) -> dict:
        """Send an email with attachments using the Gmail API."""
        message = MIMEMultipart()
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        
        print("Inside gmail class")
        if cc:
            message['cc'] = ', '.join(cc)

        msg_body = MIMEText(body_text, 'plain')
        message.attach(msg_body)


        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = self.api_resource.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        
        
        return result




def send_service_confirmation_email(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends a service appointment confirmation email to the customer.

    Args:
        appointment_data (dict): Dictionary containing appointment details.

    Returns:
        dict: Response from the Gmail API or error information.
    """

    recipient_email = appointment_data['email']
    # cc_emails = ["skumar.bscs20seecs@seecs.edu.pk", "basit@forloops.co"]
    cc_emails = ["skumar.bscs20seecs@seecs.edu.pk"]
    subject = "Company Deatil Overview"

    email_body = f"""
    Dear Customer,

    Thank you for contacting us. Here are compay details:

    
    If you need to reschedule or have any questions, please reply to this email or call our support team.

    Best regards,
    Support Team
    """

    try:
        send_message_tool = GmailSendMessageWithAttachment(api_resource=api_resource)
        response = send_message_tool.send_message_with_attachments(
            sender="",
            to=recipient_email,
            subject=subject,
            body_text=email_body,
            cc=cc_emails
        )
        return {'success': f"Appointment scheduled successfully and confirmation email sent to {recipient_email}."}
    except Exception as e:
        return {'error': "Failed to send confirmation email. Please contact support."}
