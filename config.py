import os
import json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# PROCESSED_PAGES_PER_MINUTE = BATCH_SIZE * REQUESTS_PER_MINUTE
# CURRENT = 15 * 12

# Generic Config
TIMEOUT = 30
BATCH_SIZE = 15

# OpenAI Config
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
MODEL_NAME = "gpt-4.1"
MAX_RETRIES = 3
RETRY_DELAY = 5

# Google Sheets Config
SHEET_TITLE = "MTMD"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SERVICE_ACCOUNT_FILE = "service_account.json"

with open(SERVICE_ACCOUNT_FILE, "w") as f:
    json.dump(json.loads(st.secrets["SERVICE_ACCOUNT_JSON"]), f)