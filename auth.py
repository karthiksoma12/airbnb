import bcrypt
from db import get_connection
import hashlib

def hash_password_sha256(password: str) -> str:
    """Hash password using SHA256 (for property managers)"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user (admin or property manager)
    Returns: dict with user info or None
    """
    conn = get_connection()
    
    # First check if it's an admin (using bcrypt)
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM user_details WHERE username = %s",
            (username,)
        )
        admin = cursor.fetchone()
        
        if admin:
            # Check password with bcrypt
            try:
                if bcrypt.checkpw(password.encode(), admin['password'].encode()):
                    conn.close()
                    return {
                        'user_type': 'admin',
                        'username': admin['username'],
                        'user_id': admin.get('user_id', 'admin-001')
                    }
            except Exception as e:
                print(f"Bcrypt error: {e}")
    
    # Check if it's a property manager (using SHA256 and email as username)
    hashed_password = hash_password_sha256(password)
    
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM property_manager WHERE email = %s AND password = %s AND is_active = TRUE",
            (username, hashed_password)
        )
        manager = cursor.fetchone()
        
        if manager:
            conn.close()
            return {
                'user_type': 'property_manager',
                'username': manager['email'],
                'user_id': manager['manager_id'],
                'manager_name': manager['manager_name']
            }
    
    conn.close()
    return None

def verify_admin(username: str) -> bool:
    """Check if user is admin"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM user_details WHERE username = %s",
            (username,)
        )
        result = cursor.fetchone()
    conn.close()
    return result is not None
