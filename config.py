import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# PROCESSED_PAGES_PER_MINUTE = BATCH_SIZE * REQUESTS_PER_MINUTE

# Generic Config
TIMEOUT = 15
BATCH_SIZE = 15

# Gemini Config
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_NAME = "gemini-1.5-flash"
MAX_RETRIES = 3
RETRY_DELAY = 5

# Google Sheets Config
SHARE_EMAIL = os.getenv("SHARE_EMAIL")
SHEET_TITLE = os.getenv("SHEET_TITLE")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SERVICE_ACCOUNT_FILE = "service_account.json"

with open(SERVICE_ACCOUNT_FILE, "w") as f:
    json.dump(json.loads(st.secrets["SERVICE_ACCOUNT_JSON"]), f)