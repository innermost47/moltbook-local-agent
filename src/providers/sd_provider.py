try:
    import torch
    from diffusers import AutoPipelineForText2Image
except Exception as e:
    pass
import base64
from io import BytesIO
from typing import Optional
import gc
from src.utils import log


class SDProvider:
    def __init__(
        self,
        model_id: str = "stabilityai/sd-turbo",
        device: Optional[str] = None,
    ):
        self.model_id = model_id
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.pipe = None

        log.info(
            f"SD Turbo generator initialized (device: {self.device}, model will load on first use)"
        )

        if self.device == "cuda":
            vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            log.info(f"GPU: {torch.cuda.get_device_name(0)} ({vram_gb:.1f}GB VRAM)")

    def _load_model(self):
        if self.pipe is not None:
            log.info("Model already loaded, skipping")
            return

        log.info(f"Loading SD Turbo model: {self.model_id}...")

        try:
            self.pipe = AutoPipelineForText2Image.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                variant="fp16" if self.device == "cuda" else None,
            )
            self.pipe = self.pipe.to(self.device)
            if self.device == "cuda":
                self.pipe.enable_attention_slicing()
                log.info("Memory optimizations enabled")

            log.success(f"SD Turbo loaded successfully on {self.device}")

        except Exception as e:
            log.error(f"Failed to load SD Turbo: {e}")
            raise

    def _unload_model(self):
        if self.pipe is not None:
            log.info("Unloading model and clearing GPU cache...")
            del self.pipe
            self.pipe = None
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                log.success("GPU cache cleared")
            else:
                log.success("Model unloaded")

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
            self._load_model()

            enhanced_prompt = (
                f"{prompt}. Digital art, modern, bold, powerful aesthetic. "
                "High quality, professional. NOT horror, NOT bloody, NOT violent."
            )

            if negative_prompt is None:
                negative_prompt = (
                    "blurry, bad quality, distorted, ugly, bad anatomy, "
                    "horror, blood, violence, gore, disturbing"
                )

            log.info(f"Generating image with SD Turbo: {prompt[:50]}...")

            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
                log.info(f"Using seed: {seed}")

            image = self.pipe(
                prompt=enhanced_prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                generator=generator,
            ).images[0]

            log.success("Image generated successfully")

            buffered = BytesIO()
            image.save(buffered, format="PNG", optimize=True)
            image_bytes = buffered.getvalue()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            data_uri = f"data:image/png;base64,{image_b64}"

            log.success(f"Image converted to base64 ({len(image_b64)} chars)")

            return data_uri

        except Exception as e:
            log.error(f"Image generation failed: {e}")
            return None

        finally:
            self._unload_model()
