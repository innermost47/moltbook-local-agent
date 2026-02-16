import requests
import markdown
import nh3
from typing import Dict
from src.utils import log
from src.settings import settings
from src.providers.sd_provider import SDProvider
from src.providers.proxy_sd_provider import ProxySDProvider
from src.providers.fal_ai_provider import FalAiProvider


class BlogManager:

    def __init__(self, test_mode=False):
        self.test_mode = test_mode
        self.blog_api_url = settings.BLOG_API_URL
        self.blog_api_key = settings.BLOG_API_KEY
        self.fal_api_key = settings.FAL_API_KEY
        self.blog_base_url = settings.BLOG_BASE_URL
        if settings.USE_STABLE_DIFFUSION_LOCAL:
            self.image_generator = SDProvider()
        elif settings.USE_SD_PROXY:
            self.image_generator = ProxySDProvider(
                proxy_url=settings.OLLAMA_PROXY_URL,
                api_key=settings.OLLAMA_PROXY_API_KEY,
            )
        else:
            self.image_generator = FalAiProvider(fal_api_key=settings.FAL_API_KEY)

    def post_article(
        self, title: str, excerpt: str, content: str, image_prompt: str
    ) -> Dict:
        if getattr(self, "test_mode", False):
            log.info(f"🧪 [MOCK] Bypassing real blog post for: {title[:30]}...")
            return {
                "success": True,
                "url": "https://blog.test/mock-article",
                "slug": "mock-article",
                "article_id": 999,
            }
        try:
            image_data = self.image_generator.generate_image(image_prompt)

            if not image_data:
                log.error("Failed to generate image, aborting article post")
                return {"success": False, "error": "Image generation failed"}

            headers = {
                "X-API-Key": self.blog_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            data = {
                "title": title,
                "excerpt": excerpt,
                "content": content,
                "image_data": image_data,
            }

            log.info(f"Posting article to blog: {title[:50]}...")

            response = requests.post(
                f"{self.blog_api_url}/post_article.php",
                headers=headers,
                json=data,
                timeout=30,
            )

            if response.status_code == 201:
                result = response.json()
                article_url = result.get("url", "")

                log.success(f"Article published: {article_url}")

                return {
                    "success": True,
                    "url": article_url,
                    "slug": result.get("slug", ""),
                    "article_id": result.get("article_id"),
                }
            else:
                error_msg = response.json().get("error", "Unknown error")
                log.error(f"Failed to post article: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            log.error("Blog post request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            log.error(f"Failed to post article: {e}")
            return {"success": False, "error": str(e)}

    def format_article_safe(self, markdown_content: str) -> str:
        extensions = ["extra", "sane_lists", "nl2br"]
        raw_html = markdown.markdown(markdown_content, extensions=extensions)
        return nh3.clean(raw_html)

    def list_articles(self) -> list:
        try:
            headers = {
                "X-API-Key": self.blog_api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            url = f"{self.blog_api_url}/get_articles.php"
            log.info(f"Syncing from: {url}")
            response = requests.get(
                url,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    articles = result.get("articles", [])
                    log.info(
                        f"Successfully retrieved {len(articles)} existing articles."
                    )
                    return articles
                else:
                    log.error(f"API returned error during sync: {result.get('error')}")
                    return []
            else:
                log.error(f"HTTP Error {response.status_code} while fetching articles.")
                return []

        except Exception as e:
            log.error(f"Failed to fetch blog articles list: {e}")
            return []
