import google.generativeai as genai
import json
from typing import List, Dict, Tuple
from config import GEMINI_API_KEY, MODEL_NAME, MAX_RETRIES, RETRY_DELAY
from utils.logger import logger
import time

class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(MODEL_NAME)
    
    def generate_meta_batch(self, urls: List[str]) -> Dict[str, Tuple[str, str]]:
        """Generate meta titles and descriptions for a batch of URLs"""
        prompt = self._build_prompt(urls)
        
        for attempt in range(MAX_RETRIES):
            try:
                response = self.model.generate_content(prompt)
                return self._parse_response(response.text, urls)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
        
        return {url: ("N/A", "N/A") for url in urls}
    
    def _build_prompt(self, urls: List[str]) -> str:
        """Construct the prompt for batch processing"""
        url_list = "\n".join([f"- {url}" for url in urls])
        return f"""
You are an SEO expert. For each of the following URLs, generate an SEO-optimized meta title and meta description.
Return ONLY a JSON response where each URL is a key with title and description as values.

URLs:
{url_list}

Format:
{{
  "url1": {{
    "title": "Optimized meta title",
    "description": "SEO-optimized meta description"
  }},
  "url2": {{
    "title": "...",
    "description": "..."
  }}
}}

Follow these guidelines:
- Use brackets and numbers to increase CTR
- Keep descriptions 150-160 characters
- Include CTAs like "Learn more", "Discover"
- Use powerful words: "proven", "guaranteed"
"""
    
    def _parse_response(self, response_text: str, urls: List[str]) -> Dict[str, Tuple[str, str]]:
        """Parse Gemini response into structured data"""
        try:
            data = json.loads(response_text.strip("```json\n").strip("```"))
            return {
                url: (
                    data.get(url, {}).get("title", "N/A"),
                    data.get(url, {}).get("description", "N/A")
                )
                for url in urls
            }
        except json.JSONDecodeError:
            logger.error("Failed to parse Gemini response")
            return {url: ("N/A", "N/A") for url in urls}