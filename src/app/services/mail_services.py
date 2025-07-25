import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

tmp_logger = logging.getLogger(__name__)

# Utility to send raw emails via SMTP

def send_email(subject: str, body: str, recipient: str) -> bool:
    """
    Send an email via configured SMTP server.

    :param subject:   Email subject
    :param body:      Email body (plain text)
    :param recipient: Recipient email address
    :return:          True if sent successfully, False otherwise
    """
    email_acc = os.getenv("EMAIL_USER")
    email_pssw = os.getenv("EMAIL_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = email_acc
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_acc, email_pssw)
            server.sendmail(email_acc, recipient, msg.as_string())
        return True
    except Exception as e:
        # Consider logging this error in production
        if os.getenv("FLASK_ENV") == "development":
            print(f"Failed to send email to {recipient}: {e}")
        else:
            tmp_logger.error("Failed to send email to %s: %s", recipient, e)
        return False


# High-level email scenarios

def send_verification_email(username: str, token: str, recipient: str) -> bool:
    """
    Compose and send account verification code email.
    """
    subject = "ChatCLI Account Verification Code"
    body = f"""
Dear {username},

Thank you for registering with ChatCLI! To complete your registration, please enter the verification code below in the application:

Verification code: {token}

This code is valid for 5 minutes. If you didn’t request it, you can safely ignore this email.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
"""
    return send_email(subject, body, recipient)


def send_password_reset_email(username: str, token: str, recipient: str) -> bool:
    """
    Compose and send password reset instructions email.
    """
    reset_link = f"http://fortbow.zapto.org:5123/user/reset-password?token={token}&username={username}"
    subject = "Password Reset Request for Your ChatCLI Account"
    body = f"""
Dear {username},

We received a request to reset the password for your ChatCLI account. To continue, click the link below:

{reset_link}

If you didn’t request this, simply ignore this email.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
"""
    return send_email(subject, body, recipient)


def send_release_notification():
    """
    Notify all subscribers about a new ChatCLI release.
    """
    from app.database.db_helper import fetch_records

    # Fetch all subscriber emails
    rows = fetch_records(
        table="email_subscribers",
        fetch_all=True
    )
    emails = [r['email'] for r in rows]

    subject = "🎉 New ChatCLI Release Available!"
    body = """
Hello!

We’re excited to announce a new ChatCLI release! Highlights include:
• New features
• Bug fixes
• Performance improvements

For full details, visit our GitHub repository:
https://github.com/SciTechMC/ChatCLI

Thank you for using ChatCLI!

Best regards,
The ChatCLI Team
"""
    success = True
    for email in emails:
        if not send_email(subject, body, email):
            success = False
    return success

def send_account_disable_notification(username: str, recipient: str) -> bool:
    """
    Notify user about account disablement.
    """
    subject = "Your ChatCLI Account Has Been Disabled"
    body = f"""
Dear {username},

Your ChatCLI account has been disabled. You will not be able to log in until you reactivate it by submitting a request via email.

If you did not request this, please contact support immediately.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
"""
    return send_email(subject, body, recipient)

def send_account_deletion_notification(username: str, recipient: str) -> bool:
    """
    Notify user about account deletion.
    """
    subject = "Your ChatCLI Account Has Been Deleted"
    body = f"""
Dear {username},

Your ChatCLI account has been permanently deleted along with all associated data, including messages and chats.

If you did not request this, please contact support immediately.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
"""
    return send_email(subject, body, recipient)

def send_email_change_verification(username: str, token: str, recipient: str) -> bool:
    """
    Compose and send email‐change verification code.
    """
    subject = "ChatCLI Email Change Confirmation Code"
    body = f"""
Dear {username},

You requested to change your ChatCLI account’s email address. To confirm this change, please enter the code below in the application:

Confirmation code: {token}

This code is valid for 5 minutes. If you did not request this change, please ignore this email or contact support.

Best regards,
The ChatCLI Team
https://github.com/SciTechMC/ChatCLI
"""
    return send_email(subject, body, recipient)