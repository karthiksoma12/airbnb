import streamlit as st
from auth import authenticate_user

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"

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

# ---------------- ROUTER ----------------
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
    elif st.session_state.page == "mapper":
        from pages.mapper import show_mapper_page
        show_mapper_page()
    elif st.session_state.page == "chatbot":
        from pages.chatbot import show_property_chatbot
        show_property_chatbot()
