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
    from_email = getattr(settings, "ses_from_email", "")
    if not from_email:
        logger.warning("SES_FROM_EMAIL not configured — skipping email notification")
        return False

    subject = f"Action Required: Please Re-upload '{filename}'"

    flag_items = "".join(f"<li>{f}</li>" for f in flags) if flags else "<li>Document could not be automatically validated</li>"

    extra_message = f"<p><strong>Additional note from our team:</strong> {message}</p>" if message.strip() else ""

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #f8f9fa; border-radius: 8px; padding: 24px; border-left: 4px solid #e67e22;">
            <h2 style="color: #e67e22; margin-top: 0;">Action Required — Document Re-upload</h2>
            <p>Our team has reviewed the document <strong>"{filename}"</strong> and found the following issues that need to be corrected:</p>
            <ul style="background: #fff3cd; border-radius: 6px; padding: 16px 16px 16px 32px; border: 1px solid #ffc107;">
                {flag_items}
            </ul>
            {extra_message}
            <p>Please review the issues above and re-upload a corrected document at your earliest convenience.</p>
            <p style="margin-top: 24px; font-size: 13px; color: #666;">
                This is an automated notification from DocFlow AI.<br>
                Please do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """

    text_body = (
        f"Action Required: Please Re-upload '{filename}'\n\n"
        f"Our team reviewed your document and found the following issues:\n"
        + "\n".join(f"- {f}" for f in flags)
        + (f"\n\nNote from our team: {message}" if message.strip() else "")
        + "\n\nPlease re-upload a corrected document."
    )

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
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Re-upload email sent to %s for file '%s'", to_email, filename)
        return True
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to send SES email to %s: %s", to_email, exc)
        return False
