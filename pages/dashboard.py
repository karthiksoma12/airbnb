import streamlit as st

def show_dashboard():
    st.title("📊 Dashboard")
    st.success(f"Welcome, {st.session_state.username}")
    
    
    if st.button("💬 View Chat Sessions", use_container_width=True):
        st.session_state.page = "chat_sessions"
        st.rerun()

    col1, col2,col3 = st.columns(3)

    with col1:
        if st.button("🏠 Property Registration"):
            st.session_state.page = "property"
            st.rerun()

    with col2:
        if st.button("📚 Guidebook Registration"):
            st.session_state.page = "guidebook"
            st.rerun()

    with col3:
        if st.button("👥 Property Managers"):
            st.session_state.page = "property_manager"
            st.rerun()

    st.divider()

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()
