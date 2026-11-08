DREAMSTAR AI STUDIO BACKEND — QUICK DEPLOY

1) Upload the ZIP contents to your backend GitHub repository.
2) Deploy using Docker on a host that supports Docker + FFmpeg.
3) Add these private environment variables:
   APP_ACCESS_KEY = your own long random secret
   ENGINE_API_URL = your real provider's video generation endpoint
   ENGINE_ACCESS_TOKEN = provider token, if required
4) Open /health. Check engineConfigured=true and ffmpeg=true.
5) In Dreamstar frontend, set API URL to your backend base URL and access key to APP_ACCESS_KEY.

IMPORTANT:
No real video provider is bundled. No provider URL/token means generation will fail honestly.
30 minutes = about 180 clips at 10 seconds each. Free compute and unlimited generation
cannot be promised. This version does not generate voice/music/SFX.
