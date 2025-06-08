import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Database configuration
DB_NAME = os.getenv('DB_NAME', 'default_db')  # Default values prevent crashes
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# Secret key for Flask sessions and encryption
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

# SMTP configuration for sending emails
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# URL of the login page (used in QR code generation and password reset links)
LOGIN_PAGE_URL = os.getenv('LOGIN_PAGE_URL', "http://localhost:5000/")

# Print to check if variables are loaded correctly
print("LOGIN_PAGE_URL:", LOGIN_PAGE_URL)
