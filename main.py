import time
import pandas as pd
import streamlit as st
from services.wordpress import WordPressService
from services.openai_service import OpenAIService
from services.google_sheets import GoogleSheetsService
from config import BATCH_SIZE
from utils.logger import logger

# Set page config
st.set_page_config(
    page_title="Meta Generator",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# AMOLED Dark Theme CSS
def set_custom_theme():
    st.markdown("""
    <style>
    :root {
        --bg: #000000;
        --card-bg: #121212;
        --text: #FFFFFF;
        --border: #333333;
        --primary: #FFFFFF;
        --secondary: #AAAAAA;
    }
    
    html, body, .stApp {
        background-color: var(--bg);
        color: var(--text);
        font-family: 'Inter', sans-serif;
    }
    
    h1 {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: var(--text) !important;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: var(--text) !important;
        margin-bottom: 1rem !important;
    }
    
    .card {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 2rem;
        border: 1px solid var(--border);
        margin-bottom: 2rem;
    }
    
    .stTextInput>div>div>input {
        background-color: var(--card-bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
    }
    
    .stButton>button {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        border: 1px solid var(--text) !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton>button:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    .stButton>button:focus {
        box-shadow: 0 0 0 2px var(--text) !important;
    }
    
    .progress-container {
        height: 6px;
        background-color: var(--border);
        border-radius: 3px;
        margin: 2rem 0;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background-color: var(--text);
        width: 0%;
        transition: width 0.4s ease;
    }
    
    .loader {
        display: flex;
        justify-content: center;
        padding: 2rem 0;
    }
    
    .spinner {
        width: 40px;
        height: 40px;
        border: 4px solid var(--border);
        border-top: 4px solid var(--text);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .info-text {
        color: var(--secondary);
        font-size: 0.9rem;
        margin-top: 0.5rem;
    }
    
    .error-box {
        background-color: rgba(255, 0, 0, 0.1);
        border: 1px solid #FF3333;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
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
if 'error' not in st.session_state:
    st.session_state.error = None

def batch_process(site_url: str, username: str, application_password: str):
    """Main processing pipeline"""
    logger.info("Starting meta generation process")
    
    # Initialize services
    gpt = OpenAIService()
    wp_service = WordPressService(site_url, username, application_password)
    
    # Step 1: Fetch all pages
    logger.info("Fetching sitemap URLs...")
    urls = wp_service.fetch_sitemap_urls()
    logger.info(f"Found {len(urls)} pages")
    
    # Step 2: Get WordPress page IDs
    logger.info("Mapping URLs to page IDs...")
    page_ids, cleaned_aboutus_text = wp_service.get_page_ids_and_about_us_content(urls)
    logger.info("URLs mapped to page IDs...")

    # Step 3: Summarize AboutUs page content
    logger.info("Summarizing About us page content")
    summarized_about_us_text = gpt.summarize_about_content(cleaned_aboutus_text)
    logger.info("Summarized About us page content successfully")
    
    # Step 4: Process in batches
    results = []
    total_urls = len(urls)
    
    for i in range(0, total_urls, BATCH_SIZE):
        batch = urls[i:i+BATCH_SIZE]
        logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(total_urls//BATCH_SIZE)+1}")

        # Generate meta for batch
        meta_data = gpt.generate_meta_batch(batch, summarized_about_us_text)
        
        # Prepare results
        for url in batch:
            title, desc = meta_data.get(url, ("N/A", "N/A"))
            results.append({
                "post_id": page_ids.get(url, "N/A"),
                "url": url,
                "post_type": "page",
                "_yoast_wpseo_title": title,
                "_yoast_wpseo_metadesc": desc
            })
        
        # Rate limiting (adjust based on gpt's rate limits)
        if i + BATCH_SIZE < total_urls:
            time.sleep(1)  # Small delay between batches
    
    # Step 5: Create Google Sheet
    logger.info("Creating CSV File...")

    df = pd.DataFrame(results)
    df = df[["post_id", "post_type", "_yoast_wpseo_title", "_yoast_wpseo_metadesc", "url"]]
    csv = df.to_csv(index=False).encode('utf-8')
    
    logger.info("CSV created successfully!")

    return csv

def show_progress():
    progress = (st.session_state.current_step - 1) / 3
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {progress*100}%"></div>
    </div>
    """, unsafe_allow_html=True)

def handle_error(e):
    """Translate known technical errors to user-friendly messages"""
    error_msg = str(e).lower()

    if "sitemap" in error_msg or "fetching sitemap" in error_msg:
        return "Error in fetching the sitemap. Please ensure your website has a valid and accessible sitemap.xml."

    elif "page ids" in error_msg or "mapping urls" in error_msg:
        return "Error in mapping URLs to WordPress page IDs. Please ensure the WordPress REST API is enabled and reachable."

    elif "gpt" in error_msg or "openai" in error_msg or "meta generation" in error_msg or "response" in error_msg:
        return "Error in generating meta tags using AI. The model may have failed to respond. Please retry or check your OpenAI API configuration."

    elif "google sheets" in error_msg or "create sheet" in error_msg:
        return "Error in creating the Google Sheet. Please ensure the service account has access and your email is valid."

    elif "connection" in error_msg or "timeout" in error_msg:
        return "Network issue occurred. Please check your internet connection."

    elif "authentication" in error_msg or "unauthorized" in error_msg:
        return "Authentication failed. Please double-check your WordPress credentials or permissions."

    elif "email" in error_msg:
        return "Invalid email address. Please make sure it's correctly formatted and accessible."

    elif "spreadsheet not initialized" in error_msg:
        return "Sheet creation failed or was skipped. Please try again."

    else:
        return "An unexpected error occurred. Please retry or contact support with the error details."

def step_website():
    st.title("Website Information")
    show_progress()
    
    with st.container():
        st.header("Enter your website URL")
        
        website_url = st.text_input(
            "Website address (e.g., https://example.com)",
            value=st.session_state.form_data.get('website_url', ''),
            key="website_url"
        )
        
        st.markdown('<p class="info-text">We\'ll use this to fetch your pages</p>', unsafe_allow_html=True)
        
        st.session_state.form_data['website_url'] = website_url
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("Continue"):
            if website_url and website_url.startswith(('http://', 'https://')):
                st.session_state.current_step = 2
                st.session_state.error = None
                st.rerun()
            else:
                st.session_state.error = "Please enter a valid website URL starting with http:// or https://"

def step_credentials():
    st.title("WordPress Credentials")
    show_progress()
    
    with st.container():
        st.header("Enter your WordPress credentials")
        
        username = st.text_input(
            "WordPress username",
            value=st.session_state.form_data.get('username', ''),
            key="username"
        )
        
        app_password = st.text_input(
            "Application password",
            type="password",
            value=st.session_state.form_data.get('app_password', ''),
            key="app_password",
            help="You can create an application password in WordPress Users → Edit → Application Passwords"
        )
        
        st.session_state.form_data['username'] = username
        st.session_state.form_data['app_password'] = app_password
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2, gap='large')
        with col1:
            if st.button("Back"):
                st.session_state.current_step = 1
                st.rerun()
        with col2:
            if st.button("Continue"):
                if username and app_password:
                    st.session_state.current_step = 3
                    st.session_state.error = None
                    st.rerun()
                else:
                    st.session_state.error = "Please enter both username and application password"

