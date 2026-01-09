import bcrypt
from db import get_connection

def authenticate_user(username, password):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT password FROM user_details WHERE username=%s",
            (username,)
        )
        user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
        return True
    return False
