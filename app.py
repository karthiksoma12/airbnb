import streamlit as st
from auth import authenticate_user

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"

# ---------------- CHECK FOR PUBLIC CHATBOT ACCESS ----------------
# Allow direct access to chatbot via URL without login
params = st.query_params

if ("guidebook" in params or "id" in params):
    # User is accessing chatbot via direct URL - bypass login
    st.session_state.page = "chatbot"
    # Skip login entirely for chatbot access
    if st.session_state.page == "chatbot":
        from pages.chatbot import main
        main()
        st.stop()  # Stop execution here, don't show login

# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- ROUTER (Admin Pages Only) ----------------
else:
    if st.session_state.page == "dashboard":
        from pages.dashboard import show_dashboard
        show_dashboard()

    elif st.session_state.page == "property":
        from pages.property_registration import show_property_page
        show_property_page()
    
    elif st.session_state.page == "guidebook":
        from pages.guidebook_registration import show_guidebook_page
        show_guidebook_page()

