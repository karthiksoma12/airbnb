import pymysql

def get_connection():
    return pymysql.connect(
        host="whereisit-karthiksomasundaram598-2d46.l.aivencloud.com",
        user="avnadmin",
        password="AVNS_X8yJEAfpgmX7ZH-NkDy",  # 🔴 add password
        database="property_management",
        port=17028,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
