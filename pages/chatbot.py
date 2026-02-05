import streamlit as st
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
from db import get_connection
import uuid
from datetime import datetime
import re

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

def get_session_contact_info(session_id: str):
    """Get contact information already provided in this session"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT user_phone, user_email 
        FROM unanswered_questions 
        WHERE session_id = %s 
        AND contact_provided = TRUE
        ORDER BY created_at DESC
        LIMIT 1
        """
        cursor.execute(sql, (session_id,))
        row = cursor.fetchone()
    conn.close()
    return row

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

def log_unanswered_question(session_id: str, guideid: str, question: str, response: str, reason: str,
                           phone: str = None, email: str = None):
    """Log questions that couldn't be answered with optional contact info"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        INSERT INTO unanswered_questions 
        (session_id, guideid, user_question, ai_response, reason, user_phone, user_email, contact_provided)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        contact_provided = bool(phone or email)
        cursor.execute(sql, (session_id, guideid, question, response, reason, phone, email, contact_provided))
    conn.commit()
    conn.close()

def update_unanswered_question_contact(session_id: str, question: str, phone: str = None, email: str = None):
    """Update contact information for an unanswered question"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        UPDATE unanswered_questions 
        SET user_phone = %s, user_email = %s, contact_provided = TRUE
        WHERE session_id = %s AND user_question = %s
        ORDER BY created_at DESC
        LIMIT 1
        """
        cursor.execute(sql, (phone, email, session_id, question))
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

# ---------------- CONTACT VALIDATION ----------------
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15

# ---------------- ANSWER DETECTION ----------------
def check_if_answered(response: str) -> tuple[bool, str, bool]:
    """
    Detect if the AI was able to answer the question
    Returns: (was_answered: bool, reason: str, is_property_related: bool)
    """
    response_lower = response.lower()
    
    # Check if response indicates property-related unanswered question
    property_related_keywords = [
        "pass this question to the property manager",
        "property manager or owner",
        "contact the property"
    ]
    
    # Check if response indicates non-property-related question
    non_property_keywords = [
        "not available in the guidebook",
        "not relevant to the property",
        "not related to this property",
        "outside the scope of this guidebook",
        "not covered in this guidebook"
    ]
    
    # Check for property-related unanswered
    for keyword in property_related_keywords:
        if keyword in response_lower:
            return False, f"Property-related: '{keyword}'", True
    
    # Check for non-property-related unanswered
    for keyword in non_property_keywords:
        if keyword in response_lower:
            return False, f"Non-property-related: '{keyword}'", False
    
    # Generic unable to answer keywords
    unable_keywords = [
        "not in the guidebook",
        "don't have information",
        "cannot find",
        "not mentioned",
        "doesn't contain",
        "no information about",
        "not covered",
        "not included",
        "i don't know",
        "i'm not sure",
        "unable to answer"
    ]
    
    for keyword in unable_keywords:
        if keyword in response_lower:
            return False, f"Response contained: '{keyword}'", False
    
    return True, "Answered successfully", False

# ---------------- OPENAI CHAT ----------------
def ask_openai(user_question: str, guidebook_title: str, guide_text: str, 
               guide_url: str, chat_history: list) -> tuple[str, int, int]:
    """Generate AI response using OpenAI GPT-4o-mini"""
    
    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful AI assistant for the property guidebook titled "{guidebook_title}".

Your role is to answer questions based ONLY on the following guidebook content.

Guidebook Content:
{guide_text}

Original Guide URL (for reference):
{guide_url}

IMPORTANT INSTRUCTIONS:

1. If the question IS RELATED TO THE PROPERTY and the answer is NOT in the guidebook:
   - Respond EXACTLY: "I am going to pass this question to the property manager or owner. Do you mind sharing your phone number or email so one of them can call or text you back with an answer?"

2. If the question IS NOT RELATED TO THE PROPERTY (e.g., general knowledge, unrelated topics, personal questions):
   - Respond: "I'm sorry, but that question is not available in the guidebook or not relevant to the property. I can only help with questions about this specific property and its amenities, policies, and guidelines."

3. If you CAN answer the question from the guidebook:
   - Answer directly, accurately, and concisely based on the guidebook content

Guidelines:
- Be helpful and friendly
- Do NOT make up information not in the guidebook
- Clearly distinguish between property-related and non-property questions"""
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

