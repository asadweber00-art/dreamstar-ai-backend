# Dreamstar AI Studio — Backend Kit

This is a **long-form orchestration backend**, not a bundled AI video model.
It accepts a story request, splits it into short scenes, calls a connected video
engine for each scene, then joins returned MP4 clips with FFmpeg.

## Important limitations — read first

- A 30-minute video at 10 seconds per scene requires about **180 separate clips**.
- This backend does not contain GPU weights or provide a free video-generation service.
- You must connect a real provider endpoint using `ENGINE_API_URL`; provider access,
  speed, limits and possible charges are controlled by that provider.
- The connected engine must return a completed, downloadable `videoUrl` for each
  scene. Async `jobId`-only engines need a provider-specific polling adapter.
- First scene receives the reference image. Later scenes rely on prompt continuity;
  strict character consistency requires an engine that supports persistent reference
  images/character IDs and a matching adapter.
- Audio narration, music and sound effects are not generated in this version.
- Job state is in memory and generated files use local storage. For reliable production,
  add Redis/database + persistent object storage before deploying on ephemeral hosting.
- Free hosts may sleep, time out, or delete files. A 30-minute job is not guaranteed
  to finish on a free tier.

## API

### `GET /health`
Reports API and FFmpeg status, plus whether an engine URL is configured.

### `POST /api/generate`
Header: `X-API-Key: <APP_ACCESS_KEY>` (if APP_ACCESS_KEY is set)

JSON:
```json
{
  "prompt": "A story about Sheru and Bunty...",
  "image": null,
  "ratio": "16:9",
  "storyDurationMinutes": 30,
  "sceneSeconds": 10,
  "quality": "1080p"
}
```

Returns:
```json
{"jobId":"...","status":"queued","statusUrl":"/api/status/..."}
```

### `GET /api/status/{jobId}`
Returns queued/generating/completed/failed status, progress and final `videoUrl`.

## Deploy

1. Deploy this folder as a Docker web service on a host that supports Docker and FFmpeg.
2. Set `APP_ACCESS_KEY` to a strong secret.
3. Set `ENGINE_API_URL` to the actual provider's completed-clip endpoint.
4. Set `ENGINE_ACCESS_TOKEN` only if that provider requires it.
5. Check `/health`; `engineConfigured` must be true and `ffmpeg` must be true.
6. Connect the deployed base URL and `APP_ACCESS_KEY` in Dreamstar AI Studio.

Do not put provider tokens in frontend code or public GitHub files.

## Honest status

This package provides the orchestration layer only. It is not proof that a video engine
is connected, and it cannot generate a video until a compatible engine endpoint is set.
