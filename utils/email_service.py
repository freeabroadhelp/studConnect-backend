import os
import logging
import resend

logger = logging.getLogger("otp_mail")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "StudConnect <onboarding@resend.dev>")

resend.api_key = RESEND_API_KEY


def send_otp(email: str, code: str) -> bool:
    """
    Send OTP email using Resend.
    Returns True if email sent successfully, False otherwise.
    """
    try:
        subject = "Your Verification Code - StudConnect"

        html_content = f"""
        <div style="font-family: Arial, sans-serif;">
            <h2>StudConnect Email Verification</h2>
            <p>Your OTP code is:</p>
            <h1>{code}</h1>
            <p>This code will expire in 10 minutes.</p>
        </div>
        """

        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [email],
            "subject": subject,
            "html": html_content,
        })

        logger.info(f"[EMAIL] OTP sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send OTP to {email}: {e}")
        return False


def send_email(to_email: str, subject: str, message: str) -> bool:
    """
    Send a plain text email using Resend.
    Returns True if email sent successfully, False otherwise.
    """
    try:
        html_content = f"""
        <div style="font-family: Arial, sans-serif;">
            <pre style="white-space: pre-wrap; font-family: inherit;">{message}</pre>
        </div>
        """

        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })

        logger.info(f"[EMAIL] Email sent successfully to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email to {to_email}: {e}")
        return False
