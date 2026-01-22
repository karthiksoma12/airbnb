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

# ---------------- GENERATE CHATBOT URL ----------------
def generate_chatbot_url(guidebook_title: str) -> str:
    """Generate a clean URL for the guidebook chatbot"""
    slug = guidebook_title.lower().replace(" ", "_").replace("-", "_")
    slug = ''.join(c for c in slug if c.isalnum() or c == '_')
    
    try:
        base_url = st.context.headers.get("Host", "localhost:8501")
        protocol = "https://" if "localhost" not in base_url else "http://"
    except:
        base_url = "localhost:8501"
        protocol = "http://"
    
    return f"{protocol}{base_url}?guidebook={slug}"

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


def insert_guidebook(title, text, original_url, description, user):
    # Generate chatbot URL based on title
    chatbot_url = generate_chatbot_url(title)
    
    # Generate QR code for the chatbot URL
    qr_base64 = generate_qr_base64(chatbot_url)

    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO guidebook_registration
        (guideid, guidebook_title, guide_text, guide_original_url, guide_chatbot_url, 
         chatbot_description, qr_code_base64, created_by, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            str(uuid.uuid4()),
            title,
            text,
            original_url,
            chatbot_url,
            description,
            qr_base64,
            user,
            datetime.now()
        ))
    conn.commit()
    conn.close()
    
    return chatbot_url, qr_base64


def update_guidebook(guideid, title, text, original_url, description, user):
    # Regenerate chatbot URL based on new title
    chatbot_url = generate_chatbot_url(title)
    
    # Regenerate QR code for the new chatbot URL
    qr_base64 = generate_qr_base64(chatbot_url)

    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE guidebook_registration
        SET guidebook_title=%s,
            guide_text=%s,
            guide_original_url=%s,
            guide_chatbot_url=%s,
            chatbot_description=%s,
            qr_code_base64=%s,
            modified_date=%s,
            modified_by=%s
        WHERE guideid=%s
        """
        cursor.execute(sql, (
            title,
            text,
            original_url,
            chatbot_url,
            description,
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
    with st.expander("➕ Create New Guidebook", expanded=True):
        title = st.text_input("Guidebook Title")
        
        description = st.text_input(
            "Chatbot Description", 
            placeholder="Ask me anything about this guidebook!",
            help="This message will appear at the top of the chatbot"
        )
        
        original_url = st.text_input("Original Guide URL", placeholder="https://example.com/guide")
        text = st.text_area("Guide Content", height=150)

        if st.button("Save Guidebook", type="primary"):
            if not (title and text and original_url):
                st.error("Title, Guide Content, and Original URL are required")
            else:
                # Use default description if not provided
                final_description = description if description else "Ask me anything about this guidebook!"
                
                chatbot_url, qr_base64 = insert_guidebook(
                    title, text, original_url, final_description, st.session_state.username
                )
                
                # Show success with generated URL and QR
                st.success("✅ Guidebook created successfully!")
                
                st.subheader("🎉 Your Chatbot is Ready!")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info("🔗 **Chatbot URL:**")
                    st.code(chatbot_url, language=None)
                    st.caption("Share this link to access the chatbot")
                
                with col2:
                    st.info("📱 **QR Code:**")
                    qr_bytes = base64.b64decode(qr_base64)
                    st.image(qr_bytes, width=200, caption="Scan to access")
                
                st.divider()
                
                if st.button("Create Another Guidebook"):
                    st.rerun()

    st.divider()

    # EXISTING GUIDEBOOKS
    st.subheader("📚 Existing Guidebooks")

    guidebooks = get_guidebooks()

    if not guidebooks:
        st.info("No guidebooks found")
        return

    for g in guidebooks:
        with st.expander(f"📖 {g['guidebook_title']}"):
            new_title = st.text_input(
                "Guidebook Title",
                g["guidebook_title"],
                key=f"title_{g['guideid']}"
            )

            new_description = st.text_input(
                "Chatbot Description",
                g.get("chatbot_description", "Ask me anything about this guidebook!"),
                key=f"desc_{g['guideid']}",
                help="This message appears at the top of the chatbot"
            )

            new_original_url = st.text_input(
                "Original Guide URL",
                g["guide_original_url"],
                key=f"original_url_{g['guideid']}"
            )

            new_text = st.text_area(
                "Guide Content",
                g["guide_text"],
                height=120,
                key=f"text_{g['guideid']}"
            )

            # DISPLAY BOTH URLs
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("📄 **Original Guide URL:**")
                st.code(g['guide_original_url'], language=None)
            
            with col2:
                st.success("🤖 **Chatbot URL:**")
                st.code(g['guide_chatbot_url'], language=None)

            # QR CODE (points to chatbot URL)
            st.markdown("**📱 QR Code for Chatbot:**")
            qr_bytes = base64.b64decode(g["qr_code_base64"])
            st.image(qr_bytes, width=200, caption="Scan to open chatbot")

            st.caption(f"🆔 {g['guideid']}")
            st.caption(f"Created: {g['created_date']} by {g['created_by']}")
            if g.get('modified_date'):
                st.caption(f"Modified: {g['modified_date']} by {g.get('modified_by', 'N/A')}")

            if st.button("Update Guidebook", key=f"upd_{g['guideid']}"):
                update_guidebook(
                    g["guideid"],
                    new_title,
                    new_text,
                    new_original_url,
                    new_description,
                    st.session_state.username
                )
                st.success("✏️ Updated successfully!")
                st.rerun()
