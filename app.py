import streamlit as st
from auth import authenticate_user

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Property Management System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- SESSION INIT ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"

if "user_type" not in st.session_state:
    st.session_state.user_type = None

# ---------------- CHECK FOR PUBLIC CHATBOT ACCESS ----------------
params = st.query_params

if ("guidebook" in params or "id" in params):
    st.session_state.page = "chatbot"
    if st.session_state.page == "chatbot":
        from pages.chatbot import main
        main()
        st.stop()

# ---------------- LOGIN PAGE ----------------
if not st.session_state.logged_in:
    # Hide sidebar on login page
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {display: none;}
        .login-header {
            text-align: center;
            padding: 2rem 0;
        }
        .login-box {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Center login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-header">', unsafe_allow_html=True)
        st.title("🏢 Property Management System")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Login form
        with st.form("login_form"):
            st.subheader("🔐 Login")
            
            username = st.text_input(
                "Username / Email",
                placeholder="Enter your username or email",
                help="Admins: use username | Property Managers: use email"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            submit = st.form_submit_button("🔑 Login", use_container_width=True, type="primary")
            
            if submit:
                if not username or not password:
                    st.error("❌ Please enter both username and password")
                else:
                    with st.spinner("Authenticating..."):
                        user_info = authenticate_user(username, password)
                        
                        if user_info:
                            # Successful login
                            st.session_state.logged_in = True
                            st.session_state.username = user_info['username']
                            st.session_state.user_type = user_info['user_type']
                            st.session_state.user_id = user_info['user_id']
                            
                            if user_info['user_type'] == 'property_manager':
                                st.session_state.manager_name = user_info['manager_name']
                            
                            st.session_state.page = "dashboard"
                            
                            # Show welcome message
                            display_name = user_info.get('manager_name', username)
                            st.success(f"✅ Welcome, {display_name}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials. Please try again.")
        
        st.markdown("---")
        
        # Login hints
        with st.expander("ℹ️ Login Information"):
            st.info("""
            **For Administrators:**
            - Use your admin username
            - Use your admin password
            
            **For Property Managers:**
            - Use your registered email address
            - Use your manager password
            
            *Contact your administrator if you forgot your credentials.*
            """)
        
        st.markdown("---")
        st.caption("🏢 Property Management System v1.0")

# ---------------- SIDEBAR NAVIGATION ----------------
else:
    with st.sidebar:
        st.title("🏢 Property Management")
        st.markdown("---")
        
        # User info badge
        if st.session_state.user_type == "admin":
            st.success("🔑 **Administrator**")
        else:
            st.info("👤 **Property Manager**")
        
        display_name = st.session_state.get('manager_name', st.session_state.username)
        st.markdown(f"**User:** {display_name}")
        st.markdown("---")
        
        # Navigation Menu
        st.subheader("📋 Menu")
        
        # Dashboard (all users)
        if st.button("🏠 Dashboard", use_container_width=True, 
                    type="primary" if st.session_state.page == "dashboard" else "secondary"):
            st.session_state.page = "dashboard"
            st.rerun()
        
        # Property Managers (Admin only)
        if st.session_state.user_type == "admin":
            if st.button("👥 Property Managers", use_container_width=True,
                        type="primary" if st.session_state.page == "property_manager" else "secondary"):
                st.session_state.page = "property_manager"
                st.rerun()
        
        # Property Registration (all users)
        if st.button("🏢 Properties", use_container_width=True,
                    type="primary" if st.session_state.page == "property" else "secondary"):
            st.session_state.page = "property"
            st.rerun()
        
        # Guidebook Registration (all users)
        if st.button("📘 Guidebooks", use_container_width=True,
                    type="primary" if st.session_state.page == "guidebook" else "secondary"):
            st.session_state.page = "guidebook"
            st.rerun()
        
        # Chat Sessions (all users)
        if st.button("💬 Chat Sessions", use_container_width=True,
                    type="primary" if st.session_state.page == "chat_sessions" else "secondary"):
            st.session_state.page = "chat_sessions"
            st.rerun()
        
        st.markdown("---")
        
        # User info section
        with st.expander("ℹ️ Account Info"):
            st.caption(f"**Type:** {st.session_state.user_type.replace('_', ' ').title()}")
            if st.session_state.user_type == "admin":
                st.caption(f"**Username:** {st.session_state.username}")
            else:
                st.caption(f"**Email:** {st.session_state.username}")
            st.caption(f"**ID:** {st.session_state.user_id[:8]}...")
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.logged_in = False
            st.session_state.page = "login"
            st.rerun()

    # ---------------- ROUTER (MAIN CONTENT AREA) ----------------
    if st.session_state.page == "dashboard":
        from pages.dashboard import show_dashboard
        show_dashboard()

    elif st.session_state.page == "property_manager":
        # Admin-only page
        if st.session_state.user_type == "admin":
            from pages.property_manager_registration import show_property_manager_page
            show_property_manager_page()
        else:
            st.error("🚫 Access Denied")
            st.warning("This page is only accessible to administrators.")
            if st.button("⬅️ Back to Dashboard"):
                st.session_state.page = "dashboard"
                st.rerun()

    elif st.session_state.page == "property":
        from pages.property_registration import show_property_page
        show_property_page()
    
    elif st.session_state.page == "guidebook":
        from pages.guidebook_registration import show_guidebook_page
        show_guidebook_page()
    
    elif st.session_state.page == "chat_sessions":
        from pages.page_sessions import show_chat_sessions_page
        show_chat_sessions_page()


