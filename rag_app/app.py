import streamlit as st
import os
from dotenv import load_dotenv
from rag import get_chat_engine
from ingest import list_ingested_files
import fitz # PyMuPDF
from PIL import Image

# Load environment variables
load_dotenv()

st.set_page_config(page_title="SaazAi", layout="wide")

# --- Custom CSS for Premium "SaaS" Look ---
st.markdown("""
<style>
    /* 1. TYPOGRAPHY & RESET */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1E293B; /* Slate 800 */
    }
    
    /* 2. COLORS & VARIABLES */
    :root {
        --primary: #D32F2F;        /* Deep Red */
        --primary-light: #FFEBEE;  /* Light Red BG */
        --secondary: #64748B;      /* Slate 500 */
        --bg-surface: #FFFFFF;     /* White */
        --bg-canvas: #F8F9FC;      /* Cool Grey */
        --border: #E2E8F0;         /* Slate 200 */
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        --radius: 12px;
    }

    /* 3. LAYOUT & SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-surface);
        border-right: 1px solid var(--border);
    }
    
    /* Sidebar Navigation Links (Buttons) */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        border: none !important;
        background-color: transparent !important;
        color: #64748B !important; /* Inactive Text */
        font-weight: 500 !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        display: flex;
        align-items: center;
        margin-bottom: 0.25rem;
        box-shadow: none !important;
        justify-content: flex-start !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #F1F5F9 !important;
        color: #1E293B !important;
    }

    /* ACTIVE STATE: Target the Primary button inside Sidebar */
    /* FORCE OVERRIDE default streamlit primary solid red */
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background-color: #FEF2F2 !important; /* Extremely light red */
        color: #D32F2F !important; /* Brand Red Text */
        border: 1px solid #FECACA !important; /* Subtle border */
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    
    /* Icons in buttons (if we add them later via markdown, but for now generic) */
    div[data-testid="stSidebar"] .stButton > button:before {
        margin-right: 8px;
    }

    /* 4. CHAT ELEMENTS */
    /* Message Container */
    div[data-testid="stChatMessage"] {
        background-color: transparent;
        border: none;
        padding: 1rem 0; /* Increase spacing */
        margin-bottom: 0.5rem;
    }
    
    /* AVATARS: Circular & Styled */
    div[data-testid="stChatMessage"] .st-emotion-cache-1p1m4ay, 
    div[data-testid="stChatMessage"] .st-emotion-cache-10tzppz,
    div[data-testid="stChatMessage"] > div:first-child {
        border-radius: 50% !important;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        border: 2px solid white; /* clean border ring */
    }
    
    /* USER MESSAGE: Right Aligned, Red Bubble */
    div[data-testid="stChatMessage"][data-author="user"] {
        flex-direction: row-reverse;
    }
    div[data-testid="stChatMessage"][data-author="user"] .stMarkdown {
        background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%); /* Slightly brighter gradient */
        color: white !important;
        padding: 12px 20px;
        border-radius: 20px 20px 4px 20px;
        box-shadow: 0 4px 12px rgba(185, 28, 28, 0.2);
        max-width: 75%;
        text-align: right;
        font-size: 0.95rem;
    }
    div[data-testid="stChatMessage"][data-author="user"] p {
        color: white !important;
    }

    /* ASSISTANT MESSAGE: Left Aligned, White Card */
    div[data-testid="stChatMessage"][data-author="assistant"] .stMarkdown {
        background-color: white;
        color: #334155;
        padding: 16px 24px;
        border-radius: 20px 20px 20px 4px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); /* Softer shadow */
        border: 1px solid #F1F5F9;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    /* 5. INPUT AREA (Glassmorphic Pill) */
    div[data-testid="stChatInput"] {
        margin-bottom: 3rem; 
        max-width: 800px !important; /* Constrain width */
        margin-left: auto;
        margin-right: auto;
    }
    
    div[data-testid="stChatInput"] > div {
        border-radius: 50px !important;
        border: 1px solid #E2E8F0 !important; 
        background-color: white !important; /* Cleaner than glass for readability */
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01); /* Elevate */
        padding: 10px 10px; /* Slimmer inner padding */
        align_items: center; 
    }

    div[data-testid="stChatInput"] :focus-within {
        border-color: #EF4444 !important; /* Brighter red focus */
        box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1) !important;
    }

    /* Input Text Field */
    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        border: none !important;
        color: #1E293B !important;
        font-size: 0.95rem;
        padding-left: 10px;
    }

    /* Send Button */
    div[data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%) !important;
        color: white !important;
        border-radius: 50% !important;
        border: none !important;
        height: 42px !important;
        width: 42px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px rgba(185, 28, 28, 0.2);
    }
    
    div[data-testid="stChatInput"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 10px rgba(185, 28, 28, 0.3);
    }
    
    /* 6. CUSTOM COMPONENTS */
    /* Sidebar Header */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem; 
    }
    
    .sidebar-header-container {
        background: linear-gradient(to right, #B71C1C, #9A1616); /* Subtle gradient */
        padding: 2rem 1.5rem 1.5rem 1.5rem;
        margin: -6rem -1rem 1.5rem -1rem; 
        color: white;
    }
    .sidebar-header-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 4px;
        letter-spacing: -0.02em;
    }
    
    /* Top Chat Banner - Refined */
    .top-banner {
        background: white; /* Switch to white for cleaner look */
        border-bottom: 1px solid #E2E8F0;
        padding: 1rem 0; /* Reduced padding */
        display: flex;
        align-items: center;
        margin-bottom: 2rem;
        /* No shadow for flat clean look */
    }
    .top-banner h3 {
        color: #1E293B !important; /* Dark Text */
        margin: 0;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .banner-icon-box {
        background: #FEF2F2; /* Light Red BG */
        color: #D32F2F;
        padding: 8px;
        border-radius: 8px;
        margin-right: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Empty State Card */
    .empty-state-frame {
        display: flex;
        justify-content: center;
        margin-top: 10vh;
    }
    .empty-state-card {
        background: white;
        padding: 4rem 2rem;
        border-radius: 24px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        text-align: center;
        max-width: 480px;
        width: 100%;
        border: 1px solid #F1F5F9;
    }
    
    /* Admin Footer Link specific styling */
    a[href*="Admin_Panel"] {
        display: block;
        background-color: #B71C1C !important;
        color: white !important;
        padding: 12px 16px;
        border-radius: 10px;
        text-decoration: none;
        text-align: center;
        margin-top: 2rem;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(183, 28, 28, 0.15);
        transition: all 0.2s;
    }
    a[href*="Admin_Panel"]:hover {
        background-color: #9A1616 !important;
        color: white !important;
        transform: translateY(-2px);
    }
    a[href*="Admin_Panel"] span {
        color: white !important; /* Force icon/text color */
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_file" not in st.session_state:
    st.session_state.selected_file = None

# --- Helper Functions ---
@st.cache_resource(show_spinner=False)
def load_chat_engine(selected_file=None):
    return get_chat_engine(selected_file=selected_file)

def reset_chat_history():
    st.session_state.messages = []

def render_pdf_page_as_image(file_name, page_number):
    """
    Renders a specific page of a PDF as an image using PyMuPDF.
    """
    try:
        # Construct path to data directory
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        file_path = os.path.join(data_dir, file_name)
        
        if not os.path.exists(file_path):
            return None, f"File not found: {file_name}"
            
        doc = fitz.open(file_path)
        # page_number is 1-indexed in metadata, but 0-indexed in fitz
        try:
             page_idx = int(page_number) - 1
        except ValueError:
             page_idx = 0
        
        if page_idx < 0 or page_idx >= len(doc):
             return None, f"Page {page_number} out of range"
             
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better quality
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img, None
        
    except Exception as e:
        return None, str(e)

# --- Sidebar: Document Selection ---
with st.sidebar:
    # 1. Custom Header
    st.markdown("""
    <div class="sidebar-header-container">
        <div class="sidebar-header-title">Documents</div>
        <div class="sidebar-header-subtitle">Select a PDF to ask questions</div>
    </div>
    """, unsafe_allow_html=True)
    
    docs = list_ingested_files()
    
    # Document List
    if not docs:
        st.info("No documents found.")
        
    for doc in docs:
        is_selected = st.session_state.selected_file == doc
        label = f"📄 {doc}"
        
        # We use standard buttons; CSS handles the 'active' red text style via kind="primary"
        if st.button(label, key=f"btn_{doc}", use_container_width=True, type="primary" if is_selected else "secondary"): 
            if st.session_state.selected_file != doc:
                st.session_state.selected_file = doc
                reset_chat_history()
                st.rerun()

    # Spacer to push Admin button to bottom (simple visual separation)
    st.markdown("<br>" * 5, unsafe_allow_html=True) 

    # Admin Login Footer (Solid Red Block via CSS)
    st.page_link("pages/Admin_Panel.py", label="🔒 Admin Login", icon=None)


# --- Main Content Area ---
selected_file = st.session_state.selected_file

if not selected_file:
    # --- EMPTY STATE (Card View) ---
    st.markdown("""
    <div class="empty-state-frame">
        <div class="empty-state-card">
            <div class="empty-icon-circle">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
            </div>
            <div class="empty-title">Select a Document</div>
            <div class="empty-subtitle">
                Choose a document from the sidebar to start asking questions about your PDF knowledge base.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # --- ACTIVE STATE (Chat) ---
    
    # 1. Top Red Banner
    st.markdown(f"""
    <div class="top-banner">
        <div class="banner-icon-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
        </div>
        <h3>{selected_file}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    chat_engine = load_chat_engine(selected_file)
    
    # Display Chat Messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    # Chat Input
    if prompt := st.chat_input(f"Ask about {selected_file}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    response = chat_engine.chat(prompt)
                    
                    # Check for source nodes/images
                    image_to_display = None
                    if hasattr(response, 'source_nodes') and response.source_nodes:
                         for node in response.source_nodes:
                             if 'file_name' in node.metadata and 'page_label' in node.metadata:
                                 img, err = render_pdf_page_as_image(node.metadata['file_name'], node.metadata['page_label'])
                                 if img:
                                     image_to_display = img
                                     break # Show top match
                    
                    # Display text
                    st.markdown(response.response)
                    
                    # Display Image if found
                    if image_to_display:
                        st.markdown("### 🖼️ Visual Context")
                        st.image(image_to_display, caption="Relevant Diagram/Page", use_container_width=True)
                    
                    # Citations
                    with st.expander("📚 Source Citations"):
                         if hasattr(response, 'source_nodes') and response.source_nodes:
                            for node in response.source_nodes:
                                 file_n = node.metadata.get('file_name', 'Unknown')
                                 page_n = node.metadata.get('page_label', 'Unknown')
                                 score = f"{node.score:.2f}" if node.score else "N/A"
                                 st.markdown(f"**{file_n} (Page {page_n})** - Score: {score}")
                                 st.caption(node.get_text()[:300] + "...")
                                 st.divider()

                    st.session_state.messages.append({"role": "assistant", "content": response.response})
                
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
