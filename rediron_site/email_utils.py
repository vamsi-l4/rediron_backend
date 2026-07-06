import logging
from typing import Iterable, Optional
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError

logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Raised when an email could not be sent."""


def send_email_message(
    subject: str,
    message: str,
    recipient_list: Iterable[str],
    *,
    from_email: Optional[str] = None,
    html_message: Optional[str] = None,
    fail_silently: bool = False,
) -> bool:
    """Send an email through the configured Django email backend.

    Returns True when the backend reports at least one successful recipient.
    Logs failures and never raises for normal request handling.
    """
    recipients = [recipient for recipient in recipient_list if recipient]
    if not recipients:
        logger.warning("Email skipped: no recipients for subject '%s'", subject)
        return False

    sender = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    if not sender:
        logger.warning("Email skipped: no FROM address configured for subject '%s'", subject)
        return False

    try:
        delivered = send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=fail_silently,
        )
    except BadHeaderError:
        logger.exception("Email failed due to invalid header for subject '%s'", subject)
        if fail_silently:
            return False
        raise EmailServiceError("Invalid email header")
    except Exception:
        logger.exception(
            "Email sending failed for subject '%s' via host=%s port=%s tls=%s ssl=%s user_configured=%s from=%s recipients=%s",
            subject,
            getattr(settings, "EMAIL_HOST", None),
            getattr(settings, "EMAIL_PORT", None),
            getattr(settings, "EMAIL_USE_TLS", None),
            getattr(settings, "EMAIL_USE_SSL", None),
            bool(getattr(settings, "EMAIL_HOST_USER", None)),
            sender,
            recipients,
        )
        if fail_silently:
            return False
        raise EmailServiceError("Email delivery failed")

    if delivered is not None and int(delivered) < 1:
        logger.warning("Email backend reported zero deliveries for subject '%s'", subject)
        return False

    logger.info("Email sent successfully subject='%s' recipients=%s", subject, recipients)
    return True


def send_admin_notification(subject: str, message: str, *, html_message: Optional[str] = None) -> bool:
    admin_email = getattr(settings, "ADMIN_EMAIL", None) or getattr(settings, "SITE_OWNER_EMAIL", None) or getattr(settings, "SHOP_ADMIN_EMAIL", None)
    if not admin_email:
        logger.warning("Admin email skipped because no ADMIN_EMAIL configured")
        return False
    try:
        return send_email_message(subject, message, [admin_email], html_message=html_message)
    except EmailServiceError:
        return False


def send_user_email(subject: str, recipient: str | object, message: str, *, html_message: Optional[str] = None) -> bool:
    if not recipient:
        logger.warning("User email skipped because recipient is empty")
        return False

    recipient_email = None
    if hasattr(recipient, 'email'):
        recipient_email = getattr(recipient, 'email')
    elif isinstance(recipient, str):
        recipient_email = recipient

    if not recipient_email:
        logger.warning("User email skipped because recipient email is empty")
        return False

    try:
        return send_email_message(subject, message, [recipient_email], html_message=html_message)
    except EmailServiceError:
        logger.exception("Failed to send user email to %s", recipient_email)
        return False
