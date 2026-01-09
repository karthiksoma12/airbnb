import streamlit as st
import uuid
import base64
from io import BytesIO
from datetime import datetime
import qrcode
from db import get_connection

# ---------------- QR GENERATOR ----------------
def generate_qr_base64(url: str) -> str:
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

# ---------------- DB OPS ----------------
def get_guidebooks():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM guidebook_registration ORDER BY created_date DESC"
        )
        rows = cursor.fetchall()
    conn.close()
    return rows


def insert_guidebook(title, text, url, user):
    qr_base64 = generate_qr_base64(url)

    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO guidebook_registration
        (guideid, guidebook_title, guide_text, guide_url, qr_code_base64, created_by,created_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            str(uuid.uuid4()),
            title,
            text,
            url,
            qr_base64,
            user, datetime.now()
        ))
    conn.commit()
    conn.close()


def update_guidebook(guideid, title, text, url, user):
    qr_base64 = generate_qr_base64(url)

    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE guidebook_registration
        SET guidebook_title=%s,
            guide_text=%s,
            guide_url=%s,
            qr_code_base64=%s,
            modified_date=%s,
            modified_by=%s
        WHERE guideid=%s
        """
        cursor.execute(sql, (
            title,
            text,
            url,
            qr_base64,
            datetime.now(),
            user,
            guideid
        ))
    conn.commit()
    conn.close()

# ---------------- PAGE UI ----------------
def show_guidebook_page():
    st.title("📘 Guidebook Registration")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    # ➕ NEW GUIDEBOOK
    with st.expander("➕ Create New Guidebook"):
        title = st.text_input("Guidebook Title")
        url = st.text_input("Guide URL")
        text = st.text_area("Guide Content", height=150)

        if st.button("Save Guidebook"):
            if not (title and text and url):
                st.error("All fields are required")
                return

            insert_guidebook(title, text, url, st.session_state.username)
            st.success("Guidebook created ✅")
            st.rerun()

    st.divider()

    # EXISTING GUIDEBOOKS
    st.subheader("📚 Existing Guidebooks")

    guidebooks = get_guidebooks()

    if not guidebooks:
        st.info("No guidebooks found")
        return

    for g in guidebooks:
        with st.expander(g["guidebook_title"]):
            new_title = st.text_input(
                "Guidebook Title",
                g["guidebook_title"],
                key=f"title_{g['guideid']}"
            )

            new_url = st.text_input(
                "Guide URL",
                g["guide_url"],
                key=f"url_{g['guideid']}"
            )

            new_text = st.text_area(
                "Guide Content",
                g["guide_text"],
                height=120,
                key=f"text_{g['guideid']}"
            )

            # QR DISPLAY
            qr_bytes = base64.b64decode(g["qr_code_base64"])
            st.image(qr_bytes, width=150, caption="QR Code")

            st.caption(f"🆔 {g['guideid']}")
            st.text(f"Created: {g['created_date']} by {g['created_by']}")
            st.text(f"Modified: {g['modified_date']} by {g['modified_by']}")

            if st.button("Update Guidebook", key=f"upd_{g['guideid']}"):
                update_guidebook(
                    g["guideid"],
                    new_title,
                    new_text,
                    new_url,
                    st.session_state.username
                )
                st.success("Updated ✏️")
                st.rerun()
