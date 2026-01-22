import streamlit as st
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from db import get_connection
import uuid
from datetime import datetime

# ---------------- OPENAI CLIENT ----------------
client = client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- TOKEN CALCULATION ----------------
def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    return len(text) // 4

# ---------------- SESSION MANAGEMENT ----------------
def create_chat_session(guideid: str, user_identifier: str = "anonymous") -> str:
    """Create a new chat session"""
    session_id = str(uuid.uuid4())
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO chat_sessions 
        (session_id, guideid, user_identifier)
        VALUES (%s, %s, %s)
        """
        cursor.execute(sql, (session_id, guideid, user_identifier))
    conn.commit()
    conn.close()
    return session_id

def update_session_stats(session_id: str, input_tokens: int, output_tokens: int):
    """Update session token statistics"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE chat_sessions 
        SET total_messages = total_messages + 1,
            total_input_tokens = total_input_tokens + %s,
            total_output_tokens = total_output_tokens + %s
        WHERE session_id = %s
        """
        cursor.execute(sql, (input_tokens, output_tokens, session_id))
    conn.commit()
    conn.close()

def end_chat_session(session_id: str):
    """Mark session as ended"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE chat_sessions 
        SET session_end = NOW(), is_active = FALSE
        WHERE session_id = %s
        """
        cursor.execute(sql, (session_id,))
    conn.commit()
    conn.close()

# ---------------- MESSAGE LOGGING ----------------
def save_chat_message(session_id: str, guideid: str, role: str, content: str, 
                     input_tokens: int, output_tokens: int, was_answered: bool = True):
    """Save individual chat message"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO chat_messages 
        (session_id, guideid, role, content, input_tokens, output_tokens, was_answered)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (session_id, guideid, role, content, input_tokens, output_tokens, was_answered))
    conn.commit()
    conn.close()

def log_unanswered_question(session_id: str, guideid: str, question: str, response: str, reason: str):
    """Log questions that couldn't be answered"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO unanswered_questions 
        (session_id, guideid, user_question, ai_response, reason)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (session_id, guideid, question, response, reason))
    conn.commit()
    conn.close()

# ---------------- DB OPERATIONS ----------------
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

# ---------------- QR DISPLAY ----------------
def show_qr(qr_base64):
    """Display QR code from base64"""
    if not qr_base64:
        return
    try:
        img = Image.open(BytesIO(base64.b64decode(qr_base64)))
        st.image(img, width=200, caption="Scan to share")
    except Exception as e:
        st.error(f"Error loading QR code: {e}")

# ---------------- ANSWER DETECTION ----------------
def check_if_answered(response: str) -> tuple[bool, str]:
    """Detect if the AI was able to answer the question"""
    unable_keywords = [
        "not in the guidebook",
        "don't have information",
        "cannot find",
        "not mentioned",
        "doesn't contain",
        "no information about",
        "not covered",
        "outside the scope",
        "not included",
        "i don't know",
        "i'm not sure",
        "unable to answer"
    ]
    
    response_lower = response.lower()
    
    for keyword in unable_keywords:
        if keyword in response_lower:
            return False, f"Response contained: '{keyword}'"
    
    return True, "Answered successfully"

# ---------------- OPENAI CHAT ----------------
def ask_openai(user_question: str, guidebook_title: str, guide_text: str, 
               guide_url: str, chat_history: list) -> tuple[str, int, int]:
    """Generate AI response using OpenAI GPT-4o-mini"""
    
    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful AI assistant for the guidebook titled "{guidebook_title}".

Your role is to answer questions based ONLY on the following guidebook content.

Guidebook Content:
{guide_text}

Original Guide URL (for reference):
{guide_url}

Guidelines:
- Answer questions directly and accurately based on the guidebook content above
- If the answer is NOT in the guidebook, you MUST clearly state: "I don't have information about that in the guidebook."
- Be concise but thorough
- Use a friendly, professional tone
- Do NOT make up information not in the guidebook
- If asked about topics outside the guidebook, clearly say it's not covered"""
        }
    ]
    
    if chat_history:
        recent_history = chat_history[-10:]
        for msg in recent_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    messages.append({
        "role": "user",
        "content": user_question
    })

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        return response_text, input_tokens, output_tokens
    
    except Exception as e:
        error_msg = f"I apologize, but I encountered an error: {str(e)}. Please try again."
        return error_msg, estimate_tokens(str(messages)), estimate_tokens(error_msg)

