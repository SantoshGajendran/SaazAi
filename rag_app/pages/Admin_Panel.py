import streamlit as st
import os
import time
import sys
# Add parent directory to path to import from ingest
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingest import ingest_document, list_ingested_files, delete_ingested_file
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="SaazAi Admin", layout="wide")

# --- Custom CSS for Admin Panel ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1E293B;
        background-color: #F8F9FC; /* Light background for whole admin page */
    }

    /* Login Card Positioning */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 80vh;
    }
    
    /* Headers */
    h1, h2, h3 {
        font-weight: 700 !important;
    }
    h1 { color: #1E293B !important; font-size: 1.8rem !important; }
    h2 { color: #1E293B !important; font-size: 1.2rem !important; opacity: 0.8; }
    
    /* Buttons */
    .stButton > button {
        background-color: #B71C1C !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #9A1616 !important;
        box-shadow: 0 4px 6px rgba(183, 28, 28, 0.2);
    }
    .stButton > button[kind="secondary"] {
        background-color: white !important;
        color: #B71C1C !important;
        border: 1px solid #B71C1C !important;
    }
    
    /* Cards */
    .card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
        margin-bottom: 1.5rem;
    }
    
    /* Dotted Upload Zone Styling Attempt (Applied to container of file uploader if possible, or just visual) */
    .upload-section {
        border: 2px dashed #CBD5E1;
        border-radius: 12px;
        background: #F8FAFC;
        padding: 3rem;
        text-align: center;
    }
    
    /* Metrics */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label { font-size: 0.85rem; color: #64748B; font-weight: 500; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #B71C1C; margin-top: 5px; }
    
    /* Hide Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- Authentication Logic ---
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

def check_password():
    password = st.session_state.get("password_input", "")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    if password == admin_password:
        st.session_state.admin_authenticated = True
        st.success("Login Successful")
    else:
        st.error("Incorrect Password")

def logout():
    st.session_state.admin_authenticated = False
    st.rerun()

# --- 1. LOGIN VIEW ---
if not st.session_state.admin_authenticated:
    # Centered Layout using Columns
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        # Visual Icon center
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="background: #B71C1C; width: 50px; height: 50px; border-radius: 10px; display: inline-flex; align-items: center; justify-content: center; color: white;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            </div>
            <h1 style="margin-top: 1rem;">Admin Access</h1>
            <p style="color: #64748B;">Manage PDF documents</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Form Container
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Admin Login")
            st.markdown("<p style='font-size: 0.9rem; color: #64748B; margin-bottom: 1.5rem;'>Enter your admin credentials</p>", unsafe_allow_html=True)
            
            st.text_input("Email", placeholder="admin@saazai.com (Demo)", key="email_input")
            st.text_input("Password", type="password", key="password_input")
            
            st.button("Login as Admin", on_click=check_password)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Back to Chat", type="secondary"):
                st.switch_page("app.py")
                
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("""
            <div style="text-align: center; margin-top: 2rem; color: #94A3B8; font-size: 0.8rem;">
                Demo credentials:<br>admin / admin123 (check .env)
            </div>
            """, unsafe_allow_html=True)

else:
    # --- 2. DASHBOARD VIEW ---
    
    # Header
    col_h1, col_h2 = st.columns([0.8, 0.2])
    with col_h1:
        st.markdown("# Admin Dashboard")
        st.markdown("Manage documents and uploads")
    with col_h2:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        st.write(f"Logged in as **Admin**")
        if st.button("Logout"):
            logout()
        st.markdown("</div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    # UPLOAD SECTION
    st.markdown("### 📤 Upload Documents")
    
    # We create a "Card" for upload
    with st.container():
        st.markdown('<div class="card" style="text-align: center;">', unsafe_allow_html=True)
        
        # Dotted Zone Visual (Note: The actual file_uploader will sit below this or we try to style it)
        # Streamlit's file uploader is hard to style internally, so we put it inside a clean card.
        
        st.markdown("""
        <div style="margin-bottom: 1rem;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#B71C1C" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Drag and drop PDF files here", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file:
            st.info(f"Selected: {uploaded_file.name}")
            if st.button("Select Files (Ingest)", type="primary"):
                 with st.spinner("Ingesting..."):
                    try:
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        data_dir = os.path.join(base_dir, "data")
                        if not os.path.exists(data_dir): os.makedirs(data_dir)
                        
                        file_path = os.path.join(data_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        ingest_document(file_path, original_filename=uploaded_file.name)
                        st.success(f"Successfully added {uploaded_file.name}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        else:
             st.markdown("<p style='color: #64748B;'>Drag and and drop PDF files here<br>or click to browse</p>", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


    # LIST SECTION
    st.markdown("### 📄 Uploaded Documents")
    
    files = list_ingested_files()
    
    if not files:
        st.info("No documents found.")
    else:
        # Wrap list in a card
        st.markdown('<div class="card" style="padding: 0;">', unsafe_allow_html=True)
        
        for i, file in enumerate(files):
            # Custom Row
            bg_color = "#F8FAFC" if i % 2 == 0 else "white"
            
            c1, c2, c3 = st.columns([0.1, 0.8, 0.1])
            with c1:
                st.markdown(f"<div style='padding: 1rem; text-align: center;'>📄</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div style='padding: 1rem; font-weight: 600;'>{file}<br><span style='font-size: 0.8rem; color: #64748B; font-weight: 400;'>Uploaded recently</span></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div style='padding: 0.8rem;'>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_{file}"):
                    delete_ingested_file(file)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
            if i < len(files) - 1:
                st.markdown("<hr style='margin: 0; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    # METRICS SECTION (Bottom)
    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Documents</div>
            <div class="metric-value">{len(files)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with m2:
        # Fake size calc for demo or real if easy
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Size</div>
            <div class="metric-value">9.3 MB</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Active Users</div>
            <div class="metric-value">24</div>
        </div>
        """, unsafe_allow_html=True)
