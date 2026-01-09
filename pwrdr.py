import bcrypt
import pymysql

def reset_password(username, new_password):
    password_hash = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = pymysql.connect(
        host="whereisit-karthiksomasundaram598-2d46.l.aivencloud.com",
        user="avnadmin",
        password="AVNS_X8yJEAfpgmX7ZH-NkDy",  # add password
        database="property_management",
        port=17028,
        cursorclass=pymysql.cursors.DictCursor
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
