import os
import base64
import binascii
import secrets
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from huggingface_hub import InferenceClient

app = FastAPI(title="Dreamstar AI Studio Video Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
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
    return {
        "ok": True,
        "service": "Dreamstar AI Studio backend",
        "image_to_video": True,
        "video_generation_tested": False
    }

def decode_image(value: str) -> bytes:
    try:
        if value.startswith("data:"):
            header, encoded = value.split(",", 1)
            if not header.startswith("data:image/"):
                raise ValueError("Only image files are accepted.")
        else:
            encoded = value

        image_bytes = base64.b64decode(encoded, validate=True)

        if not image_bytes:
            raise ValueError("Empty image.")

        if len(image_bytes) > 10 * 1024 * 1024:
            raise ValueError("Image must be 10 MB or smaller.")

        if not image_bytes.startswith(
            (b"\x89PNG", b"\xff\xd8\xff", b"RIFF")
        ):
            raise ValueError("Unsupported or invalid image format.")

        return image_bytes

    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

@app.post("/api/generate")
def generate(
    body: GenerateRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None)
):
    expected_key = os.environ.get("APP_ACCESS_KEY", "")
    hf_token = os.environ.get("HF_TOKEN", "")

    if not expected_key or not hf_token:
        raise HTTPException(
            status_code=503,
            detail="Backend is not configured. Add HF_TOKEN and APP_ACCESS_KEY."
        )

    supplied = (authorization or "").removeprefix("Bearer ").strip()

    if not supplied or not secrets.compare_digest(supplied, expected_key):
        raise HTTPException(status_code=401, detail="Invalid backend access key.")

    try:
        client = InferenceClient(
            provider="fal-ai",
            api_key=hf_token
        )

        frames = max(17, min(161, int(body.duration or 5) * 24))

        if body.image:
            image_bytes = decode_image(body.image)

            video_bytes = client.image_to_video(
                image_bytes,
                prompt=body.prompt,
                model="Wan-AI/Wan2.2-I2V-A14B",
                num_frames=frames
            )
        else:
            video_bytes = client.text_to_video(
                body.prompt,
                model="Wan-AI/Wan2.2-TI2V-5B",
                num_frames=frames
            )

        if not video_bytes:
            raise RuntimeError("Provider returned an empty video.")

        return Response(
            content=video_bytes,
            media_type="video/mp4",
            headers={"Cache-Control": "no-store"}
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Video provider failed. Check model availability, HF token, and provider access."
        )
