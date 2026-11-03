Dreamstar AI Studio — Render backend starter

Repository files should be extracted (not uploaded as a ZIP file) into the GitHub repository.

Backend deployment:
- This package includes Dockerfile, app.py, requirements.txt, and render.yaml at repository root.
- Create a Render Web Service from the GitHub repository.
- Runtime: Docker (or let Render detect Dockerfile).
- Add environment variables in Render dashboard:
  APP_ACCESS_KEY = choose a long random secret of your own
  HF_TOKEN = your Hugging Face token (never share it in chat or put it in frontend code)
- Deploy, then open https://YOUR-RENDER-URL/health to check service health.

IMPORTANT LIMITATIONS:
- /health only confirms the server is running.
- Video generation has NOT been tested and depends on Hugging Face provider/model availability and account credits.
- The starter currently requests a short 81-frame video, not a full 30-minute finished story.
- Do not claim this is a complete production app until a real generation request is tested.
- The static website is in the site/ folder and should continue to be hosted separately (for example on Netlify).
