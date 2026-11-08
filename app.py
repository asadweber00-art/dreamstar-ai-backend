import os, uuid, json, time, shutil, subprocess, threading
from pathlib import Path
from typing import Optional
import requests
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_KEY = os.getenv("APP_ACCESS_KEY", "")
ENGINE_URL = os.getenv("ENGINE_API_URL", "").rstrip("/")
ENGINE_TOKEN = os.getenv("ENGINE_ACCESS_TOKEN", "")
OUT = Path(os.getenv("OUTPUT_DIR", "/data/generated"))
OUT.mkdir(parents=True, exist_ok=True)
JOBS = {}
LOCK = threading.Lock()

app = FastAPI(title="Dreamstar AI Studio Backend", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3)
    image: Optional[str] = None  # data:image/...;base64,...
    ratio: str = "16:9"
    storyDurationMinutes: int = Field(default=1, ge=1, le=45)
    quality: str = "1080p"
    sceneSeconds: int = Field(default=10, ge=5, le=10)

def auth(x_api_key: Optional[str]):
    if APP_KEY and x_api_key != APP_KEY:
        raise HTTPException(401, "Invalid API key")

def split_story(prompt: str, count: int):
    # Keep the user's story intent while requesting a distinct continuous scene.
    return [f"""Create scene {i+1} of {count} in one continuous cinematic 3D animated story.
Maintain exactly the same character identities, faces, clothes, colors and visual style as previous scenes.
Story and creative direction: {prompt}
Scene {i+1}/{count}. Make this scene visually coherent and suitable for seamless editing.
Do not add titles, subtitles, logos or watermarks.""" for i in range(count)]

def engine_generate(scene_prompt, image, ratio, seconds, quality):
    if not ENGINE_URL:
        raise RuntimeError("ENGINE_API_URL is not configured. Connect a real image-to-video/text-to-video engine first.")
    payload = {"prompt": scene_prompt, "image": image, "ratio": ratio, "duration": seconds, "quality": quality}
    headers = {"Content-Type": "application/json"}
    if ENGINE_TOKEN:
        headers["X-API-Key"] = ENGINE_TOKEN
        headers["Authorization"] = f"Bearer {ENGINE_TOKEN}"
    r = requests.post(ENGINE_URL, json=payload, headers=headers, timeout=1800)
    r.raise_for_status()
    data = r.json()
    url = data.get("videoUrl") or data.get("video_url") or data.get("url")
    if not url:
        raise RuntimeError("Engine did not return videoUrl. This backend adapter expects a completed clip URL.")
    clip = requests.get(url, timeout=1800)
    clip.raise_for_status()
    return clip.content

def run_job(job_id, req):
    try:
        minutes = req["storyDurationMinutes"]
        seconds = req["sceneSeconds"]
        total_seconds = minutes * 60
        count = (total_seconds + seconds - 1) // seconds
        prompts = split_story(req["prompt"], count)
        clips_dir = OUT / job_id
        clips_dir.mkdir(parents=True, exist_ok=True)
        concat_file = clips_dir / "concat.txt"
        for i, scene_prompt in enumerate(prompts):
            with LOCK:
                JOBS[job_id]["status"] = "generating"
                JOBS[job_id]["currentScene"] = i + 1
                JOBS[job_id]["totalScenes"] = count
                JOBS[job_id]["progress"] = round(i / count * 90, 1)
            content = engine_generate(scene_prompt, req.get("image") if i == 0 else None,
                                      req["ratio"], seconds, req["quality"])
            clip_path = clips_dir / f"scene_{i+1:04d}.mp4"
            clip_path.write_bytes(content)
        with concat_file.open("w", encoding="utf-8") as f:
            for i in range(count):
                p = clips_dir / f"scene_{i+1:04d}.mp4"
                f.write(f"file '{p.as_posix()}'\n")
        output = OUT / f"{job_id}.mp4"
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
               "-c", "copy", str(output)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        with LOCK:
            JOBS[job_id].update(status="completed", progress=100, videoUrl=f"/generated/{job_id}.mp4")
    except Exception as e:
        with LOCK:
            JOBS[job_id].update(status="failed", error=str(e))

@app.get("/")
def root():
    return {"name": "Dreamstar AI Studio Backend", "status": "online", "note": "A real ENGINE_API_URL is required for generation."}

@app.get("/health")
def health():
    return {"ok": True, "engineConfigured": bool(ENGINE_URL), "ffmpeg": shutil.which("ffmpeg") is not None}

@app.post("/api/generate")
def generate(req: GenerateRequest, background: BackgroundTasks, x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    job_id = str(uuid.uuid4())
    with LOCK:
        JOBS[job_id] = {"jobId": job_id, "status": "queued", "progress": 0, "currentScene": 0, "totalScenes": 0}
    background.add_task(run_job, job_id, req.model_dump())
    return {"jobId": job_id, "status": "queued", "statusUrl": f"/api/status/{job_id}"}

@app.get("/api/status/{job_id}")
def status(job_id: str, x_api_key: Optional[str] = Header(None)):
    auth(x_api_key)
    with LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found (job state is in-memory and resets on server restart)")
    return job

@app.get("/generated/{filename}")
def generated(filename: str):
    from fastapi.responses import FileResponse
    path = OUT / filename
    if not path.exists() or path.parent != OUT:
        raise HTTPException(404, "Video not found")
    return FileResponse(path, media_type="video/mp4", filename=filename)