def step_email():
    st.title("Email Sharing")
    show_progress()
    
    with st.container():
        st.header("Where should we send the results?")
        
        email = st.text_input(
            "Your email address",
            value=st.session_state.form_data.get('email', ''),
            key="email",
            help="We'll share the Google Sheet with this address"
        )
        
        st.session_state.form_data['email'] = email
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back"):
                st.session_state.current_step = 2
                st.rerun()
        with col2:
            if st.button("Review"):
                if email and "@" in email and "." in email.split("@")[-1]:
                    st.session_state.current_step = 4
                    st.session_state.error = None
                    st.rerun()
                else:
                    st.session_state.error = "Please enter a valid email address"

def step_review():
    st.title("Review & Generate")
    show_progress()
    
    with st.container():
        
        st.header("Confirm your details")
        
        st.subheader("Website URL")
        st.write(st.session_state.form_data.get('website_url', ''))
        
        st.subheader("WordPress Username")
        st.write(st.session_state.form_data.get('username', ''))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back"):
                st.session_state.current_step = 3
                st.rerun()
        with col2:
            if st.button("Generate Meta Data"):
                st.session_state.processing = True
                st.rerun()

def step_processing():
    st.title("Processing")
    show_progress()
    
    with st.container():
        
        st.header("Generating your meta data")
        st.write("This may take a few minutes...")
        
        st.markdown('<div class="loader"><div class="spinner"></div></div>', unsafe_allow_html=True)
        
        try:
            form_data = st.session_state.form_data
            csv = batch_process(
                site_url=form_data["website_url"],
                username=form_data["username"],
                application_password=form_data["app_password"]
            )
            
            st.session_state.csv = csv
            st.session_state.processing = False
            st.session_state.completed = True
            st.rerun()
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            st.session_state.error = handle_error(e)
            st.session_state.processing = False
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def step_results():
    st.title("Results Ready")
    show_progress()
    
    with st.container():
        st.header("Your meta data is ready")
        st.write("You can now view and edit the generated meta titles and descriptions from the CSV:")
        
        cols = st.columns(1)
        
        with cols[0]:
            if st.button("Continue to Download"):
                st.session_state.current_step = 5
                st.rerun()

def step_download():
    st.title("Download Results")
    show_progress()
    
    with st.container():
        st.header("Download your data")    
        st.write("You can download the CSV file with all generated meta data:")
        
        col1, col2 = st.columns(2, gap='large')
        
        with col1:
            st.download_button(
                label="📥 Download Meta CSV",
                data=st.session_state.csv,
                file_name="meta_data.csv",
                mime="text/csv"
            )
        
        with col2:       
            if st.button("Start New Request"):
                st.session_state.current_step = 1
                st.session_state.form_data = {}
                st.session_state.completed = False
                st.rerun()

# Main app flow
if st.session_state.error:
    st.markdown(f'<div class="error-box">{st.session_state.error}</div>', unsafe_allow_html=True)

if st.session_state.processing:
    step_processing()
elif st.session_state.completed:
    if st.session_state.current_step == 4:
        step_results()
    else:
        step_download()
else:
    if st.session_state.current_step == 1:
        step_website()
    elif st.session_state.current_step == 2:
        step_credentials()
    elif st.session_state.current_step == 3:
        step_review()