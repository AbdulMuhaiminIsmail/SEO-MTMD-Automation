import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from typing import Dict, List
from config import TIMEOUT
from utils.logger import logger

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
            response = requests.get(self.wp_sitemap_url, timeout=TIMEOUT*2)
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
    
    def get_page_ids(self, urls: List[str]) -> Dict[str, int]:
        """Get WordPress page IDs for a list of URLs"""
        page_ids = {}
        endpoint = f"{self.wp_site}/wp-json/wp/v2/pages?per_page=100"
        
        try:
            response = requests.get(endpoint, auth=self.auth, timeout=TIMEOUT)
            response.raise_for_status()
            
            for page in response.json():
                clean_url = page['link'].rstrip('/')
                if clean_url in urls:
                    page_ids[clean_url] = page['id']
        except Exception as e:
            logger.error(f"Page ID fetch error: {str(e)}")
        
        return page_ids