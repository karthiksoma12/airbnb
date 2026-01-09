import streamlit as st
import uuid
from datetime import datetime
from db import get_connection

# ---------------- DB OPS ----------------
def get_properties():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM property_registration")
        rows = cursor.fetchall()
    conn.close()
    return rows

def insert_property(address, user):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO property_registration
            (propId, property_address,created_date, created_by)
            VALUES (%s, %s, %s,%s)
            """,
            (str(uuid.uuid4()), address, datetime.now(),user)
        )
    conn.commit()
    conn.close()

def update_property(prop_id, address, user):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE property_registration
            SET property_address=%s,
                modified_date=%s,
                modified_by=%s
            WHERE propId=%s
            """,
            (address, datetime.now(), user, prop_id)
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

    # ➕ NEW PROPERTY
    with st.expander("➕ Register New Property"):
        address = st.text_area("Property Address")

        if st.button("Save Property"):
            if address.strip():
                insert_property(address, st.session_state.username)
                st.success("Property registered ✅")
                st.rerun()
            else:
                st.error("Address required")

    st.divider()

    # EXISTING PROPERTIES
    st.subheader("🏘 Existing Properties")

    properties = get_properties()

    if not properties:
        st.info("No properties found")
    else:
        for prop in properties:
            with st.expander(prop["property_address"][:40]):
                new_addr = st.text_area(
                    "Property Address",
                    prop["property_address"],
                    key=prop["propId"]
                )

                st.text(f"Created At: {prop['created_date']}")
                st.text(f"Created By: {prop['created_by']}")
                st.text(f"Modified At: {prop['modified_date']}")
                st.text(f"Modified By: {prop['modified_by']}")

                if st.button("Update", key=f"upd_{prop['propId']}"):
                    update_property(
                        prop["propId"],
                        new_addr,
                        st.session_state.username
                    )
                    st.success("Updated ✏️")
                    st.rerun()
