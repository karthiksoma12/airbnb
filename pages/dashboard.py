import streamlit as st

def show_dashboard():
    st.title("📊 Dashboard")
    st.success(f"Welcome, {st.session_state.username}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🏠 Property Registration"):
            st.session_state.page = "property"
            st.rerun()

    with col2:
        if st.button("📚 Guidebook Registration"):
            st.session_state.page = "guidebook"
            st.rerun()
        
    with col3:
        if st.button("🔗 Property-Guidebook Mapping"):
            st.session_state.page = "mapper"
            st.rerun()
    
    with st.expander("💬 Chat with Guidebook"):
        if st.button("Go to Chatbot"):
            st.session_state.page = "chatbot"
            st.rerun()

    st.divider()

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()
