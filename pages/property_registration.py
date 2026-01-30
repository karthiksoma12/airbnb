import streamlit as st
import uuid
from datetime import datetime
from db import get_connection

# ---------------- DB OPS ----------------
def get_all_property_managers():
    """Get all active property managers"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT manager_id, manager_name, email FROM property_manager WHERE is_active = TRUE ORDER BY manager_name"
        )
        rows = cursor.fetchall()
    conn.close()
    return rows

def get_properties():
    """Get properties based on user type"""
    conn = get_connection()
    with conn.cursor() as cursor:
        if st.session_state.get('user_type') == "property_manager":
            # Property manager sees only their properties
            cursor.execute(
                """
                SELECT p.*, pm.manager_name 
                FROM property_registration p
                LEFT JOIN property_manager pm ON p.manager_id = pm.manager_id
                WHERE p.manager_id = %s 
                ORDER BY p.created_date DESC
                """,
                (st.session_state.user_id,)
            )
        else:
            # Admin sees all properties
            cursor.execute(
                """
                SELECT p.*, pm.manager_name 
                FROM property_registration p
                LEFT JOIN property_manager pm ON p.manager_id = pm.manager_id
                ORDER BY p.created_date DESC
                """
            )
        rows = cursor.fetchall()
    conn.close()
    return rows

def insert_property(address, user, manager_id=None):
    """Create new property"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO property_registration
            (propId, property_address, created_date, created_by, manager_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), address, datetime.now(), user, manager_id)
        )
    conn.commit()
    conn.close()

def update_property(prop_id, address, user, manager_id=None):
    """Update property"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE property_registration
            SET property_address=%s,
                modified_date=%s,
                modified_by=%s,
                manager_id=%s
            WHERE propId=%s
            """,
            (address, datetime.now(), user, manager_id, prop_id)
        )
    conn.commit()
    conn.close()

# ---------------- PAGE UI ----------------
def show_property_page():
    st.title("🏠 Property Registration")

    if st.button("⬅ Back"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    # Show user info
    if st.session_state.get('user_type') == "property_manager":
        st.info(f"👤 Viewing properties for: **{st.session_state.get('manager_name')}**")
        st.divider()

    # ➕ NEW PROPERTY
    with st.expander("➕ Register New Property", expanded=True):
        address = st.text_area("Property Address *", height=100, 
                              placeholder="Enter full property address...")

        # Property Manager Assignment (Admin only or auto-assign for managers)
        if st.session_state.get('user_type') == "admin":
            st.divider()
            st.subheader("👤 Assign Property Manager")
            
            managers = get_all_property_managers()
            
            if managers:
                manager_options = {"-- None --": None}
                manager_options.update({
                    f"{m['manager_name']} ({m['email']})": m['manager_id'] 
                    for m in managers
                })
                
                selected_manager = st.selectbox(
                    "Property Manager",
                    options=list(manager_options.keys()),
                    key="new_manager",
                    help="Select a property manager to assign this property to"
                )
                
                manager_id = manager_options[selected_manager]
            else:
                st.warning("⚠️ No property managers available")
                manager_id = None
        else:
            # Property manager creating property - auto-assign to themselves
            manager_id = st.session_state.user_id

        if st.button("💾 Save Property", type="primary"):
            if address.strip():
                insert_property(address, st.session_state.username, manager_id)
                st.success("✅ Property registered successfully!")
                st.rerun()
            else:
                st.error("❌ Property address is required")

    st.divider()

    # EXISTING PROPERTIES
    st.subheader("🏘️ Existing Properties")

    properties = get_properties()

    if not properties:
        if st.session_state.get('user_type') == "property_manager":
            st.info("📭 No properties assigned to you yet")
        else:
            st.info("📭 No properties registered yet")
    else:
        # Show count
        st.caption(f"Total Properties: {len(properties)}")
        
        for prop in properties:
            # Property title with manager info
            manager_info = ""
            if prop.get('manager_name'):
                manager_info = f" | 👤 {prop['manager_name']}"
            
            with st.expander(f"📍 {prop['property_address'][:50]}...{manager_info}"):
                # Property details
                new_addr = st.text_area(
                    "Property Address",
                    prop["property_address"],
                    height=100,
                    key=f"addr_{prop['propId']}"
                )

                # Manager assignment (Admin only)
                if st.session_state.get('user_type') == "admin":
                    st.divider()
                    st.subheader("👤 Property Manager")
                    
                    managers = get_all_property_managers()
                    
                    if managers:
                        # Get current manager
                        current_manager = None
                        if prop.get('manager_id'):
                            for m in managers:
                                if m['manager_id'] == prop['manager_id']:
                                    current_manager = f"{m['manager_name']} ({m['email']})"
                                    break
                        
                        manager_options = {"-- None --": None}
                        manager_options.update({
                            f"{m['manager_name']} ({m['email']})": m['manager_id'] 
                            for m in managers
                        })
                        
                        # Set default to current manager or None
                        default_index = 0
                        if current_manager and current_manager in manager_options:
                            default_index = list(manager_options.keys()).index(current_manager)
                        
                        selected_manager = st.selectbox(
                            "Assign to Property Manager",
                            options=list(manager_options.keys()),
                            index=default_index,
                            key=f"manager_{prop['propId']}"
                        )
                        
                        new_manager_id = manager_options[selected_manager]
                    else:
                        st.warning("No property managers available")
                        new_manager_id = None
                else:
                    # Property manager cannot change assignment
                    new_manager_id = prop.get('manager_id')
                    if prop.get('manager_name'):
                        st.info(f"👤 Managed by: **{prop['manager_name']}**")

                st.divider()

                # Metadata
                col1, col2 = st.columns(2)
                
                with col1:
                    st.caption(f"🆔 ID: {prop['propId']}")
                    st.caption(f"📅 Created: {prop['created_date']}")
                    st.caption(f"👤 Created By: {prop['created_by']}")
                
                with col2:
                    if prop.get('modified_date'):
                        st.caption(f"📝 Modified: {prop['modified_date']}")
                        st.caption(f"👤 Modified By: {prop.get('modified_by', 'N/A')}")

                # Update button
                if st.button("💾 Update Property", key=f"upd_{prop['propId']}", type="primary"):
                    if not new_addr.strip():
                        st.error("Property address cannot be empty")
                    else:
                        update_property(
                            prop["propId"],
                            new_addr,
                            st.session_state.username,
                            new_manager_id
                        )
                        st.success("✅ Property updated successfully!")
                        st.rerun()

if __name__ == "__main__":
    show_property_page()
