# app/email_helpers.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.policy import compat32
from app.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

def send_email(to_email, subject, body):
    """
    Send an email using SMTP.
    
    Constructs a multipart email using the compat32 policy for headers and ensures proper encoding.
    """
    msg = MIMEMultipart(policy=compat32)
    msg["From"] = Header(str(SMTP_USERNAME), 'utf-8')
    msg["To"] = Header(str(to_email), 'utf-8')
    msg["Subject"] = Header(str(subject), 'utf-8')
    msg.attach(MIMEText(body, "plain", 'utf-8'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Upgrade connection to secure TLS
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print("Error sending email:")
        import traceback
        traceback.print_exc()

def send_credentials_email(to_email, user_name, user_id, temp_password, login_url):
    """
    Send an email with newly created clinician account credentials.
    """
    subject = "Your New Account Login Credentials"
    body = (
        f"Dear {user_name},\n\n"
        "We are pleased to inform you that your account has been successfully created. Please find your login credentials below:\n\n"
        f"Your clinician ID: {user_id}\n"
        f"Temporary Password: {temp_password}\n\n"
        f"To access your account, please visit the following link: {login_url}\n\n"
        "For security purposes, we strongly recommend that you log in immediately and change your temporary password to a secure, personalized one.\n\n"
        "If you have any questions or require further assistance, please do not hesitate to contact our support team.\n\n"
        "Sincerely,\n"
        "Braining Team"
    )
    send_email(to_email, subject, body)
