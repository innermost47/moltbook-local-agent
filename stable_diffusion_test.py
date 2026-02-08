import torch
from diffusers import AutoPipelineForText2Image
import os
from datetime import datetime


def check_cuda():
    if torch.cuda.is_available():
        print(f"[OK] CUDA available - GPU: {torch.cuda.get_device_name(0)}")
        print(
            f"[OK] VRAM available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
        )
        return "cuda"
    else:
        print("[WARNING] CUDA not available - using CPU (slower)")
        return "cpu"


def generate_image(
    prompt="a beautiful landscape with mountains and a lake at sunset, highly detailed, 8k",
    negative_prompt="blurry, bad quality, distorted, ugly, bad anatomy",
    num_inference_steps=4,
    guidance_scale=0.0,
    width=512,
    height=512,
    seed=None,
):
    print("\n" + "=" * 70)
    print("STABLE DIFFUSION TURBO - Generation Test")
    print("=" * 70)

    device = check_cuda()

    print("\n[1/3] Loading model...")
    print("       Model: stabilityai/sd-turbo")

    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sd-turbo",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        variant="fp16" if device == "cuda" else None,
    )
    pipe = pipe.to(device)

    if device == "cuda":
        pipe.enable_attention_slicing()
        print("[OK] GPU optimizations enabled")

    print("[OK] Model loaded\n")

    generator = None
    if seed is not None:
        generator = torch.Generator(device=device).manual_seed(seed)
        print(f"[INFO] Seed set to: {seed}")

    print("[2/3] Generation parameters:")
    print(f"       Prompt: {prompt}")
    print(f"       Negative: {negative_prompt}")
    print(f"       Steps: {num_inference_steps}")
    print(f"       Guidance: {guidance_scale}")
    print(f"       Resolution: {width}x{height}")

    print("\n[3/3] Generating image...")

    # Generation
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        width=width,
        height=height,
        generator=generator,
    ).images[0]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/sd_turbo_{timestamp}.png"
    image.save(filename)

    print(f"[OK] Image generated and saved: {filename}")
    print("=" * 70)
    print("\n✓ Done! Open the file to see the result.\n")

    return image, filename


if __name__ == "__main__":
    test_prompts = {
        "landscape": "a beautiful landscape with mountains and a lake at sunset, highly detailed, 8k, photorealistic",
        "portrait": "portrait of a cyberpunk character, neon lights, futuristic city background, highly detailed",
        "abstract": "abstract digital art, vibrant colors, geometric shapes, modern art style",
        "nature": "enchanted forest with glowing mushrooms, magical atmosphere, fantasy art, detailed",
    }

    selected = "landscape"

    print(f"\nGenerating: {selected}")
    print(f"Prompt: {test_prompts[selected]}\n")

    image, filepath = generate_image(
        prompt=test_prompts[selected],
        num_inference_steps=4,
        width=512,
        height=512,
        seed=42,
    )

    print(f"\nYou can change the prompt by modifying the 'selected' variable")
    print(f"Available presets: {', '.join(test_prompts.keys())}")
