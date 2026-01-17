import streamlit as st

def show_dashboard():
    st.title("📊 Dashboard")
    st.success(f"Welcome, {st.session_state.username}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏠 Property Registration"):
            st.session_state.page = "property"
            st.rerun()

    with col2:
        if st.button("📚 Guidebook Registration"):
            st.session_state.page = "guidebook"
            st.rerun()

    st.divider()

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()
