import re
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from typing import Dict, List
from config import TIMEOUT
from utils.logger import logger
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

class WordPressService:
    def __init__(self, wp_site, wp_username, wp_application_password):
        self.wp_username = wp_username
        self.wp_site = wp_site.rstrip('/')
        self.wp_sitemap_url = f"{wp_site}/page-sitemap.xml"
        self.wp_application_password = wp_application_password.replace(' ', '')
        self.auth = HTTPBasicAuth(self.wp_username, self.wp_application_password)
    
    def fetch_sitemap_urls(self) -> List[str]:
        """Fetch all URLs from WordPress sitemap"""
        try:
            response = requests.get(self.wp_sitemap_url, headers=HEADERS, timeout=TIMEOUT*2)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            return self._parse_sitemap(root)
        except Exception as e:
            logger.error(f"Sitemap fetch error: {str(e)}")
            return []
    
    def _parse_sitemap(self, root: ET.Element) -> List[str]:
        """Parse XML sitemap recursively"""
        urls = []
        namespace = {'ns': root.tag.split("}")[0].strip("{")}
        
        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall("ns:sitemap", namespace):
                loc = sitemap.find("ns:loc", namespace).text
                urls.extend(self.fetch_sitemap_urls(loc))
        elif root.tag.endswith("urlset"):
            for url in root.findall("ns:url", namespace):
                loc = url.find("ns:loc", namespace)
                if loc is not None:
                    urls.append(loc.text.rstrip('/'))
        return urls
    
    def get_page_ids_and_about_us_content(self, urls: List[str]) -> Dict[str, int]:
        """Get WordPress page IDs for a list of URLs (with pagination) and about us page content"""
        cleaned_text = ""
        page_ids = {}
        page = 1

        try:
            while True:
                endpoint = f"{self.wp_site}/wp-json/wp/v2/pages?per_page=100&page={page}"
                response = requests.get(endpoint, auth=self.auth, headers=HEADERS, timeout=TIMEOUT)
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    break  # No more pages

                for page_data in data:
                    if "about" in page_data['link'].lower() or "about" in page_data['slug'].lower():
                        raw_html = page_data['content']['rendered']
                        cleaned_text = self.clean_about_us_text(raw_html)
                    clean_url = page_data['link'].rstrip('/')
                    if clean_url in urls:
                        page_ids[clean_url] = page_data['id']

                page += 1

        except Exception as e:
            logger.error(f"Page ID fetch error: {str(e)}")

        return page_ids, cleaned_text
    
    def clean_about_us_text(self, raw_html: str) -> str:
        soup = BeautifulSoup(raw_html, "html.parser")

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Remove non-printable characters & unusual symbols
        text = re.sub(r"[^\x20-\x7E\n]+", "", text)

        # Remove excessive newlines
        text = re.sub(r"\n{2,}", "\n", text)

        # Remove promotional calls to action
        unwanted_phrases = [
            "Claim Your Lead Now!", 
            "Send Message", 
            "You agree to our friendly terms", 
            "Get Started",
            "Support",
            "Testimonial",
            "What they say about us"
        ]

        for phrase in unwanted_phrases:
            text = text.replace(phrase, "")

        return text
