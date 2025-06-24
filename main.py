from typing import List, Dict
from services.wordpress import WordPressService
from services.gemini_service import GeminiService
from services.google_sheets import GoogleSheetsService
from config import BATCH_SIZE
from utils.logger import logger
import time

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

if __name__ == "__main__":
    batch_process()