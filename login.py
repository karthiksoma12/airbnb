import streamlit as st
import pymysql
import bcrypt
import uuid

# ================== DB CONNECTION ==================
def get_connection():
    return pymysql.connect(
       
    )

# ================== AUTH ==================
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

# ================== CREATE USER (ADMIN) ==================
def create_user(username, password):
    user_id = str(uuid.uuid4())[:45]
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_details (id, username, password)
                VALUES (%s, %s, %s)
                """,
                (user_id, username, password_hash)
            )
        conn.commit()
        conn.close()
        return True
    except pymysql.err.IntegrityError:
        return False

# ================== SESSION ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ================== UI ==================
st.set_page_config(page_title="Secure Login", layout="centered")
st.title("🔐 Login")

# ------------------ LOGIN PAGE ------------------
if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login successful ✅")
            st.rerun()
        else:
            st.error("Invalid username or password ❌")

# ------------------ DASHBOARD ------------------
else:
    st.success(f"Welcome, {st.session_state.username} 👋")
    st.divider()

    st.subheader("➕ Create New User")

    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Create User"):
        if new_password != confirm_password:
            st.error("Passwords do not match")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            if create_user(new_username, new_password):
                st.success("User created successfully 🎉")
            else:
                st.error("Username already exists")

    st.divider()

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

