(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const promptEl = $('prompt');
  const imageInput = $('imageInput');
  const preview = $('preview');
  const canvasImage = $('canvasImage');
  const dropzone = $('dropzone');
  const generateBtn = $('generate');
  const resultbox = $('resultbox');
  const settingsModal = $('settingsModal');
  let referenceDataUrl = null;
  let referenceName = '';
  let busy = false;

  const SETTINGS_KEY = 'dreamstar-ai-studio-settings-v1';
  const CREATIONS_KEY = 'dreamstar-ai-studio-creations-v1';
  const readJson = (key, fallback) => {
    try { const value = JSON.parse(localStorage.getItem(key)); return value ?? fallback; }
    catch (_) { return fallback; }
  };
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));

  function setResult(title, detail, icon = '✧') {
    resultbox.innerHTML = `<div class="resulticon">${icon}</div><div><b>${escapeHtml(title)}</b><span>${escapeHtml(detail)}</span></div>`;
  }
  function setBusy(value) {
    busy = value;
    generateBtn.disabled = value;
    const span = generateBtn.querySelector('span');
    if (span) span.textContent = value ? 'Connecting to video engine…' : 'Generate video';
  }
  function loadSettings() {
    const settings = readJson(SETTINGS_KEY, {});
    $('apiUrl').value = settings.apiUrl || '';
    $('apiToken').value = settings.apiToken || '';
  }
  function getCreations() { return readJson(CREATIONS_KEY, []); }
  function saveCreation(item) {
    const items = getCreations();
    items.unshift(item);
    try { localStorage.setItem(CREATIONS_KEY, JSON.stringify(items.slice(0, 50))); }
    catch (_) { setResult('Video generated, but not saved to history', 'Browser storage is full. Save or download the video directly.', '!'); }
  }
  function showLibrary() {
    let modal = $('libraryModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'libraryModal';
      modal.className = 'modal';
      modal.innerHTML = '<div class="modalcard librarycard"><button class="close" id="closeLibrary" aria-label="Close">×</button><div class="eyebrow">YOUR WORKSPACE</div><h2>My Creations</h2><p>Only real video links returned by your connected engine are listed here.</p><div id="libraryItems"></div></div>';
      document.body.appendChild(modal);
      modal.querySelector('#closeLibrary').addEventListener('click', () => modal.classList.remove('show'));
      modal.addEventListener('click', (event) => { if (event.target === modal) modal.classList.remove('show'); });
    }
    const items = getCreations();
    const list = modal.querySelector('#libraryItems');
    if (!items.length) {
      list.innerHTML = '<div class="resultbox"><div class="resulticon">✧</div><div><b>No saved creations yet</b><span>Generated videos from a connected engine will appear here.</span></div></div>';
    } else {
      list.innerHTML = items.map((item) => `<div class="libraryitem"><div><b>${escapeHtml(item.title || 'Untitled video')}</b><small>${escapeHtml(item.createdAt || '')} · ${escapeHtml(item.quality || '')}</small></div><a href="${escapeHtml(item.videoUrl)}" target="_blank" rel="noopener noreferrer">Open video ↗</a></div>`).join('');
    }
    modal.classList.add('show');
  }

  promptEl.addEventListener('input', () => { $('count').textContent = `${promptEl.value.length.toLocaleString()} characters · no app limit`; });
  imageInput.addEventListener('change', () => {
    const file = imageInput.files && imageInput.files[0];
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      imageInput.value = ''; setResult('Unsupported image format', 'Choose a PNG, JPG or WEBP reference image.', '!'); return;
    }
    if (file.size > 10 * 1024 * 1024) {
      imageInput.value = ''; setResult('Image is too large', 'Please choose an image smaller than 10 MB.', '!'); return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      referenceDataUrl = String(reader.result || '');
      referenceName = file.name;
      preview.src = referenceDataUrl;
      preview.style.display = 'block';
      canvasImage.src = referenceDataUrl;
      canvasImage.style.display = 'block';
      const playmark = document.querySelector('.playmark');
      const canvastext = document.querySelector('.canvastext');
      if (playmark) playmark.style.display = 'none';
      if (canvastext) canvastext.style.display = 'none';
      setResult('Reference image ready', `${referenceName} is selected. No video has been generated yet.`, '✓');
    };
    reader.onerror = () => setResult('Could not read image', 'Try selecting the image again.', '!');
    reader.readAsDataURL(file);
  });

  $('settingsNav').addEventListener('click', () => { loadSettings(); settingsModal.classList.add('show'); });
  $('closeSettings').addEventListener('click', () => settingsModal.classList.remove('show'));
  settingsModal.addEventListener('click', (event) => { if (event.target === settingsModal) settingsModal.classList.remove('show'); });
  $('saveSettings').addEventListener('click', () => {
    const apiUrl = $('apiUrl').value.trim();
    const apiToken = $('apiToken').value.trim();
    if (apiUrl) {
      try { const parsed = new URL(apiUrl); if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Invalid protocol'); }
      catch (_) { setResult('Invalid API URL', 'Enter a valid http:// or https:// API endpoint.'); return; }
    }
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify({ apiUrl, apiToken }));
      settingsModal.classList.remove('show');
      setResult(apiUrl ? 'API settings saved' : 'API connection not configured', apiUrl ? 'Settings saved in this browser. Saving settings does not verify the engine.' : 'Add your backend endpoint when it is ready. No generation request was sent.', '✓');
    } catch (_) { setResult('Could not save settings', 'Your browser may block local storage.'); }
  });
  $('libraryNav').addEventListener('click', showLibrary);

  async function parseResponse(response) {
    const raw = await response.text();
    let data = {};
    if (raw) { try { data = JSON.parse(raw); } catch (_) { data = { message: raw.slice(0, 500) }; } }
    if (!response.ok) {
      const message = data.error || data.message || data.detail || `Server returned HTTP ${response.status}`;
      throw new Error(message);
    }
    return data;
  }

  function findVideoUrl(data) {
    return data?.videoUrl || data?.video_url || data?.url || data?.video?.url ||
      data?.output?.videoUrl || data?.output?.video_url || data?.output?.video?.url ||
      data?.result?.video?.url || data?.result?.url || null;
  }

  async function pollHostedQueue(data, headers) {
    const statusUrl = data.status_url || data.statusUrl;
    const responseUrl = data.response_url || data.responseUrl;
    if (!statusUrl || !responseUrl) return data;
    setResult('Video job accepted', 'Waiting for the hosted engine to finish the real video…', '…');
    const deadline = Date.now() + 8 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      const statusResponse = await fetch(statusUrl, { headers: { 'Accept': 'application/json', ...(headers.Authorization ? { Authorization: headers.Authorization } : {}) } });
      const statusData = await parseResponse(statusResponse);
      const status = String(statusData.status || statusData.state || '').toUpperCase();
      if (status === 'COMPLETED' || status === 'SUCCEEDED' || status === 'SUCCESS') {
        const resultResponse = await fetch(responseUrl, { headers: { 'Accept': 'application/json', ...(headers.Authorization ? { Authorization: headers.Authorization } : {}) } });
        return await parseResponse(resultResponse);
      }
      if (status === 'FAILED' || status === 'ERROR' || status === 'CANCELLED') {
        throw new Error(statusData.error || statusData.message || `Video provider job ${status.toLowerCase()}.`);
      }
    }
    throw new Error('The video job is still running after 8 minutes. Check the provider dashboard before trying again.');
  }

  function renderVideoResult(videoUrl, prompt, payload, isBlob) {
    const item = { title: prompt.length > 70 ? `${prompt.slice(0, 67)}…` : prompt, prompt, videoUrl, quality: payload.quality, ratio: payload.ratio, duration: payload.duration, storyDurationMinutes: payload.storyDurationMinutes, createdAt: new Date().toLocaleString() };
    saveCreation(item);
    setResult('Video returned by the engine', 'A real video response was received. Open it below to review the output.', '✓');
    const existing = $('generatedVideoLink');
    if (existing) existing.remove();
    const link = document.createElement('a');
    link.id = 'generatedVideoLink'; link.href = videoUrl; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.textContent = isBlob ? 'Open / download generated video ↗' : 'Open generated video ↗';
    link.style.cssText = 'display:inline-block;margin-top:12px;color:#5b55c8;font-size:12px;word-break:break-all';
    resultbox.appendChild(link);
    const canvas = $('canvas');
    const oldVideo = $('generatedVideoPreview');
    if (oldVideo) oldVideo.remove();
    const video = document.createElement('video');
    video.id = 'generatedVideoPreview'; video.controls = true; video.playsInline = true; video.src = videoUrl;
    video.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#101828;z-index:3';
    canvas.appendChild(video);
    const playmark = document.querySelector('.playmark');
    const canvastext = document.querySelector('.canvastext');
    if (playmark) playmark.style.display = 'none';
    if (canvastext) canvastext.style.display = 'none';
  }

  generateBtn.addEventListener('click', async () => {
    if (busy) return;
    const prompt = promptEl.value.trim();
    if (!prompt) { promptEl.focus(); setResult('Describe your scene first', 'Enter a prompt before requesting video generation.', '!'); return; }
    const settings = readJson(SETTINGS_KEY, {});
    if (!settings.apiUrl) {
      setResult('AI video engine not connected', 'Open Generation settings and add your backend API URL. This app will not create a fake video.', '!');
      settingsModal.classList.add('show');
      return;
    }
    const payload = {
      prompt,
      image: referenceDataUrl,
      imageName: referenceName || null,
      ratio: $('ratio').value,
      duration: Number($('duration').value),
      storyDurationMinutes: Number($('storyDuration').value),
      quality: $('quality').value
    };
    setBusy(true);
    setResult('Sending request to your video engine', 'Waiting for a response from the configured server…', '↗');
    try {
      const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json, video/mp4, application/octet-stream' };
      if (settings.apiToken) headers.Authorization = `Bearer ${settings.apiToken}`;
      const response = await fetch(settings.apiUrl, { method: 'POST', headers, body: JSON.stringify(payload) });
      if (!response.ok) {
        const errorData = await parseResponse(response);
        throw new Error(errorData.error || errorData.message || errorData.detail || `Server returned HTTP ${response.status}`);
      }
      const contentType = (response.headers.get('content-type') || '').toLowerCase();
      if (contentType.startsWith('video/') || contentType.includes('application/octet-stream')) {
        renderVideoResult(URL.createObjectURL(await response.blob()), prompt, payload, true);
        return;
      }
      let data = await parseResponse(response);
      const videoUrl = findVideoUrl(data);
      if (videoUrl) {
        const resolvedUrl = new URL(videoUrl, settings.apiUrl).href;
        if (!['http:', 'https:'].includes(new URL(resolvedUrl).protocol)) throw new Error('The engine returned an unsupported video URL.');
        renderVideoResult(resolvedUrl, prompt, payload, false);
      } else if (data.jobId || data.job_id) {
        const jobId = data.jobId || data.job_id;
        setResult('Generation job accepted', `Job ID: ${jobId}. No finished video URL was returned yet. This app has not verified completion; your backend must expose a status/result route or return a final videoUrl.`, '…');
      } else {
        setResult('Engine response received, no video found', 'The server did not return a video URL, video file, or usable queue result. Check the API response format.', '!');
      }
    } catch (error) {
      setResult('Video generation request failed', `${error.message || 'Unknown connection error'}. Check the API URL, server availability, CORS and backend logs.`, '!');
    } finally { setBusy(false); }
  });

  loadSettings();
  $('count').textContent = `${promptEl.value.length.toLocaleString()} characters · no app limit`;
})();
