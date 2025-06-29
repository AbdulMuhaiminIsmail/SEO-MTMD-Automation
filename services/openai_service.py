import json
import time
from typing import List, Dict, Tuple
from openai import OpenAI
from config import OPENAI_API_KEY, MODEL_NAME, MAX_RETRIES, RETRY_DELAY
from utils.logger import logger

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def summarize_about_content(self, about_text: str) -> str:
        text = about_text
        prompt = f"""
        You are an SEO assistant. Analyze the following About Us page content and extract only the key insights that are useful for generating SEO meta titles and descriptions.

        ONLY include:
        - Business type
        - Services offered
        - Location or service area
        - Unique selling points (USPs)
        - Tone or brand personality
        - Anything important for search engine relevance

        Remove any vague marketing fluff or repeated information.

        Here is the About Us content:
        \"\"\"
        {text}
        \"\"\"

        Respond with a concise summary of the key SEO-relevant insights.
        """

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are an SEO analyst and an expert in summarizing content to include only the information needed to generate high-quality SEO metadata."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"SEO content summarization failed (attempt {attempt + 1}): {e}")
                time.sleep(RETRY_DELAY)

        return "Unable to extract SEO relevant content."
    
    def generate_meta_batch(self, urls: List[str], summarized_aboutus_content: str) -> Dict[str, Tuple[str, str]]:
        """Generate meta titles and descriptions for a batch of URLs"""
        prompt = self._build_prompt(urls)

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": f"You are an SEO expert that returns only JSON. Use this about us page summary to generate high quality SEO meta titles and descriptions: {summarized_aboutus_content}"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
                return self._parse_response(response_text, urls)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        return {url: ("N/A", "N/A") for url in urls}
    
    def _build_prompt(self, urls: List[str]) -> str:
        """Construct the prompt for batch processing"""
        url_list = "\n".join([f"- {url}" for url in urls])
        prompt = f"""
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

        Follow these tips from now for meta title:
        - Using brackets increases CTR by 38%.
        - Using numbers increases CTR by 36%.
        - Use provoking words from paid Google ads, e.g., free shipping, discounts, etc.

        For meta description:
        - Keep the length between 150-160 characters (920 pixels)
        - Add a Call-To-Action. ("Learn more", "Discover more", "Find out", "Get it", "Start now", "Unlock now")
        - Add Powerful and Emotional Words. ("proven", "guaranteed", "revolutionary", "exclusive", "essential")
        """

        return prompt
    
    def _parse_response(self, response_text: str, urls: List[str]) -> Dict[str, Tuple[str, str]]:
        """Parse OpenAI response into structured data"""
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
            logger.error("Failed to parse OpenAI response")
            return {url: ("N/A", "N/A") for url in urls}
