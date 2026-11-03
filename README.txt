DREAMSTAR AI STUDIO — SECURE BACKEND KIT (FIRST SHORT-CLIP TEST)

IMPORTANT
- The previously shared Hugging Face token was revoked. Do not use it again.
- Do NOT paste your Hugging Face token into the public Netlify website.
- This kit separates the website (Netlify) from a server-side backend (Hugging Face Docker Space).
- Hugging Face Inference Providers may require available credits/payment. Free unlimited video generation is not guaranteed.
- This first backend supports text-to-video short clips only. It does not yet support reference-image-to-video, 30-minute single video, story stitching, voice or music.

PART A — UPDATE THE NETLIFY WEBSITE
1. Upload the contents of the `site` folder to your existing Netlify site (not the ZIP itself if Netlify asks for extracted files).
2. This front-end no longer sends the Hugging Face token directly to a provider. It sends a separate backend access key to your own backend.

PART B — CREATE THE BACKEND ON HUGGING FACE
1. Open https://huggingface.co/new-space while logged in.
2. Create a new Space. Choose Docker as the SDK. A name such as dreamstar-video-backend is fine. Public code is okay; NEVER put secret values in files.
3. Upload these three files from the `backend` folder to the root of the Space:
   - app.py
   - requirements.txt
   - Dockerfile
4. Open the Space Settings and find Variables and secrets.
5. Add these as Secrets (not public Variables):
   - HF_TOKEN = a NEW Hugging Face token with Inference Providers permission
   - APP_ACCESS_KEY = a separate private password you create for your own app, not your HF token
6. Because the previously shared token was revoked, create a new HF token only now, and keep it private. Do not paste it into ChatGPT or the website.
7. Wait for the Space to build. Check https://YOUR-SPACE-NAME.hf.space/health . It should return JSON with ok:true once the server is running. This only checks the server, not video generation.

PART C — CONNECT THE WEBSITE
1. Open the Space URL, usually https://YOUR-SPACE-NAME.hf.space
2. In Dreamstar AI Studio > Generation settings:
   Backend API URL: https://YOUR-SPACE-NAME.hf.space/api/generate
   Backend access key: the same APP_ACCESS_KEY value you saved in Space Secrets
3. Save connection.
4. Test with a short prompt and no reference image first.

TROUBLESHOOTING
- HTTP 401: backend access key in the website does not match APP_ACCESS_KEY.
- HTTP 503: HF_TOKEN or APP_ACCESS_KEY is missing from Space Secrets, or the Space needs restart/rebuild.
- HTTP 502: provider/model request failed, may be unavailable or require credits. Check Space logs and Hugging Face Inference Providers settings.
- /health returning ok:true does NOT prove the video provider works. Only a successful real video response proves that.
- The API response is expected to be MP4 bytes. The site handles a video/mp4 response.
