import streamlit as st
import uuid
import re
from datetime import datetime
from db import get_connection
import hashlib

# ---------------- PASSWORD HASHING ----------------
def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- VALIDATION ----------------
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

# ---------------- DB OPERATIONS ----------------
def check_email_exists(email: str) -> bool:
    """Check if email already exists"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT email FROM property_manager WHERE email = %s",
            (email,)
        )
        result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_property_manager(name: str, address: str, email: str, phone: str, password: str):
    """Create new property manager"""
    manager_id = str(uuid.uuid4())
    hashed_password = hash_password(password)
    
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO property_manager
        (manager_id, manager_name, contact_address, email, phone, password, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            manager_id,
            name,
            address,
            email,
            phone,
            hashed_password,
            datetime.now()
        ))
    conn.commit()
    conn.close()
    return manager_id

def get_all_property_managers():
    """Get all property managers"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM property_manager ORDER BY created_date DESC"
        )
        rows = cursor.fetchall()
    conn.close()
    return rows

def update_property_manager(manager_id: str, name: str, address: str, phone: str):
    """Update property manager details (excluding email and password)"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE property_manager
        SET manager_name = %s,
            contact_address = %s,
            phone = %s
        WHERE manager_id = %s
        """
        cursor.execute(sql, (name, address, phone, manager_id))
    conn.commit()
    conn.close()

def update_manager_password(manager_id: str, new_password: str):
    """Update property manager password"""
    hashed_password = hash_password(new_password)
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE property_manager SET password = %s WHERE manager_id = %s",
            (hashed_password, manager_id)
        )
    conn.commit()
    conn.close()

def toggle_manager_status(manager_id: str, is_active: bool):
    """Activate or deactivate property manager"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE property_manager SET is_active = %s WHERE manager_id = %s",
            (is_active, manager_id)
        )
    conn.commit()
    conn.close()

# ---------------- PAGE UI ----------------
def show_property_manager_page():
    st.title("👤 Property Manager Registration")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    # ➕ NEW PROPERTY MANAGER
    with st.expander("➕ Register New Property Manager", expanded=True):
        st.subheader("Manager Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Manager Name *", key="new_name")
            email = st.text_input("Email *", key="new_email", 
                                 help="This will be used as login username")
            phone = st.text_input("Phone Number *", key="new_phone", 
                                 placeholder="+1 234 567 8900")
        
        with col2:
            address = st.text_area("Contact Address", key="new_address", height=100)
            password = st.text_input("Password *", type="password", key="new_password",
                                    help="Must be at least 8 characters with uppercase, lowercase, and numbers")
            confirm_password = st.text_input("Confirm Password *", type="password", 
                                           key="new_confirm_password")

        st.caption("* Required fields")

        if st.button("✅ Register Property Manager", type="primary", key="register_btn"):
            # Validation
            if not all([name, email, phone, password, confirm_password]):
                st.error("Please fill in all required fields")
            elif not validate_email(email):
                st.error("Please enter a valid email address")
            elif check_email_exists(email):
                st.error("This email is already registered")
            elif not validate_phone(phone):
                st.error("Please enter a valid phone number")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                is_valid, message = validate_password(password)
                if not is_valid:
                    st.error(message)
                else:
                    try:
                        manager_id = insert_property_manager(name, address, email, phone, password)
                        st.success(f"✅ Property Manager registered successfully!")
                        st.info(f"**Manager ID:** {manager_id}")
                        st.info(f"**Login Username:** {email}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error registering manager: {e}")

    st.divider()

    # EXISTING PROPERTY MANAGERS
    st.subheader("📋 Registered Property Managers")

    managers = get_all_property_managers()

    if not managers:
        st.info("No property managers registered yet")
        return

    # Summary
    active_count = sum(1 for m in managers if m['is_active'])
    st.caption(f"Total: {len(managers)} managers | Active: {active_count} | Inactive: {len(managers) - active_count}")

    for manager in managers:
        status_icon = "🟢" if manager['is_active'] else "🔴"
        status_text = "Active" if manager['is_active'] else "Inactive"
        
        with st.expander(f"{status_icon} {manager['manager_name']} - {status_text}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.text(f"📧 Email: {manager['email']}")
                st.text(f"📱 Phone: {manager['phone']}")
                st.text(f"📍 Address: {manager.get('contact_address', 'N/A')}")
            
            with col2:
                st.caption(f"🆔 ID: {manager['manager_id']}")
                st.caption(f"📅 Created: {manager['created_date']}")
                st.caption(f"Status: {status_text}")
            
            st.divider()
            
            # Edit form
            st.subheader("✏️ Edit Manager")
            
            edit_col1, edit_col2 = st.columns(2)
            
            with edit_col1:
                new_name = st.text_input(
                    "Manager Name",
                    manager['manager_name'],
                    key=f"name_{manager['manager_id']}"
                )
                
                new_phone = st.text_input(
                    "Phone Number",
                    manager['phone'],
                    key=f"phone_{manager['manager_id']}"
                )
            
            with edit_col2:
                new_address = st.text_area(
                    "Contact Address",
                    manager.get('contact_address', ''),
                    height=100,
                    key=f"address_{manager['manager_id']}"
                )
            
            # Update button
            if st.button("💾 Update Details", key=f"update_{manager['manager_id']}"):
                if not new_name or not new_phone:
                    st.error("Name and phone are required")
                elif not validate_phone(new_phone):
                    st.error("Invalid phone number")
                else:
                    try:
                        update_property_manager(
                            manager['manager_id'],
                            new_name,
                            new_address,
                            new_phone
                        )
                        st.success("✅ Manager details updated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating: {e}")
            
            st.divider()
            
            # Password reset
            with st.expander("🔒 Reset Password"):
                new_password = st.text_input(
                    "New Password",
                    type="password",
                    key=f"newpass_{manager['manager_id']}"
                )
                confirm_new_password = st.text_input(
                    "Confirm New Password",
                    type="password",
                    key=f"confirmpass_{manager['manager_id']}"
                )
                
                if st.button("🔑 Reset Password", key=f"reset_{manager['manager_id']}"):
                    if not new_password or not confirm_new_password:
                        st.error("Please enter both password fields")
                    elif new_password != confirm_new_password:
                        st.error("Passwords do not match")
                    else:
                        is_valid, message = validate_password(new_password)
                        if not is_valid:
                            st.error(message)
                        else:
                            try:
                                update_manager_password(manager['manager_id'], new_password)
                                st.success("✅ Password reset successfully!")
                            except Exception as e:
                                st.error(f"Error resetting password: {e}")
            
            st.divider()
            
            # Activate/Deactivate
            current_status = manager['is_active']
            action_btn = st.columns([1, 1])
            
            with action_btn[0]:
                if current_status:
                    if st.button("🔴 Deactivate Manager", key=f"deactivate_{manager['manager_id']}"):
                        toggle_manager_status(manager['manager_id'], False)
                        st.warning("Manager deactivated")
                        st.rerun()
                else:
                    if st.button("🟢 Activate Manager", key=f"activate_{manager['manager_id']}"):
                        toggle_manager_status(manager['manager_id'], True)
                        st.success("Manager activated")
                        st.rerun()

if __name__ == "__main__":
    show_property_manager_page()
