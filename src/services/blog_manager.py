import requests
import re
from typing import Dict
from src.utils import log
from src.settings import settings
from src.generators import (
    FalAiImageGenerator,
    StableDiffusionImageGenerator,
    ProxySDImageGenerator,
)


class BlogManager:

    def __init__(self):
        self.blog_api_url = settings.BLOG_API_URL
        self.blog_api_key = settings.BLOG_API_KEY
        self.fal_api_key = settings.FAL_API_KEY
        self.blog_base_url = settings.BLOG_BASE_URL
        if settings.USE_STABLE_DIFFUSION_LOCAL:
            self.image_generator = StableDiffusionImageGenerator()
        elif settings.USE_SD_PROXY:
            self.image_generator = ProxySDImageGenerator(
                proxy_url=settings.OLLAMA_PROXY_URL,
                api_key=settings.OLLAMA_PROXY_API_KEY,
            )
        else:
            self.image_generator = FalAiImageGenerator()

    def post_article(
        self, title: str, excerpt: str, content: str, image_prompt: str
    ) -> Dict:
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

    def format_article_html(self, markdown_content: str) -> str:
        html = markdown_content

        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

        html = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", html)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"__(.+?)__", r"<strong>\1</strong>", html)
        html = re.sub(r"_(.+?)_", r"<em>\1</em>", html)

        html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"(<li>.*?</li>\n)+", r"<ul>\g<0></ul>", html, flags=re.DOTALL)

        html = re.sub(r"^\d+\. (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

        html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)

        html = re.sub(
            r"^```(\w+)?\n(.*?)\n```$",
            r"<pre><code>\2</code></pre>",
            html,
            flags=re.MULTILINE | re.DOTALL,
        )

        paragraphs = html.split("\n\n")
        formatted_paragraphs = []

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            if not re.match(r"^<(h[1-6]|ul|ol|pre|blockquote)", p):
                p = f"<p>{p}</p>"
            formatted_paragraphs.append(p)

        html = "\n".join(formatted_paragraphs)

        return html
