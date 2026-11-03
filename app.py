import os
import secrets
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

app = FastAPI(title="Dreamstar AI Studio Video Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=100000)
    image: Optional[str] = None
    imageName: Optional[str] = None
    ratio: Optional[str] = "16:9"
    duration: Optional[int] = 5
    storyDurationMinutes: Optional[int] = 30
    quality: Optional[str] = "720p"

@app.get("/health")
def health():
    return {"ok": True, "service": "Dreamstar AI Studio backend", "video_generation_tested": False}

@app.post("/api/generate")
def generate(body: GenerateRequest, request: Request, authorization: Optional[str] = Header(default=None)):
    expected_key = os.environ.get("APP_ACCESS_KEY", "")
    hf_token = os.environ.get("HF_TOKEN", "")
    if not expected_key or not hf_token:
        raise HTTPException(status_code=503, detail="Backend is not configured. Add HF_TOKEN and APP_ACCESS_KEY as Space secrets.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not supplied or not secrets.compare_digest(supplied, expected_key):
        raise HTTPException(status_code=401, detail="Invalid backend access key.")
    if body.image:
        raise HTTPException(status_code=400, detail="This first backend test supports text-to-video only. Remove the reference image and retry.")
    try:
        # Provider availability, model support, and billing depend on the user's Hugging Face account.
        client = InferenceClient(provider="fal-ai", api_key=hf_token)
        video_bytes = client.text_to_video(
            body.prompt,
            model="Wan-AI/Wan2.2-TI2V-5B",
            num_frames=81,
        )
        if not video_bytes:
            raise RuntimeError("The provider returned an empty video response.")
        return Response(content=video_bytes, media_type="video/mp4", headers={"Cache-Control": "no-store"})
    except Exception as exc:
        # Return a readable error but never expose credentials.
        raise HTTPException(status_code=502, detail=f"Video provider request failed: {str(exc)[:400]}") from exc
