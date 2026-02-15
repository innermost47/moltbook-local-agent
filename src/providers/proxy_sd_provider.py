import requests
from typing import Optional
from src.utils import log


class ProxySDProvider:

    def __init__(
        self,
        proxy_url: str = "http://127.0.0.1:8000",
        api_key: Optional[str] = None,
    ):
        self.proxy_url = proxy_url.rstrip("/")
        self.api_key = api_key
        self.endpoint = f"{self.proxy_url}/api/generate-image"

        log.info(f"Proxy SD generator initialized (endpoint: {self.endpoint})")

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 576,
        num_inference_steps: int = 4,
        guidance_scale: float = 0.0,
        seed: Optional[int] = None,
    ) -> Optional[str]:
        try:
            enhanced_prompt = (
                f"{prompt}. Digital art, modern, bold, powerful aesthetic. "
                "High quality, professional. NOT horror, NOT bloody, NOT violent."
            )

            if negative_prompt is None:
                negative_prompt = (
                    "blurry, bad quality, distorted, ugly, bad anatomy, "
                    "horror, blood, violence, gore, disturbing"
                )

            log.info(f"Generating image via proxy: {prompt[:50]}...")

            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["X-API-Key"] = self.api_key

            payload = {
                "prompt": enhanced_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
            }

            if seed is not None:
                payload["seed"] = seed
                log.info(f"Using seed: {seed}")

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("success") and "data_uri" in result:
                    data_uri = result["data_uri"]
                    log.success(
                        f"Image generated successfully via proxy ({result.get('size', 'unknown size')})"
                    )
                    log.success(f"Base64 length: {len(data_uri)} chars")
                    return data_uri
                else:
                    log.error("Invalid response format from proxy")
                    return None

            elif response.status_code == 403:
                log.error("Proxy authentication failed - check OLLAMA_PROXY_API_KEY")
                return None

            elif response.status_code == 503:
                log.error("Proxy service unreachable - is the server running?")
                return None

            else:
                log.error(f"Proxy API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            log.error("Image generation timeout (120s)")
            return None

        except requests.exceptions.ConnectionError:
            log.error(
                f"Cannot connect to proxy at {self.proxy_url} - is the server running?"
            )
            return None

        except Exception as e:
            log.error(f"Image generation failed: {e}")
            return None
