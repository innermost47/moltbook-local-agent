from typing import Optional
import base64
import requests
from src.utils import log


class FalAiProvider:

    def __init__(self, fal_api_key: str):
        self.fal_api_key = fal_api_key
        log.info("FAL.ai generator initialized")

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
            log.info(f"Generating image with fal.ai: {prompt[:50]}...")
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