# ---------------- PROCESS USER MESSAGE ----------------
def process_user_message(user_input: str, guidebook: dict):
    """Process user message and generate response"""
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
    
    was_answered, reason, is_property_related = check_if_answered(response)
    
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
            if is_property_related:
                # Property-related question - ask for contact
                if st.session_state.saved_phone or st.session_state.saved_email:
                    # Contact already saved
                    log_unanswered_question(
                        st.session_state.session_id,
                        guidebook['guideid'],
                        user_input,
                        response,
                        reason,
                        st.session_state.saved_phone,
                        st.session_state.saved_email
                    )
                    
                    contact_parts = []
                    if st.session_state.saved_phone:
                        contact_parts.append(f"phone ({st.session_state.saved_phone})")
                    if st.session_state.saved_email:
                        contact_parts.append(f"email ({st.session_state.saved_email})")
                    
                    contact_info_msg = f"ℹ️ We already have your contact information on file ({' and '.join(contact_parts)}). The property manager will get back to you soon."
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": contact_info_msg
                    })
                    
                    save_chat_message(
                        st.session_state.session_id,
                        guidebook['guideid'],
                        "assistant",
                        contact_info_msg,
                        0,
                        estimate_tokens(contact_info_msg),
                        True
                    )
                else:
                    # No contact yet - ask for it
                    log_unanswered_question(
                        st.session_state.session_id,
                        guidebook['guideid'],
                        user_input,
                        response,
                        reason
                    )
                    
                    st.session_state.awaiting_contact = True
                    st.session_state.pending_question = user_input
            else:
                # Non-property-related - just log, don't ask for contact
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
        .contact-form {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        .quick-action-btn {
            margin: 0.25rem;
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
    
    if "awaiting_contact" not in st.session_state:
        st.session_state.awaiting_contact = False
    
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    
    # Check if contact info already exists for this session
    if "session_contact_checked" not in st.session_state:
        existing_contact = get_session_contact_info(st.session_state.session_id)
        if existing_contact:
            st.session_state.saved_phone = existing_contact.get('user_phone')
            st.session_state.saved_email = existing_contact.get('user_email')
        else:
            st.session_state.saved_phone = None
            st.session_state.saved_email = None
        st.session_state.session_contact_checked = True

    # Display guidebook header
    chatbot_description = guidebook.get('chatbot_description', 'Ask me anything about this guidebook!')
    
    st.markdown(f"""
        <div class="guidebook-header">
            <h1>🤖 {guidebook['guidebook_title']}</h1>
            <p>{chatbot_description}</p>
        </div>
    """, unsafe_allow_html=True)

    # Minimal Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        
        if guidebook.get('guide_original_url'):
            st.markdown(f"[📄 View Original Guide]({guidebook['guide_original_url']})")
        
        st.divider()
        
        # QR Code
        st.subheader("📱 Share")
        show_qr(guidebook.get('qr_code_base64'))
        
        st.divider()
        
        # Show saved contact info
        if st.session_state.saved_phone or st.session_state.saved_email:
            st.subheader("📞 Your Contact")
            if st.session_state.saved_phone:
                st.caption(f"📱 {st.session_state.saved_phone}")
            if st.session_state.saved_email:
                st.caption(f"📧 {st.session_state.saved_email}")
            st.divider()
        
        # Clear chat button
        if st.button("🗑️ New Chat", use_container_width=True):
            end_chat_session(st.session_state.session_id)
            st.session_state.messages = []
            st.session_state.total_input_tokens = 0
            st.session_state.total_output_tokens = 0
            st.session_state.awaiting_contact = False
            st.session_state.pending_question = None
            st.session_state.saved_phone = None
            st.session_state.saved_email = None
            st.session_state.session_contact_checked = False
            st.session_state.session_id = create_chat_session(
                guidebook['guideid'],
                st.session_state.get('username', 'anonymous')
            )
            st.rerun()

    # Quick Action Buttons (shown when no messages or at start)
    if len(st.session_state.messages) == 0:
        st.markdown("### 💡 Quick Questions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📶 WiFi Password", key="btn_wifi", use_container_width=True):
                process_user_message("What is the WiFi password?", guidebook)
                st.rerun()
        
        with col2:
            if st.button("📺 TV Remote", key="btn_tv", use_container_width=True):
                process_user_message("How do I use the TV remote?", guidebook)
                st.rerun()
        
        with col3:
            if st.button("🗑️ Trash Location", key="btn_trash", use_container_width=True):
                process_user_message("Where is the trash can located?", guidebook)
                st.rerun()
        
        with col4:
            if st.button("🅿️ Parking Info", key="btn_parking", use_container_width=True):
                process_user_message("Where can I park?", guidebook)
                st.rerun()
        
        # Second row of buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔑 Check-in Time", key="btn_checkin", use_container_width=True):
                process_user_message("What is the check-in time?", guidebook)
                st.rerun()
        
        with col2:
            if st.button("🚪 Check-out Time", key="btn_checkout", use_container_width=True):
                process_user_message("What is the check-out time?", guidebook)
                st.rerun()
        
        with col3:
            if st.button("🏊 Pool Hours", key="btn_pool", use_container_width=True):
                process_user_message("What are the pool hours?", guidebook)
                st.rerun()
        
        with col4:
            if st.button("🆘 Emergency Contact", key="btn_emergency", use_container_width=True):
                process_user_message("What is the emergency contact number?", guidebook)
                st.rerun()
        
        st.divider()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Show contact form if awaiting contact information
    if st.session_state.awaiting_contact:
        st.markdown('<div class="contact-form">', unsafe_allow_html=True)
        st.subheader("📞 Contact Information")
        st.write("Please provide at least one way for us to reach you:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            user_phone = st.text_input("Phone Number (optional)", placeholder="+1 234 567 8900")
        
        with col2:
            user_email = st.text_input("Email (optional)", placeholder="your@email.com")
        
        col_submit, col_skip = st.columns(2)
        
        with col_submit:
            if st.button("✅ Submit Contact Info", use_container_width=True, type="primary"):
                phone_valid = validate_phone(user_phone) if user_phone else False
                email_valid = validate_email(user_email) if user_email else False
                
                if not user_phone and not user_email:
                    st.error("Please provide at least one contact method")
                elif user_phone and not phone_valid:
                    st.error("Please enter a valid phone number")
                elif user_email and not email_valid:
                    st.error("Please enter a valid email address")
                else:
                    try:
                        update_unanswered_question_contact(
                            st.session_state.session_id,
                            st.session_state.pending_question,
                            user_phone if phone_valid else None,
                            user_email if email_valid else None
                        )
                        
                        st.session_state.saved_phone = user_phone if phone_valid else None
                        st.session_state.saved_email = user_email if email_valid else None
                        
                        confirmation = "✅ Thank you! We've saved your contact information. "
                        if user_phone and user_email:
                            confirmation += f"The property manager will reach out to you via phone ({user_phone}) or email ({user_email}) soon."
                        elif user_phone:
                            confirmation += f"The property manager will call or text you at {user_phone} soon."
                        else:
                            confirmation += f"The property manager will email you at {user_email} soon."
                        
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": confirmation
                        })
                        
                        st.session_state.awaiting_contact = False
                        st.session_state.pending_question = None
                        
                        st.success("Contact information saved!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error saving contact info: {e}")
        
        with col_skip:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.awaiting_contact = False
                st.session_state.pending_question = None
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "No problem! Feel free to ask another question."
                })
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    if not st.session_state.awaiting_contact:
        if user_input := st.chat_input("Ask me anything..."):
            process_user_message(user_input, guidebook)
            st.rerun()

if __name__ == "__main__":
    main()
