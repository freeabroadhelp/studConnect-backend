import os, smtplib, logging, socket
from email.message import EmailMessage
from contextlib import closing

logger = logging.getLogger("otp_mail")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USER
APP_NAME = os.getenv("APP_NAME", "YourNextUniversity")
SMTP_DISABLE = os.getenv("SMTP_DISABLE", "0") == "1"      # new: force-disable sending
SMTP_STRICT = os.getenv("SMTP_STRICT", "0") == "1"        # new: raise on any failure (production)

def _smtp_config_complete() -> bool:
    return all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM])

def smtp_diagnostics() -> dict:
    """
    Returns a quick diagnostic dict (does not attempt authentication unless host resolves).
    """
    diag = {
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "user_present": bool(SMTP_USER),
        "password_present": bool(SMTP_PASSWORD),
        "from": SMTP_FROM,
        "resolves": None,
        "can_connect": None,
        "disabled": SMTP_DISABLE,
        "strict": SMTP_STRICT,
        "complete_config": _smtp_config_complete()
    }
    if not SMTP_HOST:
        return diag
    try:
        socket.gethostbyname(SMTP_HOST)
        diag["resolves"] = True
    except socket.gaierror:
        diag["resolves"] = False
        return diag
    # Try TCP connect
    try:
        with closing(socket.create_connection((SMTP_HOST, SMTP_PORT), timeout=5)):
            diag["can_connect"] = True
    except OSError:
        diag["can_connect"] = False
    return diag

def send_otp(email: str, code: str) -> bool:
    """
    Send OTP via SMTP. Returns True if we consider it 'sent'.
    Honors:
      - SMTP_DISABLE=1 : always succeed, log code (dev)
      - SMTP_STRICT=1  : any failure => return False
    """
    subject = f"{APP_NAME} Email Verification Code"
    text_body = (
        f"Hi,\n\nYour {APP_NAME} verification code is: {code}\n"
        "It expires in a few minutes. If you did not initiate this request, please ignore this message.\n\n"
        f"Regards,\n{APP_NAME} Team"
    )

    if SMTP_DISABLE:
        logger.warning("[SMTP_DISABLED] OTP for %s -> %s", email, code)
        return True

    if not _smtp_config_complete():
        logger.warning("[SMTP_FALLBACK] Incomplete SMTP config; OTP=%s email=%s", code, email)
        return not SMTP_STRICT  # succeed if not strict

    # Pre-flight resolution / connection diagnostics
    diag = smtp_diagnostics()
    if not diag.get("resolves"):
        logger.error("SMTP host resolution failed: %s (OTP=%s)", SMTP_HOST, code)
        return not SMTP_STRICT
    if diag.get("can_connect") is False:
        logger.error("SMTP host unreachable (port %s): %s (OTP=%s)", SMTP_PORT, SMTP_HOST, code)
        return not SMTP_STRICT

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = email
    msg.set_content(text_body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Sent OTP email to %s", email)
        return True
    except (smtplib.SMTPException, OSError, socket.error) as e:
        logger.error("Failed sending OTP email to %s: %s", email, e)
        return not SMTP_STRICT

def send_email(to_email: str, subject: str, message: str) -> bool:
    """
    Send a plain text email via SMTP.
    Returns True if sent, False otherwise.
    """
    if SMTP_DISABLE:
        logger.warning("[SMTP_DISABLED] Email for %s -> %s", to_email, subject)
        return True

    if not _smtp_config_complete():
        logger.warning("[SMTP_FALLBACK] Incomplete SMTP config; email=%s subject=%s", to_email, subject)
        return not SMTP_STRICT

    diag = smtp_diagnostics()
    if not diag.get("resolves"):
        logger.error("SMTP host resolution failed: %s (email=%s)", SMTP_HOST, to_email)
        return not SMTP_STRICT
    if diag.get("can_connect") is False:
        logger.error("SMTP host unreachable (port %s): %s (email=%s)", SMTP_PORT, SMTP_HOST, to_email)
        return not SMTP_STRICT

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(message)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info("Sent email to %s", to_email)
        return True
    except (smtplib.SMTPException, OSError, socket.error) as e:
        logger.error("Failed sending email to %s: %s", to_email, e)
        return not SMTP_STRICT
