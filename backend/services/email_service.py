"""
Email Service — DocFlow AI

Sends transactional emails via AWS SES.
Uses the same IAM credentials as S3 (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY).

Setup:
1. Go to AWS Console → SES → Verified Identities → verify your sender email.
2. Add SES_FROM_EMAIL=your@email.com to backend/.env
3. For production: request SES production access to remove sandbox restrictions.
"""
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_document_notification(
    to_email: str,
    subject: str,
    heading: str,
    heading_color: str,
    border_color: str,
    body_html: str,
    body_text: str,
) -> bool:
    """
    Generic document notification email via AWS SES.
    Use this as the base for any workflow event that needs to notify a user.
    Returns True on success, False on failure (never raises).
    """
    from_email = getattr(settings, "ses_from_email", "")
    if not from_email:
        logger.warning("SES_FROM_EMAIL not configured — skipping email notification")
        return False

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #f8f9fa; border-radius: 8px; padding: 24px; border-left: 4px solid {border_color};">
            <h2 style="color: {heading_color}; margin-top: 0;">{heading}</h2>
            {body_html}
            <p style="margin-top: 24px; font-size: 13px; color: #666;">
                This is an automated notification from DocFlow AI.<br>
                Please do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """

    try:
        client = boto3.client(
            "ses",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Email '%s' sent to %s", subject, to_email)
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to send SES email to %s: %s", to_email, exc)
        return False


def send_approval_notification(
    to_email: str,
    filename: str,
    doc_type: str,
    crm_contact_id: str | None = None,
) -> bool:
    """
    Notify the uploader that their document was approved and pushed to HubSpot.
    Returns True on success, False on failure (never raises).
    """
    crm_note = (
        f"<p>Your information has been recorded in our system (reference: <strong>{crm_contact_id}</strong>).</p>"
        if crm_contact_id else
        "<p>Your information has been recorded in our system.</p>"
    )
    body_html = f"""
        <p>Great news! The document <strong>"{filename}"</strong> ({doc_type.replace('_', ' ').title()}) has been
        reviewed and approved by our team.</p>
        {crm_note}
        <p>No further action is required on your part.</p>
    """
    body_text = (
        f"Your document '{filename}' has been approved.\n\n"
        f"Your information has been recorded in our system"
        + (f" (reference: {crm_contact_id})." if crm_contact_id else ".")
        + "\n\nNo further action is required."
    )
    return send_document_notification(
        to_email=to_email,
        subject=f"Document Approved: '{filename}'",
        heading="Document Approved",
        heading_color="#27ae60",
        border_color="#27ae60",
        body_html=body_html,
        body_text=body_text,
    )


def send_rejection_notification(
    to_email: str,
    filename: str,
    doc_type: str,
    reason: str,
) -> bool:
    """
    Notify the uploader that their document was rejected by a reviewer.
    Returns True on success, False on failure (never raises).
    """
    body_html = f"""
        <p>Unfortunately, the document <strong>"{filename}"</strong> ({doc_type.replace('_', ' ').title()}) could not be accepted.</p>
        <div style="background: #fdecea; border-radius: 6px; padding: 16px; border: 1px solid #f5c6cb; margin: 16px 0;">
            <strong>Reason:</strong> {reason}
        </div>
        <p>Please contact our team if you have any questions or need assistance submitting a corrected document.</p>
    """
    body_text = (
        f"Your document '{filename}' was not accepted.\n\n"
        f"Reason: {reason}\n\n"
        "Please contact our team if you have questions or need to submit a corrected document."
    )
    return send_document_notification(
        to_email=to_email,
        subject=f"Document Not Accepted: '{filename}'",
        heading="Document Not Accepted",
        heading_color="#c0392b",
        border_color="#c0392b",
        body_html=body_html,
        body_text=body_text,
    )


def send_reupload_request(
    to_email: str,
    filename: str,
    doc_type: str,
    flags: list[str],
    message: str = "",
) -> bool:
    """
    Send a re-upload request email to the document uploader.
    Returns True on success, False on failure (never raises).
    """
    flag_items = "".join(f"<li>{f}</li>" for f in flags) if flags else "<li>Document could not be automatically validated</li>"
    extra_message = f"<p><strong>Additional note from our team:</strong> {message}</p>" if message.strip() else ""

    body_html = f"""
        <p>Our team has reviewed the document <strong>"{filename}"</strong> and found the following issues that need to be corrected:</p>
        <ul style="background: #fff3cd; border-radius: 6px; padding: 16px 16px 16px 32px; border: 1px solid #ffc107;">
            {flag_items}
        </ul>
        {extra_message}
        <p>Please review the issues above and re-upload a corrected document at your earliest convenience.</p>
    """
    body_text = (
        f"Action Required: Please Re-upload '{filename}'\n\n"
        "Our team reviewed your document and found the following issues:\n"
        + "\n".join(f"- {f}" for f in flags)
        + (f"\n\nNote from our team: {message}" if message.strip() else "")
        + "\n\nPlease re-upload a corrected document."
    )
    return send_document_notification(
        to_email=to_email,
        subject=f"Action Required: Please Re-upload '{filename}'",
        heading="Action Required — Document Re-upload",
        heading_color="#e67e22",
        border_color="#e67e22",
        body_html=body_html,
        body_text=body_text,
    )
