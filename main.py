import time
import streamlit as st
from streamlit_extras.stoggle import stoggle

from services.wordpress import WordPressService
from services.gemini_service import GeminiService
from services.google_sheets import GoogleSheetsService

from config import BATCH_SIZE
from utils.logger import logger

def batch_process(site_url: str, username: str, application_password: str, email: str):
    """Main processing pipeline"""
    logger.info("Starting meta generation process")
    
    # Initialize services
    gemini = GeminiService()
    sheets = GoogleSheetsService(email)
    wp_service = WordPressService(site_url, username, application_password)
    
    # Step 1: Fetch all pages
    logger.info("Fetching sitemap URLs...")
    urls = wp_service.fetch_sitemap_urls()
    logger.info(f"Found {len(urls)} pages")
    
    # Step 2: Get WordPress page IDs
    logger.info("Mapping URLs to page IDs...")
    page_ids = wp_service.get_page_ids(urls)

    # Step 3: Process in batches
    results = []
    total_urls = len(urls)
    
    for i in range(0, total_urls, BATCH_SIZE):
        batch = urls[i:i+BATCH_SIZE]
        logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(total_urls//BATCH_SIZE)+1}")
        
        # Generate meta for batch
        meta_data = gemini.generate_meta_batch(batch)
        
        # Prepare results
        for url in batch:
            title, desc = meta_data.get(url, ("N/A", "N/A"))
            results.append({
                "post_id": page_ids.get(url, "N/A"),
                "url": url,
                "title": title,
                "description": desc
            })
        
        # Rate limiting (adjust based on Gemini's rate limits)
        if i + BATCH_SIZE < total_urls:
            time.sleep(1)  # Small delay between batches
    
    # Step 4: Create Google Sheet
    logger.info("Creating Google Sheet...")
    sheet_urls = sheets.create_sheet(results)
    
    logger.info("Process completed successfully!")

    return sheet_urls

# Set page config with wider layout
st.set_page_config(
    page_title="Meta Titles & Meta Descriptions Generator",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS with animations and bigger fonts
def set_custom_theme():
    st.markdown("""
    <style>
    :root {
        --primary: #6e48aa;
        --secondary: #9d50bb;
        --accent: #4776E6;
        --dark: #121212;
        --darker: #0a0a0a;
        --light: #f8f9fa;
        --success: #4BB543;
    }
    
    html, body, .stApp {
        background: linear-gradient(135deg, var(--darker), var(--dark));
        color: var(--light);
        font-family: 'Inter', sans-serif;
    }
    
    h1 {
        font-size: 2.8rem !important;
        background: linear-gradient(to right, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-size: 1.8rem !important;
        color: var(--light) !important;
        margin-bottom: 1rem !important;
    }
    
    .card {
        background: rgba(30, 30, 30, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 2rem;
        animation: fadeIn 0.5s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stTextInput>div>div>input, 
    .stTextInput>div>div>textarea {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 1.1rem !important;
    }
    
    .stButton>button {
        background: linear-gradient(to right, var(--primary), var(--secondary));
        color: white !important;
        border: none !important;
        padding: 14px 28px !important;
        border-radius: 12px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(110, 72, 170, 0.3) !important;
        width: 100% !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(110, 72, 170, 0.4) !important;
    }
    
    .stButton>button:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(110, 72, 170, 0.5) !important;
    }
    
    .success-box {
        background: rgba(75, 181, 67, 0.2) !important;
        border: 1px solid var(--success) !important;
    }
    
    .progress-bar {
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
        margin: 2rem 0;
        overflow: hidden;
    }
    
    .progress {
        height: 100%;
        background: linear-gradient(to right, var(--primary), var(--secondary));
        border-radius: 3px;
        transition: width 0.4s ease;
    }
    
    .loader {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100px;
    }
    
    .spinner {
        width: 50px;
        height: 50px;
        border: 5px solid rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        border-top: 5px solid var(--primary);
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

set_custom_theme()

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'completed' not in st.session_state:
    st.session_state.completed = False

# Progress bar
def show_progress():
    progress = st.session_state.current_step / 4
    st.markdown(f"""
    <div class="progress-bar">
        <div class="progress" style="width: {progress*100}%"></div>
    </div>
    """, unsafe_allow_html=True)

# Step 1: Website URL
def step_website():
    st.title("Website Info")
    show_progress()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header("What's your website?")
        
        website_url = st.text_input(
            "Website URL",
            value=st.session_state.form_data.get('website_url', ''),
            placeholder="https://example.com",
            key="website_url"
        )
        
        st.session_state.form_data['website_url'] = website_url
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue to Step 2 →"):
            if website_url:
                st.session_state.current_step = 2
                st.rerun()
            else:
                st.error("Please enter a valid website URL")

# Step 2: Credentials
def step_credentials():
    st.title("WordPress Credentials")
    show_progress()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header("What's the WP Username & Application Password we are working with?")
        
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input(
                "WordPress Username",
                value=st.session_state.form_data.get('username', ''),
                placeholder="e.g, admin",
                key="username"
            )
            st.session_state.form_data['username'] = username
            
        with col2:
            app_password = st.text_input(
                "Application Password",
                type="password",
                value=st.session_state.form_data.get('app_password', ''),
                placeholder="xxxx xxxx xxxx xxxx",
                key="app_password"
            )
            st.session_state.form_data['app_password'] = app_password
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 1
                st.rerun()
        with col2:
            if st.button("Continue to Step 3 →"):
                if username and app_password:
                    st.session_state.current_step = 3
                    st.rerun()
                else:
                    st.error("Please enter both wp_username and application password")

# Step 3: Email
def step_email():
    st.title("Email Sharing")
    show_progress()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header("Which email to provide access of sheet to?")
        
        email = st.text_input(
            "Email Address",
            value=st.session_state.form_data.get('email', ''),
            placeholder="your@email.com",
            key="email"
        )
        st.session_state.form_data['email'] = email
        
        stoggle(
            "Why do we need this?",
            "The Google Sheets CSV would be shared with this email."
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 2
                st.rerun()
        with col2:
            if st.button("Review and Generate →"):
                if email:
                    st.session_state.current_step = 4
                    st.rerun()
                else:
                    st.error("Please enter a valid email address")

# Step 4: Review and Generate
def step_review():
    st.title("✅ Review & Generate")
    show_progress()
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.header("Confirm your details")
        
        st.subheader("Website URL")
        st.markdown(f"`{st.session_state.form_data.get('website_url', '')}`")
        
        st.subheader("WordPress Username")
        st.markdown(f"`{st.session_state.form_data.get('username', '')}`")
        
        st.subheader("Email Address")
        st.markdown(f"`{st.session_state.form_data.get('email', '')}`")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back"):
                st.session_state.current_step = 3
                st.rerun()
        with col2:
            if st.button("✨ Generate Meta Data", type="primary"):
                st.session_state.processing = True
                st.rerun()

# Processing Step
def step_processing():
    st.title("⚙️ Processing")
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        st.header("Generating your meta titles and descriptions")
        st.markdown("This may take a few minutes...")
        
        st.markdown('<div class="loader"><div class="spinner"></div></div>', unsafe_allow_html=True)
        
        # Start processing

        form_data = st.session_state.form_data
        sheet_urls = batch_process(
            site_url=form_data["website_url"],
            username=form_data["username"],
            application_password=form_data["app_password"],
            email=form_data["email"]
        )

        # Set results
        st.session_state.sheet_url = sheet_urls["view_url"]
        st.session_state.csv_url = sheet_urls["csv_url"]
        
        st.session_state.processing = False
        st.session_state.completed = True
        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Results Step
def step_results():
    st.title("🎉 Results Ready!")
    
    with st.container():
        st.markdown('<div class="card success-box">', unsafe_allow_html=True)
        
        st.header("Your meta data is ready!")
        st.markdown("""
        We've successfully generated all meta titles and descriptions for your website.
        You can access the results in the following ways:
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 View in Google Sheets", type="primary"):
                st.markdown(f"[Open Google Sheets]({st.session_state.sheet_url})", unsafe_allow_html=True)
        with col2:
            if st.button("📥 Download CSV", type="primary"):
                GoogleSheetsService().remove_urls()
                st.markdown(f"[Download CSV]({st.session_state.csv_url})", unsafe_allow_html=True)
        
        if st.button("🔄 Start New Request"):
            st.session_state.current_step = 1
            st.session_state.form_data = {}
            st.session_state.completed = False
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# Main app flow
if st.session_state.processing:
    step_processing()
elif st.session_state.completed:
    step_results()
else:
    if st.session_state.current_step == 1:
        step_website()
    elif st.session_state.current_step == 2:
        step_credentials()
    elif st.session_state.current_step == 3:
        step_email()
    elif st.session_state.current_step == 4:
        step_review()