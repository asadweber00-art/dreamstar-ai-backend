import base64
import binascii
import os
import secrets
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "generated"
VIDEO_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Dreamstar AI Studio Backend", version="1.0.0")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=20000)
    image: Optional[str] = None
    imageName: Optional[str] = None
    ratio: str = "16:9"
    duration: int = Field(default=5, ge=1, le=10)
    quality: str = "720p"

def decode_image_data_url(value: str) -> bytes:
    if not value.startswith("data:image/") or "," not in value:
        raise HTTPException(status_code=400, detail="Image must be a PNG, JPG or WEBP data URL.")
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0].lower()
    if mime not in {"image/png", "image/jpeg", "image/webp"} or ";base64" not in header.lower():
        raise HTTPException(status_code=400, detail="Only base64 PNG, JPG and WEBP images are supported.")
    if len(encoded) > 14 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is too large; use an image under 10 MB.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Could not decode the uploaded image.") from exc
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")
    return raw

def check_auth(authorization: Optional[str]) -> str:
    expected = os.getenv("APP_ACCESS_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Server setup incomplete: APP_ACCESS_KEY is missing.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid backend access key.")
    token = os.getenv("HF_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Server setup incomplete: HF_TOKEN is missing.")
    return token

@app.get("/")
def root():
    return {"service": "Dreamstar AI Studio Backend", "health": "/health", "generate": "POST /api/generate"}

@app.get("/health")
def health():
    return {"ok": True, "service": "Dreamstar AI Studio Backend", "generation_configured": bool(os.getenv("HF_TOKEN") and os.getenv("APP_ACCESS_KEY"))}

@app.post("/api/generate")
def generate(body: GenerateRequest, request: Request, authorization: Optional[str] = Header(default=None)):
    token = check_auth(authorization)
    model = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B")
    provider = os.getenv("HF_INFERENCE_PROVIDER", "fal-ai")
    try:
        client = InferenceClient(provider=provider, api_key=token)
        frames = max(17, min(161, body.duration * 16 + 1))
        if body.image:
            video_bytes = client.image_to_video(
                image=decode_image_data_url(body.image),
                prompt=body.prompt,
                model=model,
                num_frames=frames,
            )
        else:
            video_bytes = client.text_to_video(
                prompt=body.prompt,
                model=model,
                num_frames=frames,
            )
        if not video_bytes:
            raise RuntimeError("The inference provider returned an empty video.")
        video_id = uuid.uuid4().hex
        video_path = VIDEO_DIR / f"{video_id}.mp4"
        video_path.write_bytes(video_bytes)
        video_url = str(request.base_url).rstrip("/") + f"/videos/{video_id}.mp4"
        return {"videoUrl": video_url, "videoId": video_id, "duration": body.duration, "model": model}
    except HTTPException:
        raise
    except Exception as exc:
        safe = str(exc).replace(token, "[redacted]")[:500]
        raise HTTPException(
            status_code=502,
            detail=f"Video provider request failed: {safe}. Check provider/model availability and account limits."
        ) from exc

@app.get("/videos/{filename}")
def get_video(filename: str):
    if not filename.endswith(".mp4") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Video not found.")
    path = VIDEO_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video not found; generated files may be cleared when the server restarts.")
    return FileResponse(path, media_type="video/mp4", filename=filename)
