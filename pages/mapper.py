import streamlit as st
import uuid
from datetime import datetime
from db import get_connection

# ---------------- DB FETCH ----------------
def get_properties():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT propId, property_address FROM property_registration")
        rows = cursor.fetchall()
    conn.close()
    return rows


def get_guidebooks():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT guideid, guidebook_title FROM guidebook_registration")
        rows = cursor.fetchall()
    conn.close()
    return rows


def get_mappings():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT m.id, p.property_address, g.guidebook_title,
                   m.created_date, m.created_by,
                   m.modified_date, m.modified_by,
                   m.propid, m.guideid
            FROM mapper m
            JOIN property_registration p ON p.propId = m.propid
            JOIN guidebook_registration g ON g.guideid = m.guideid
            ORDER BY m.created_date DESC
        """)
        rows = cursor.fetchall()
    conn.close()
    return rows


# ---------------- DB WRITE ----------------
def insert_mapping(propid, guideid, user):
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO mapper
        (id, propid, guideid, created_by)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (
            str(uuid.uuid4()),
            propid,
            guideid,
            user
        ))
    conn.commit()
    conn.close()


def update_mapping(mapper_id, propid, guideid, user):
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE mapper
        SET propid=%s,
            guideid=%s,
            modified_date=%s,
            modified_by=%s
        WHERE id=%s
        """
        cursor.execute(sql, (
            propid,
            guideid,
            datetime.now(),
            user,
            mapper_id
        ))
    conn.commit()
    conn.close()


# ---------------- PAGE UI ----------------
def show_mapper_page():
    st.title("🔗 Property ↔ Guidebook Mapping")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    properties = get_properties()
    guidebooks = get_guidebooks()

    if not properties or not guidebooks:
        st.warning("Add properties and guidebooks before mapping")
        return

    prop_options = {p["property_address"]: p["propId"] for p in properties}
    guide_options = {g["guidebook_title"]: g["guideid"] for g in guidebooks}

    # ---------- NEW MAPPING ----------
    st.subheader("➕ Create Mapping")

    col1, col2 = st.columns(2)

    with col1:
        selected_prop = st.selectbox("Select Property", prop_options.keys())

    with col2:
        selected_guide = st.selectbox("Select Guidebook", guide_options.keys())

    if st.button("🔗 Map Property & Guidebook"):
        insert_mapping(
            prop_options[selected_prop],
            guide_options[selected_guide],
            st.session_state.username
        )
        st.success("Mapping created ✅")
        st.rerun()

    st.divider()

    # ---------- EXISTING MAPPINGS ----------
    st.subheader("📌 Existing Mappings")

    mappings = get_mappings()

    if not mappings:
        st.info("No mappings found")
        return

    for m in mappings:
        with st.expander(f"{m['property_address']} ↔ {m['guidebook_title']}"):
            col1, col2 = st.columns(2)

            with col1:
                new_prop = st.selectbox(
                    "Property",
                    prop_options.keys(),
                    index=list(prop_options.values()).index(m["propid"]),
                    key=f"p_{m['id']}"
                )

            with col2:
                new_guide = st.selectbox(
                    "Guidebook",
                    guide_options.keys(),
                    index=list(guide_options.values()).index(m["guideid"]),
                    key=f"g_{m['id']}"
                )

            st.text(f"Created: {m['created_date']} by {m['created_by']}")
            st.text(f"Modified: {m['modified_date']} by {m['modified_by']}")

            if st.button("Update Mapping", key=f"upd_{m['id']}"):
                update_mapping(
                    m["id"],
                    prop_options[new_prop],
                    guide_options[new_guide],
                    st.session_state.username
                )
                st.success("Mapping updated ✏️")
                st.rerun()
