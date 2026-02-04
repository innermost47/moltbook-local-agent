import requests
import base64
import re
from typing import Dict, Optional
from src.utils import log
from src.settings import settings


class BlogManager:

    def __init__(self):
        self.blog_api_url = settings.BLOG_API_URL
        self.blog_api_key = settings.BLOG_API_KEY
        self.fal_api_key = settings.FAL_API_KEY
        self.blog_base_url = settings.BLOG_BASE_URL

    def generate_image(self, prompt: str) -> Optional[str]:
        try:
            url = "https://fal.run/fal-ai/flux/schnell"

            headers = {
                "Authorization": f"Key {self.fal_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            }

            enhanced_prompt = f"{prompt}. Digital art, modern, bold, powerful aesthetic. High quality, professional. NOT horror, NOT bloody, NOT violent."

            data = {
                "prompt": enhanced_prompt,
                "image_size": "landscape_16_9",
                "num_inference_steps": 4,
                "num_images": 1,
                "enable_safety_checker": True,
            }

            log.info(f"Generating image with prompt: {prompt[:50]}...")

            response = requests.post(url, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()

                if "images" in result and len(result["images"]) > 0:
                    image_url = result["images"][0]["url"]
                    log.success(f"Image generated, downloading...")

                    img_response = requests.get(image_url, timeout=30)

                    if img_response.status_code == 200:
                        image_bytes = img_response.content
                        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

                        content_type = img_response.headers.get(
                            "content-type", "image/png"
                        )
                        if "jpeg" in content_type or "jpg" in content_type:
                            mime_type = "image/jpeg"
                        elif "webp" in content_type:
                            mime_type = "image/webp"
                        else:
                            mime_type = "image/png"

                        data_uri = f"data:{mime_type};base64,{image_b64}"

                        log.success(
                            f"Image converted to base64 ({len(image_b64)} chars)"
                        )
                        return data_uri
                    else:
                        log.error(
                            f"Failed to download image: HTTP {img_response.status_code}"
                        )
                        return None
                else:
                    log.error("No images in fal.ai response")
                    return None
            else:
                log.error(f"fal.ai API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            log.error("Image generation timeout (60s)")
            return None
        except Exception as e:
            log.error(f"Image generation failed: {e}")
            return None

    def post_article(
        self, title: str, excerpt: str, content: str, image_prompt: str
    ) -> Dict:
        try:
            image_data = self.generate_image(image_prompt)

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

        html = html.replace("## ", "<h2>").replace("\n\n", "</h2>\n\n")
        html = html.replace("### ", "<h3>").replace("\n\n", "</h3>\n\n")

        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)

        paragraphs = html.split("\n\n")
        html = "".join([f"<p>{p}</p>\n" for p in paragraphs if p.strip()])

        return html
