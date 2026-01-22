import streamlit as st
from db import get_connection
from datetime import datetime

# ---------------- DB OPERATIONS ----------------
def get_all_chat_sessions():
    """Get all chat sessions with guidebook info"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT 
            cs.*,
            g.guidebook_title
        FROM chat_sessions cs
        JOIN guidebook_registration g ON cs.guideid = g.guideid
        ORDER BY cs.session_start DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
    conn.close()
    return rows

def get_session_messages(session_id: str):
    """Get all messages for a specific session"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT *
        FROM chat_messages
        WHERE session_id = %s
        ORDER BY created_at ASC
        """
        cursor.execute(sql, (session_id,))
        rows = cursor.fetchall()
    conn.close()
    return rows

def get_unanswered_questions():
    """Get all unanswered questions"""
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT 
            uq.*,
            g.guidebook_title,
            cs.session_start
        FROM unanswered_questions uq
        JOIN guidebook_registration g ON uq.guideid = g.guideid
        JOIN chat_sessions cs ON uq.session_id = cs.session_id
        ORDER BY uq.created_at DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
    conn.close()
    return rows

# ---------------- MAIN PAGE ----------------
def show_chat_sessions_page():
    st.title("💬 Chat Sessions & Analytics")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 All Sessions", "❌ Unanswered Questions", "📊 Analytics"])

    # TAB 1: All Sessions
    with tab1:
        st.subheader("All Chat Sessions")
        
        sessions = get_all_chat_sessions()
        
        if not sessions:
            st.info("No chat sessions found")
        else:
            # Filters
            col1, col2 = st.columns(2)
            with col1:
                filter_guidebook = st.selectbox(
                    "Filter by Guidebook",
                    ["All"] + list(set([s["guidebook_title"] for s in sessions]))
                )
            with col2:
                filter_status = st.selectbox(
                    "Filter by Status",
                    ["All", "Active", "Ended"]
                )
            
            # Apply filters
            filtered_sessions = sessions
            if filter_guidebook != "All":
                filtered_sessions = [s for s in filtered_sessions if s["guidebook_title"] == filter_guidebook]
            if filter_status == "Active":
                filtered_sessions = [s for s in filtered_sessions if s["is_active"]]
            elif filter_status == "Ended":
                filtered_sessions = [s for s in filtered_sessions if not s["is_active"]]
            
            st.caption(f"Showing {len(filtered_sessions)} sessions")
            
            # Display sessions
            for session in filtered_sessions:
                status_icon = "🟢" if session["is_active"] else "🔴"
                
                with st.expander(
                    f"{status_icon} {session['guidebook_title']} - {session['session_start'].strftime('%Y-%m-%d %H:%M')} "
                    f"({session['total_messages']} messages)"
                ):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Messages", session['total_messages'])
                    with col2:
                        st.metric("Input Tokens", session['total_input_tokens'])
                    with col3:
                        st.metric("Output Tokens", session['total_output_tokens'])
                    with col4:
                        total_tokens = session['total_input_tokens'] + session['total_output_tokens']
                        st.metric("Total Tokens", total_tokens)
                    
                    st.caption(f"**Session ID:** {session['session_id']}")
                    st.caption(f"**User:** {session['user_identifier']}")
                    st.caption(f"**Started:** {session['session_start']}")
                    if session['session_end']:
                        st.caption(f"**Ended:** {session['session_end']}")
                    
                    st.divider()
                    
                    # Load and display messages
                    if st.button(f"View Chat History", key=f"view_{session['session_id']}"):
                        st.session_state.selected_session = session['session_id']
                        st.rerun()
                    
                    # Show chat if this session is selected
                    if st.session_state.get('selected_session') == session['session_id']:
                        st.subheader("💬 Chat History")
                        
                        messages = get_session_messages(session['session_id'])
                        
                        for msg in messages:
                            role_icon = "👤" if msg['role'] == "user" else "🤖"
                            answer_status = ""
                            
                            if msg['role'] == "assistant" and not msg['was_answered']:
                                answer_status = " ⚠️ (Unable to answer)"
                            
                            st.markdown(f"**{role_icon} {msg['role'].title()}{answer_status}**")
                            st.write(msg['content'])
                            
                            token_info = []
                            if msg['input_tokens'] > 0:
                                token_info.append(f"Input: {msg['input_tokens']}")
                            if msg['output_tokens'] > 0:
                                token_info.append(f"Output: {msg['output_tokens']}")
                            
                            if token_info:
                                st.caption(f"🔤 Tokens - {' | '.join(token_info)}")
                            
                            st.caption(f"🕒 {msg['created_at']}")
                            st.divider()
                        
                        if st.button("Close Chat History", key=f"close_{session['session_id']}"):
                            st.session_state.selected_session = None
                            st.rerun()

    # TAB 2: Unanswered Questions
    with tab2:
        st.subheader("❌ Unanswered Questions")
        
        unanswered = get_unanswered_questions()
        
        if not unanswered:
            st.success("🎉 All questions have been answered!")
        else:
            st.warning(f"Found {len(unanswered)} unanswered questions")
            
            for idx, uq in enumerate(unanswered):
                with st.expander(
                    f"❓ {uq['guidebook_title']} - {uq['created_at'].strftime('%Y-%m-%d %H:%M')}"
                ):
                    st.markdown("**User Question:**")
                    st.info(uq['user_question'])
                    
                    st.markdown("**AI Response:**")
                    st.warning(uq['ai_response'])
                    
                    st.markdown("**Reason:**")
                    st.caption(uq['reason'])
                    
                    st.caption(f"**Session:** {uq['session_id']}")
                    st.caption(f"**Time:** {uq['created_at']}")

    # TAB 3: Analytics
    with tab3:
        st.subheader("📊 Analytics Dashboard")
        
        if not sessions:
            st.info("No data available for analytics")
        else:
            # Overall stats
            col1, col2, col3, col4 = st.columns(4)
            
            total_sessions = len(sessions)
            active_sessions = len([s for s in sessions if s['is_active']])
            total_messages = sum([s['total_messages'] for s in sessions])
            total_tokens = sum([s['total_input_tokens'] + s['total_output_tokens'] for s in sessions])
            
            with col1:
                st.metric("Total Sessions", total_sessions)
            with col2:
                st.metric("Active Sessions", active_sessions)
            with col3:
                st.metric("Total Messages", total_messages)
            with col4:
                st.metric("Total Tokens", f"{total_tokens:,}")
            
            st.divider()
            
            # Guidebook stats
            st.subheader("📘 By Guidebook")
            
            guidebook_stats = {}
            for s in sessions:
                title = s['guidebook_title']
                if title not in guidebook_stats:
                    guidebook_stats[title] = {
                        'sessions': 0,
                        'messages': 0,
                        'tokens': 0
                    }
                guidebook_stats[title]['sessions'] += 1
                guidebook_stats[title]['messages'] += s['total_messages']
                guidebook_stats[title]['tokens'] += s['total_input_tokens'] + s['total_output_tokens']
            
            for guidebook, stats in guidebook_stats.items():
                with st.expander(f"📖 {guidebook}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Sessions", stats['sessions'])
                    with col2:
                        st.metric("Messages", stats['messages'])
                    with col3:
                        st.metric("Tokens", f"{stats['tokens']:,}")

if __name__ == "__main__":
    show_chat_sessions_page()
