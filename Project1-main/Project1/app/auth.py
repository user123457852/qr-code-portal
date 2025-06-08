# app/auth.py
import os, json, string, random, bcrypt
from app.config import SECRET_KEY

SUB_MAP_FILE = "substitution_map.json"

def load_or_generate_substitution_map():
    """
    Load a character substitution map from a JSON file or generate a new one if it does not exist.
    This map is used to obfuscate passwords before hashing.
    """
    if os.path.exists(SUB_MAP_FILE):
        with open(SUB_MAP_FILE, "r") as f:
            return json.load(f)
    original_chars = string.ascii_letters + string.digits + string.punctuation
    shuffled_chars = list(original_chars)
    random.shuffle(shuffled_chars)
    substitution_map = dict(zip(original_chars, shuffled_chars))
    with open(SUB_MAP_FILE, "w") as f:
        json.dump(substitution_map, f)
    return substitution_map

SUBSTITUTION_MAP = load_or_generate_substitution_map()

def substitute_chars(password: str) -> str:
    """
    Substitute each character in the password with its mapped character for extra obfuscation.
    """
    return ''.join(SUBSTITUTION_MAP.get(c, c) for c in password)

def hash_password(password: str) -> str:
    """
    Substitute and then hash a password using bcrypt.
    """
    substituted_password = substitute_chars(password)
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(substituted_password.encode(), salt)
    return hashed_password.decode()

def verify_password(input_password: str, stored_hash: str) -> bool:
    """
    Verify an input password against the stored hashed password.
    """
    substituted_input = substitute_chars(input_password)
    return bcrypt.checkpw(substituted_input.encode(), stored_hash.encode())

def generate_random_password(length: int = 12) -> str:
    """
    Generate a random password using letters, digits, and punctuation.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def login_user(user_id: int, input_password: str, user_type: str) -> bool:
    """
    Verify a user's credentials by comparing the provided password against the stored hash.
    """
    from app.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    table = "admins" if user_type == "admin" else "clinicians"
    id_column = "admin_id" if user_type == "admin" else "clinician_id"
    cursor.execute(f"SELECT password_hash FROM {table} WHERE {id_column} = %s", (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        stored_hash = result[0]
        return verify_password(input_password, stored_hash)
    else:
        return False
