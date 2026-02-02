from fastapi_mail import ConnectionConfig, MessageSchema

from app.core.config import get_settings


def get_mailer_config() -> ConnectionConfig:
    """Retrieve email configuration settings."""
    settings = get_settings()
    return ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_FROM,
        MAIL_PASSWORD=settings.SMTP_PASSWORD,
        MAIL_FROM=settings.SMTP_FROM,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_STARTTLS=settings.SMTP_STARTTLS,
        MAIL_SSL_TLS=settings.SMTPL_SSL_TLS,
        USE_CREDENTIALS=settings.SMTP_USE_CREDENTIALS,
        VALIDATE_CERTS=settings.SMTP_VALIDATE_CERTS,
    )


def prepare_message(email: str, activation_token: str) -> MessageSchema:
    """Prepare the email message for account activation."""
    subject = "Activate Your Account"
    body = f"""Please use the following link to
    activate your account: http://localhost:8000/api/v1/users/activate/{activation_token}"""
    return MessageSchema(
        subject=subject, recipients=[email], body=body, subtype="plain"
    )
