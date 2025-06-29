import time
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict
from config import SERVICE_ACCOUNT_FILE, SCOPES, SHEET_TITLE
from utils.logger import logger

class GoogleSheetsService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GoogleSheetsService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return  # Skip re-initialization

        self.creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        self.client = gspread.authorize(self.creds)
        self.spreadsheet = None
        self._initialized = True  # Flag to avoid re-running __init__

    def create_sheet(self, data: List[Dict]) -> object:
        """Create Google Sheet with data and return URLs"""
        try:
            time.sleep(1)
            self.spreadsheet = self.client.create(SHEET_TITLE)
            time.sleep(1)

            worksheet = self.spreadsheet.sheet1
            worksheet.update_title("Metadata")

            # Prepare headers and data
            headers = ["post_id", "post_type", "_yoast_wpseo_title", "_yoast_wpseo_metadesc", "url"]
            rows = [headers] + [
                [item["post_id"], "page", item["title"], item["description"], item["url"]]
                for item in data
            ]

            worksheet.update(rows)

            return self.spreadsheet
        except Exception as e:
            logger.error(f"Google Sheets error: {str(e)}")
            raise

    def remove_urls(self, spreadsheet):
        """Delete the 'url' column (Column E / index 5) from the current spreadsheet"""
        try:
            if not spreadsheet:
                raise Exception("Spreadsheet not initialized. Call create_sheet() first.")

            worksheet = spreadsheet.sheet1
            worksheet.delete_columns(5)
            logger.info("URL column removed successfully.")
        except Exception as e:
            logger.error(f"Failed to remove URL column: {str(e)}")
            raise
