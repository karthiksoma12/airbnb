import bcrypt
import pymysql

def reset_password(username, new_password):
    password_hash = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = pymysql.connect(
    )

    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE user_details
            SET password = %s
            WHERE username = %s
            """,
            (password_hash, username)
        )

    conn.commit()
    conn.close()
    
    
if __name__ == "__main__":
    # Example usage
    reset_password("karthik", "Nothingnew@12")

