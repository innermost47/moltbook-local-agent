import httpx
import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(title="Moltbook Ollama Gateway")

OLLAMA_PROXY_API_KEY = os.environ.get("OLLAMA_PROXY_API_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


async def verify_api_key(request: Request):
    api_key = request.headers.get("X-API-Key")
    if not OLLAMA_PROXY_API_KEY or api_key != OLLAMA_PROXY_API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized access")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_ollama(path: str, request: Request, _=Depends(verify_api_key)):
    async with httpx.AsyncClient(timeout=None) as client:
        url = f"{OLLAMA_URL}/{path}"
        body = await request.body()
        if path == "api/chat" or path == "api/generate":
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Proxying {path} for external agent..."
            )

        headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in ["host", "content-length"]
        }

        try:
            ollama_request = client.build_request(
                method=request.method,
                url=url,
                content=body,
                params=request.query_params,
                headers=headers,
            )

            ollama_resp = await client.send(ollama_request, stream=True)

            return StreamingResponse(
                ollama_resp.aiter_raw(),
                status_code=ollama_resp.status_code,
                headers=dict(ollama_resp.headers),
            )

        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Ollama service is unreachable")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":

    uvicorn.run(app, host="127.0.0.1", port=8000)
