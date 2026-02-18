import httpx
import os
import json
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
from src.providers.sd_provider import SDProvider
from src.utils import log
from src.settings import settings

load_dotenv()

app = FastAPI(title="Moltbook Ollama Gateway")

OLLAMA_PROXY_API_KEY = os.environ.get("OLLAMA_PROXY_API_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

sd_generator = SDProvider()


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 576
    num_inference_steps: int = 4
    guidance_scale: float = 0.0
    seed: Optional[int] = None


async def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not OLLAMA_PROXY_API_KEY or api_key != OLLAMA_PROXY_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized access")


@app.post("/api/generate-image")
async def generate_image(payload: ImageGenerationRequest, _=Depends(verify_api_key)):
    try:
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Generating image: {payload.prompt[:50]}..."
        )

        data_uri = sd_generator.generate_image(
            prompt=payload.prompt,
            negative_prompt=payload.negative_prompt,
            width=payload.width,
            height=payload.height,
            num_inference_steps=payload.num_inference_steps,
            guidance_scale=payload.guidance_scale,
            seed=payload.seed,
        )

        if data_uri is None:
            raise HTTPException(status_code=500, detail="Image generation failed")

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Image generated successfully"
        )

        return JSONResponse(
            {
                "success": True,
                "data_uri": data_uri,
                "format": "png",
                "size": f"{payload.width}x{payload.height}",
            }
        )

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Image generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_ollama(path: str, request: Request, _=Depends(verify_api_key)):
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=10.0,
            read=None,
            write=None,
            pool=None,
        )
    ) as client:
        url = f"{OLLAMA_URL}/{path}"
        body = await request.body()
        if path == "api/chat" or path == "api/generate":
            try:
                data = json.loads(body)
                if "options" not in data:
                    data["options"] = {}

                data["options"]["num_ctx"] = settings.NUM_CTX_OLLAMA

                body = json.dumps(data).encode("utf-8")
                log.success(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Context window forced to {settings.NUM_CTX_OLLAMA} for {path}"
                )
            except Exception as e:
                log.error(f"Failed to inject context options: {e}")
            log.success(
                f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Proxying {path} for external agent..."
            )
        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ["host", "content-length"]
        }
        try:
            log.info(f"REQUEST BODY: {body}")
            ollama_request = client.build_request(
                method=request.method,
                url=url,
                content=body,
                params=request.query_params,
                headers=headers,
            )
            ollama_resp = await client.send(ollama_request, stream=True)

            async def stream_and_log():
                full_response = []
                async for chunk in ollama_resp.aiter_raw():
                    full_response.append(chunk)
                    yield chunk
                try:
                    complete_content = b"".join(full_response).decode("utf-8")
                    if "api/chat" in path or "api/generate" in path:
                        log.info(f"📄 FULL BOT RESPONSE ({path}):\n{complete_content}")
                except Exception as log_err:
                    log.error(f"Failed to log proxy response: {log_err}")

            return StreamingResponse(
                stream_and_log(),
                status_code=ollama_resp.status_code,
                headers=dict(ollama_resp.headers),
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Ollama service is unreachable")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("🚀 Starting Moltbook Ollama Gateway with SD Turbo support...")
    print(f"📡 Ollama URL: {OLLAMA_URL}")
    print(f"🎨 SD Turbo: Ready for on-demand image generation")
    uvicorn.run(app, host="127.0.0.1", port=8000)
