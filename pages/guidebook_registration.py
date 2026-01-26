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
def get_all_properties():
    """Get all available properties"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT propId, property_address FROM property_registration ORDER BY property_address"
        )
        rows = cursor.fetchall()
    conn.close()
    return rows

def get_guidebooks():
    """Get all guidebooks"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM guidebook_registration ORDER BY created_date DESC"
        )
        rows = cursor.fetchall()
    conn.close()
    return rows

def get_mapped_properties(guideid: str):
    """Get properties mapped to a guidebook"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT p.propId, p.property_address 
            FROM mapper m
            JOIN property_registration p ON m.propid = p.propId
            WHERE m.guideid = %s
        """, (guideid,))
        rows = cursor.fetchall()
    conn.close()
    return rows

def insert_guidebook(title, text, original_url, description, user):
    """Create new guidebook"""
    guideid = str(uuid.uuid4())
    chatbot_url = generate_chatbot_url(title)
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
            guideid,
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
    
    return guideid, chatbot_url, qr_base64

def update_guidebook(guideid, title, text, original_url, description, user):
    """Update existing guidebook"""
    chatbot_url = generate_chatbot_url(title)
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

def map_guidebook_to_properties(guideid: str, property_ids: list, user: str):
    """Map a guidebook to multiple properties"""
    conn = get_connection()
    with conn.cursor() as cursor:
        # First, remove existing mappings for this guidebook
        cursor.execute("DELETE FROM mapper WHERE guideid = %s", (guideid,))
        
        # Then add new mappings
        for propid in property_ids:
            sql = """
            INSERT INTO mapper (propid, guideid, created_by, created_date)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (propid, guideid, user, datetime.now()))
    conn.commit()
    conn.close()

def delete_property_mapping(guideid: str, propid: str):
    """Remove a specific property mapping"""
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM mapper WHERE guideid = %s AND propid = %s",
            (guideid, propid)
        )
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
        title = st.text_input("Guidebook Title", key="new_title")
        
        description = st.text_input(
            "Chatbot Description", 
            placeholder="Ask me anything about this guidebook!",
            help="This message will appear at the top of the chatbot",
            key="new_desc"
        )
        
        original_url = st.text_input(
            "Original Guide URL", 
            placeholder="https://example.com/guide",
            key="new_url"
        )
        
        text = st.text_area("Guide Content", height=150, key="new_text")
        
        st.divider()
        
        # Property mapping during creation
        st.subheader("🏢 Map to Properties")
        st.caption("Select which properties this guidebook should be available for")
        
        properties = get_all_properties()
        
        if not properties:
            st.warning("⚠️ No properties available. Please create properties first.")
            property_ids = []
        else:
            # Create a multiselect with property addresses
            property_options = {p['property_address']: p['propId'] for p in properties}
            
            selected_properties = st.multiselect(
                "Select Properties",
                options=list(property_options.keys()),
                help="You can select multiple properties. This guidebook will be available for all selected properties.",
                key="new_properties"
            )
            
            # Get the property IDs for selected properties
            property_ids = [property_options[addr] for addr in selected_properties]
            
            if selected_properties:
                st.success(f"✅ Selected {len(selected_properties)} properties")

        if st.button("💾 Save Guidebook", type="primary", key="save_new"):
            if not (title and text and original_url):
                st.error("Title, Guide Content, and Original URL are required")
            elif not property_ids:
                st.error("Please select at least one property to map this guidebook to")
            else:
                final_description = description if description else "Ask me anything about this guidebook!"
                
                # Create guidebook
                guideid, chatbot_url, qr_base64 = insert_guidebook(
                    title, text, original_url, final_description, st.session_state.username
                )
                
                # Map to properties
                map_guidebook_to_properties(guideid, property_ids, st.session_state.username)
                
                # Show success with generated URL and QR
                st.success("✅ Guidebook created and mapped to properties successfully!")
                
                st.subheader("🎉 Your Chatbot is Ready!")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info("🔗 **Chatbot URL:**")
                    st.code(chatbot_url, language=None)
                    st.caption("Share this link to access the chatbot")
                    
                    st.info("🏢 **Mapped Properties:**")
                    for addr in selected_properties:
                        st.caption(f"• {addr}")
                
                with col2:
                    st.info("📱 **QR Code:**")
                    qr_bytes = base64.b64decode(qr_base64)
                    st.image(qr_bytes, width=200, caption="Scan to access")
                
                st.divider()
                
                if st.button("Create Another Guidebook", key="create_another"):
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
            # Guidebook details
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

            st.divider()
            
            # Property mapping management
            st.subheader("🏢 Property Mappings")
            
            mapped_properties = get_mapped_properties(g['guideid'])
            all_properties = get_all_properties()
            
            if mapped_properties:
                st.caption(f"Currently mapped to {len(mapped_properties)} properties:")
                
                for mp in mapped_properties:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(f"📍 {mp['property_address']}")
                    with col2:
                        if st.button("🗑️", key=f"unmap_{g['guideid']}_{mp['propId']}", 
                                    help="Remove this mapping"):
                            delete_property_mapping(g['guideid'], mp['propId'])
                            st.success("Mapping removed!")
                            st.rerun()
            else:
                st.warning("⚠️ Not mapped to any properties")
            
            st.divider()
            
            # Add more properties
            st.caption("Add more properties:")
            
            # Get unmapped properties
            mapped_ids = [mp['propId'] for mp in mapped_properties]
            available_properties = [p for p in all_properties if p['propId'] not in mapped_ids]
            
            if available_properties:
                property_options = {p['property_address']: p['propId'] for p in available_properties}
                
                additional_properties = st.multiselect(
                    "Select Additional Properties",
                    options=list(property_options.keys()),
                    key=f"add_props_{g['guideid']}"
                )
                
                if additional_properties:
                    additional_ids = [property_options[addr] for addr in additional_properties]
                    
                    if st.button("➕ Add Selected Properties", key=f"add_btn_{g['guideid']}"):
                        # Add to existing mappings
                        all_mapped_ids = mapped_ids + additional_ids
                        map_guidebook_to_properties(
                            g['guideid'], 
                            all_mapped_ids, 
                            st.session_state.username
                        )
                        st.success(f"Added {len(additional_properties)} properties!")
                        st.rerun()
            else:
                st.caption("✅ All properties are already mapped")
            
            st.divider()

            # Display URLs and QR
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("📄 **Original Guide URL:**")
                st.code(g['guide_original_url'], language=None)
            
            with col2:
                st.success("🤖 **Chatbot URL:**")
                st.code(g['guide_chatbot_url'], language=None)

            st.markdown("**📱 QR Code for Chatbot:**")
            qr_bytes = base64.b64decode(g["qr_code_base64"])
            st.image(qr_bytes, width=200, caption="Scan to open chatbot")

            st.caption(f"🆔 {g['guideid']}")
            st.caption(f"Created: {g['created_date']} by {g['created_by']}")
            if g.get('modified_date'):
                st.caption(f"Modified: {g['modified_date']} by {g.get('modified_by', 'N/A')}")

            if st.button("💾 Update Guidebook", key=f"upd_{g['guideid']}", type="primary"):
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

if __name__ == "__main__":
    show_guidebook_page()