# ---------------- MAIN CHATBOT PAGE ----------------
def main():
    st.set_page_config(
        page_title="Guidebook Chatbot",
        page_icon="🤖",
        layout="wide"
    )

    # Custom CSS
    st.markdown("""
        <style>
        .guidebook-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 0.5rem;
            color: white;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Get guidebook parameter from URL
    params = st.query_params

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
        st.stop()

    # Initialize session
    if "session_id" not in st.session_state:
        st.session_state.session_id = create_chat_session(
            guidebook['guideid'],
            st.session_state.get('username', 'anonymous')
        )
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "total_input_tokens" not in st.session_state:
        st.session_state.total_input_tokens = 0
    
    if "total_output_tokens" not in st.session_state:
        st.session_state.total_output_tokens = 0

    # Display guidebook header
    chatbot_description = guidebook.get('chatbot_description', 'Ask me anything about this guidebook!')
    
    st.markdown(f"""
        <div class="guidebook-header">
            <h1>🤖 {guidebook['guidebook_title']}</h1>
            <p>{chatbot_description}</p>
        </div>
    """, unsafe_allow_html=True)

    # Minimal Sidebar - No file list
    with st.sidebar:
        st.header("ℹ️ About")
        
        if guidebook.get('guide_original_url'):
            st.markdown(f"[📄 View Original Guide]({guidebook['guide_original_url']})")
        
        st.divider()
        
        # QR Code only
        st.subheader("📱 Share")
        show_qr(guidebook.get('qr_code_base64'))
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ New Chat", use_container_width=True):
            end_chat_session(st.session_state.session_id)
            st.session_state.messages = []
            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0
            st.session_state.session_id = create_chat_session(
                guidebook['guideid'],
                st.session_state.get('username', 'anonymous')
            )
            st.rerun()

    # Display chat messages (no token display)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if user_input := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({
            "role": "user", 
            "content": user_input
        })
        
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response, input_tokens, output_tokens = ask_openai(
                    user_question=user_input,
                    guidebook_title=guidebook['guidebook_title'],
                    guide_text=guidebook['guide_text'],
                    guide_url=guidebook.get('guide_original_url', ''),
                    chat_history=st.session_state.messages[:-1]
                )
                st.markdown(response)
        
        was_answered, reason = check_if_answered(response)
        
        st.session_state.messages[-1]["input_tokens"] = input_tokens
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response,
            "output_tokens": output_tokens,
            "was_answered": was_answered
        })
        
        st.session_state.total_input_tokens += input_tokens
        st.session_state.total_output_tokens += output_tokens
        
        try:
            save_chat_message(
                st.session_state.session_id,
                guidebook['guideid'],
                "user",
                user_input,
                input_tokens,
                0,
                True
            )
            
            save_chat_message(
                st.session_state.session_id,
                guidebook['guideid'],
                "assistant",
                response,
                0,
                output_tokens,
                was_answered
            )
            
            if not was_answered:
                log_unanswered_question(
                    st.session_state.session_id,
                    guidebook['guideid'],
                    user_input,
                    response,
                    reason
                )
            
            update_session_stats(
                st.session_state.session_id,
                input_tokens,
                output_tokens
            )
            
        except Exception as e:
            print(f"Error saving chat: {e}")
        
        st.rerun()

if __name__ == "__main__":
    main()
