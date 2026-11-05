DREAMSTAR AI STUDIO — BACKEND REPLACEMENT

Upload these files to the backend repository, replacing the old backend files:
- app.py
- requirements.txt
- Dockerfile
- .dockerignore
- README.md
- README-DEPLOY.txt

Keep secrets OUT of GitHub. Add HF_TOKEN and APP_ACCESS_KEY in the host's private environment settings.

Health check: https://YOUR-HOST/health
Generation endpoint: https://YOUR-HOST/api/generate

In the website's Generation settings:
API URL = https://YOUR-HOST/api/generate
Access token = same value as APP_ACCESS_KEY

HONEST STATUS:
This package is prepared but not deployed or live-tested. It calls an external Hugging Face inference provider; free access and model availability are not guaranteed. The paused Hugging Face Space quota is not bypassed by these files. Do not delete the old repository/files until the replacement has been uploaded and its /health endpoint checked.
