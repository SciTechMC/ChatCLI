import os
from app.services.base_services import get_db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject, body, recipient):
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
            print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")


def notify_subscribers():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT email FROM email_subscribers")
        subscribers = cursor.fetchall()

        subject = "🎉 New ChatCLI Release Available!"
        body = """
        Hello,

        We're excited to announce a new release of ChatCLI! Here are some highlights:
        - New features
        - Bug fixes
        - Performance improvements

        Visit our GitHub page for more details: https://github.com/SciTechMC/ChatCLI

        Thank you for staying with us!

        Best,
        ChatCLI Team
        """
        for subscriber in subscribers:
            send_email(subject, body, subscriber["email"])
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    notify_subscribers()