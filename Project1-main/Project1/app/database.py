# app/database.py
import psycopg2
from app.config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

def get_db_connection():
    """
    Establish a connection to the PostgreSQL database using the environment variables.
    """
    return psycopg2.connect(
        dbname=DB_NAME, 
        user=DB_USER, 
        password=DB_PASSWORD,
        host=DB_HOST, 
        port=DB_PORT
    )
