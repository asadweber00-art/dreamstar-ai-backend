import base64
import binascii
import os
import secrets
import uuid
import logging

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dreamstar")

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "generated"
VIDEO_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="DREAMSTAR AI STUDIO",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
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


def check_auth(authorization):
    expected = os.getenv("APP_ACCESS_KEY", "")
    token = os.getenv("HF_TOKEN", "")

    if not expected or not token:
        raise HTTPException(
            status_code=503,
            detail="Backend environment setup incomplete."
        )

    supplied = (authorization or "").strip()

    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()

    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid access key."
        )

    return token


def decode_image(value):
    if not value:
        return None

    if not value.startswith("data:image/") or "," not in value:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format."
        )

    header, encoded = value.split(",", 1)

    if ";base64" not in header.lower():
        raise HTTPException(
            status_code=400,
            detail="Base64 image required."
        )

    mime = header[5:].split(";")[0].lower()

    if mime not in (
        "image/png",
        "image/jpeg",
        "image/webp"
    ):
        raise HTTPException(
            status_code=400,
            detail="PNG, JPG and WEBP supported."
        )

    if len(encoded) > 14 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds size limit."
        )

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid image data."
        )

    if not raw:
        raise HTTPException(
            status_code=400,
            detail="Empty image."
        )

    return raw


@app.get("/")
def home():
    return {
        "studio": "DREAMSTAR AI STUDIO",
        "version": "2.0.0",
        "status": "online",
        "health": "/health",
        "generation": "/api/generate"
    }


@app.get("/health")
def health():
    configured = bool(
        os.getenv("HF_TOKEN")
        and os.getenv("APP_ACCESS_KEY")
    )

    return {
        "ok": True,
        "service": "DREAMSTAR AI STUDIO",
        "generation_configured": configured
    }


@app.post("/api/generate")
def generate(
    body: GenerateRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None)
):

    token = check_auth(authorization)

    model = os.getenv(
        "HF_VIDEO_MODEL",
        "Wan-AI/Wan2.2-TI2V-5B"
    )

    provider = os.getenv(
        "HF_INFERENCE_PROVIDER",
        "fal-ai"
    )

    image_data = decode_image(body.image)

    try:
        client = InferenceClient(
            provider=provider,
            api_key=token
        )

        frames = max(
            17,
            min(161, body.duration * 16 + 1)
        )

        if image_data:
            video = client.image_to_video(
                image=image_data,
                prompt=body.prompt,
                model=model,
                num_frames=frames
            )
        else:
            video = client.text_to_video(
                prompt=body.prompt,
                model=model,
                num_frames=frames
            )

        if not video:
            raise RuntimeError("Empty video response.")

        if not video.startswith(b"\x00\x00\x00"):
            logger.info("Video received from provider.")

        video_id = uuid.uuid4().hex

        filename = f"{video_id}.mp4"
        filepath = VIDEO_DIR / filename

        filepath.write_bytes(video)

        video_url = (
            str(request.base_url).rstrip("/")
            + f"/videos/{filename}"
        )

        return {
            "success": True,
            "videoUrl": video_url,
            "videoId": video_id,
            "duration": body.duration,
            "quality": body.quality,
            "ratio": body.ratio,
            "model": model,
            "status": "completed"
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Video generation failed")

        safe_error = str(exc).replace(
            token,
            "[REDACTED]"
        )[:400]

        raise HTTPException(
            status_code=502,
            detail={
                "success": False,
                "status": "failed",
                "error": safe_error
            }
        )


@app.get("/videos/{filename}")
def get_video(filename: str):

    if (
        not filename.endswith(".mp4")
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(
            status_code=404,
            detail="Video not found."
        )

    filepath = VIDEO_DIR / filename

    if not filepath.is_file():
        raise HTTPException(
            status_code=404,
            detail="Video not found."
        )

    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=filename
    )
