# Dreamstar AI Studio — replacement backend

This package fixes the API contract used by the Dreamstar web app:
- `POST /api/generate` accepts JSON fields `prompt`, `image` (base64 data URL or null), `ratio`, `duration`, and `quality`.
- Successful response is JSON containing `videoUrl`, so the existing browser app can open and save the actual MP4.
- `GET /health` reports whether required secrets are present.
- `GET /videos/{id}.mp4` serves generated output while the server filesystem retains it.

## Required server secrets
Set these in your hosting provider's private environment settings (never put real values in GitHub):
- `HF_TOKEN`: a Hugging Face token with the permissions required by the chosen inference provider.
- `APP_ACCESS_KEY`: a long random password. Enter the same value in Dreamstar Studio's Access token field.

Optional settings:
- `HF_VIDEO_MODEL` (default `Wan-AI/Wan2.2-TI2V-5B`)
- `HF_INFERENCE_PROVIDER` (default `fal-ai`)
- `CORS_ORIGINS` (comma-separated site origins; `*` is the development default)

## Deploy
Use a Docker-compatible host that can run Python 3.11. The container listens on port 7860.

After deployment:
1. Open `https://YOUR-HOST/health`. It should return JSON with `ok: true`.
2. In Dreamstar Studio > Generation settings, set API URL to `https://YOUR-HOST/api/generate`.
3. Set Access token to the exact `APP_ACCESS_KEY`.
4. Submit a short test prompt and one reference image.

## Important limitations — read before deployment
- This is an API integration layer, not a bundled video model or GPU. It calls Hugging Face Inference Providers.
- Provider/model access, GPU capacity, queueing, and possible charges are controlled by Hugging Face and the selected provider. A Hugging Face token alone does not guarantee free video generation.
- A free Hugging Face Space may pause or run out of quota. This package cannot bypass that quota.
- Generated MP4 files are stored on the host's local filesystem. Ephemeral hosts may erase them after restart/redeploy; use persistent storage for a lasting gallery.
- The API currently supports short clips up to 10 seconds per request. Long-form 30–45 minute films require scene splitting, orchestration, storage, and many separate inference jobs; this package does not claim to do that.
- `1080p` is passed as a requested preference by the web UI but actual output resolution depends on the provider/model.
- No generation has been claimed as tested until a real request successfully returns a playable MP4.

## Local run
```bash
pip install -r requirements.txt
export HF_TOKEN="your-private-token"
export APP_ACCESS_KEY="your-long-random-secret"
uvicorn app:app --host 0.0.0.0 --port 7860
```
