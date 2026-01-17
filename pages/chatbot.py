import streamlit as st
import base64
from io import BytesIO
from PIL import Image
from google import genai
from db import get_connection

# ---------------- GEMINI CLIENT ----------------
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ---------------- DB QUERIES ----------------
def get_guidebook_by_slug(slug: str):
    """Fetch guidebook by URL slug"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM guidebook_registration WHERE guide_chatbot_url LIKE %s",
            (f"%guidebook={slug}%",)
        )
        row = cursor.fetchone()
    conn.close()
    return row

def get_guidebook_by_id(guideid: str):
    """Fetch guidebook by ID"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM guidebook_registration WHERE guideid = %s",
            (guideid,)
        )
        row = cursor.fetchone()
    conn.close()
    return row

# ---------------- CHAT HISTORY STORAGE (Optional) ----------------
def save_chat_message(guideid: str, user_message: str, bot_response: str, user: str):
    """Save chat conversation to database"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO chat_history
        (guideid, user_message, bot_response, created_by, created_date)
        VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(sql, (guideid, user_message, bot_response, user))
    conn.commit()
    conn.close()

# ---------------- QR DISPLAY ----------------
def show_qr(qr_base64):
    """Display QR code from base64"""
    if not qr_base64:
        return
    try:
        img = Image.open(BytesIO(base64.b64decode(qr_base64)))
        st.image(img, width=200, caption="Scan to share this chatbot")
    except Exception as e:
        st.error(f"Error loading QR code: {e}")

# ---------------- GEMINI AI CHAT ----------------
def ask_gemini(user_question: str, guidebook_title: str, guide_text: str, guide_url: str, chat_history: list) -> str:
    """
    Generate AI response using Google Gemini
    """
    
    # Build conversation context
    conversation_context = ""
    if chat_history:
        # Include last 5 exchanges for context
        recent_history = chat_history[-10:]
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_context += f"{role}: {msg['content']}\n\n"
    
    # Create prompt with guidebook context
    prompt = f"""
You are a helpful AI assistant for the guidebook titled "{guidebook_title}".

Your role is to answer questions based ONLY on the following guidebook content.

Guidebook Content:
{guide_text}

Original Guide URL (for reference):
{guide_url}

Previous Conversation:
{conversation_context}

Guidelines:
- Answer questions directly and accurately based on the guidebook content above
- If the answer is not in the guidebook, politely say so and offer to help with related questions
- Be concise but thorough
- Use a friendly, professional tone
- Do NOT mention that you're using a guidebook or document - just answer naturally
- If asked about topics outside the guidebook, redirect to guidebook-related topics

User Question:
{user_question}

Your Response:
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    
    except Exception as e:
        return f"I apologize, but I encountered an error: {str(e)}. Please try again."

# ---------------- MAIN CHATBOT PAGE ----------------
def main():
    st.set_page_config(
        page_title="Guidebook Chatbot",
        page_icon="🤖",
        layout="wide"
    )

    # Custom CSS for better chat UI
    st.markdown("""
        <style>
        .stChatMessage {
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .guidebook-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 0.5rem;
            color: white;
            margin-bottom: 1rem;
        }
        .guidebook-info {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Get guidebook parameter from URL
    params = st.query_params

    # Check for guidebook parameter (slug or id)
    guidebook = None
    
    if "guidebook" in params:
        guidebook_slug = params["guidebook"]
        guidebook = get_guidebook_by_slug(guidebook_slug)
    elif "id" in params:
        guidebook_id = params["id"]
        guidebook = get_guidebook_by_id(guidebook_id)
    else:
        st.error("❌ No guidebook specified in URL")
        st.info("Please access this page via a valid guidebook link")
        st.stop()

    if not guidebook:
        st.error(f"❌ Guidebook not found")
        st.info("The guidebook you're looking for doesn't exist or has been removed.")
        st.stop()

    # Display guidebook header
    st.markdown(f"""
        <div class="guidebook-header">
            <h1>🤖 {guidebook['guidebook_title']}</h1>
            <p>Ask me anything about this guidebook!</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar with guidebook info and QR
    with st.sidebar:
        st.header("📘 Guidebook Info")
        
        st.markdown(f"**Title:** {guidebook['guidebook_title']}")
        
        if guidebook.get('guide_original_url'):
            st.markdown(f"**Original Guide:** [View Here]({guidebook['guide_original_url']})")
        
        st.divider()
        
        # Display QR Code
        st.subheader("📱 Share this Chatbot")
        show_qr(guidebook.get('qr_code_base64'))
        
        st.divider()
        
        # Guide overview
        st.subheader("📊 Guide Overview")
        with st.expander("View Full Content"):
            st.write(guidebook['guide_text'])
        
        st.divider()
        
        # Metadata
        st.caption(f"Created: {guidebook.get('created_date', 'N/A')}")
        st.caption(f"By: {guidebook.get('created_by', 'N/A')}")
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if user_input := st.chat_input("Ask me anything about this guidebook..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)

        # Generate AI response with Gemini
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = ask_gemini(
                    user_question=user_input,
                    guidebook_title=guidebook['guidebook_title'],
                    guide_text=guidebook['guide_text'],
                    guide_url=guidebook.get('guide_original_url', ''),
                    chat_history=st.session_state.messages
                )
                st.markdown(response)
        
        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Save to database (optional - for analytics/history)
        try:
            user = st.session_state.get('username', 'anonymous')
            save_chat_message(
                guidebook['guideid'],
                user_input,
                response,
                user
            )
        except Exception as e:
            # Don't break the flow if DB save fails
            print(f"Error saving chat: {e}")

if __name__ == "__main__":
    main()


