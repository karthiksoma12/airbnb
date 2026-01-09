import streamlit as st
import base64
from io import BytesIO
from PIL import Image
from google import genai
from db import get_connection

# ---------------- GEMINI CLIENT ----------------
client = genai.Client(api_key="AIzaSyC6dQyW5suajkRi3ZJEeraavUdvys30U98")

# ---------------- DB QUERIES ----------------
def get_properties_with_guide():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT p.propId, p.property_address
            FROM mapper m
            JOIN property_registration p ON p.propId = m.propid
        """)
        rows = cursor.fetchall()
    conn.close()
    return rows


def get_guidebook_context(propid):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT g.guide_text, g.guide_url, g.qr_code_base64
            FROM mapper m
            JOIN guidebook_registration g ON g.guideid = m.guideid
            WHERE m.propid = %s
        """, (propid,))
        row = cursor.fetchone()
    conn.close()
    return row

# ---------------- QR DISPLAY ----------------
def show_qr(qr_base64):
    if not qr_base64:
        return
    try:
        img = Image.open(BytesIO(base64.b64decode(qr_base64)))
        st.image(img, width=160, caption="Property Guide QR")
    except Exception:
        pass

# ---------------- GEMINI CHAT ----------------
def ask_ai(user_msg, guide_text, guide_url):
    prompt = f"""
You are a helpful property assistant.

Use ONLY the internal guidebook information below.
Do NOT mention guidebooks, documents, or sources.

Guide Content:
{guide_text}

Guide URL (internal reference):
{guide_url}

User Question:
{user_msg}
"""

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )

    return response.text

# ---------------- PAGE UI ----------------
def show_property_chatbot():
    st.title("💬 Property Assistant")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    properties = get_properties_with_guide()

    if not properties:
        st.warning("No properties mapped to guidebooks")
        return

    prop_map = {p["property_address"]: p["propId"] for p in properties}

    selected_property = st.selectbox(
        "Select Property",
        prop_map.keys()
    )

    guide = get_guidebook_context(prop_map[selected_property])

    if not guide:
        st.info("No guide context available")
        return

    # ---------------- QR ONLY ----------------
    col1, col2 = st.columns([4, 1])
    with col2:
        show_qr(guide["qr_code_base64"])

    st.divider()

    # ---------------- CHAT ----------------
    if "chat" not in st.session_state:
        st.session_state.chat = []

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about this property...")

    if user_input:
        st.session_state.chat.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            reply = ask_ai(
                user_input,
                guide["guide_text"],
                guide["guide_url"]
            )
            st.markdown(reply)

        st.session_state.chat.append(
            {"role": "assistant", "content": reply}
        )
