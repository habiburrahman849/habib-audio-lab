# Development Guidelines — Habib Lab's AI Muslim Female TTS

## Code Quality Standards

### Python (Flask Backend)
- Section headers use ASCII box-drawing comments: `# ─── SECTION NAME ───`
- Module-level constants in UPPER_SNAKE_CASE: `VOICES`, `EMOTION_SPEEDS`, `TAG_MAP`, `TAG_PATTERN`
- Docstrings on all utility functions (single-line or two-line format):
  ```python
  def parse_emotion_tags(text):
      """Parse inline emotion tags like [sad], [laughs], [whispers].
      Returns list of segment dicts with text, emotion, speed."""
  ```
- Startup banner always printed with `"=" * 50` borders
- `sys.stdout.reconfigure(encoding="utf-8")` at top of every Python entry point (Windows fix)
- `os.makedirs("voice", exist_ok=True)` called at module level, not inside routes

### JavaScript (Vanilla)
- Section headers use `// ─── SECTION NAME ───` or `// ===== SECTION NAME =====`
- Global state declared at top with `let` (mutable) or `const` (DOM refs, config objects)
- DOM element references cached at module level, not inside functions
- Template literals used for all HTML generation in JS

### React (JSX)
- All state in root `App.jsx` via `useState`, passed down as props
- Inline styles used throughout (no CSS modules or Tailwind)
- `useEffect` for side effects (API calls on mount, text change watchers)
- `const API_URL = '/api'` constant at top of App.jsx for all fetch calls

---

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python functions | `snake_case` | `parse_emotion_tags`, `generate_speech_segments` |
| Python constants | `UPPER_SNAKE_CASE` | `VOICES`, `TAG_MAP`, `EMOTION_SPEEDS` |
| JS functions | `camelCase` | `renderVoiceList`, `insertTag`, `handleGenerate` |
| JS state vars | `camelCase` | `selectedVoice`, `historyItems`, `currentAudioUrl` |
| React components | `PascalCase` | `VoiceSidebar`, `AudioPlayer`, `ScriptEditor` |
| React props | `camelCase` | `onSelect`, `onInsert`, `onPlay` |
| WAV filenames | `{voice}_{emotion}_{uuid6}.wav` | `maira_neutral_7fd9cc.wav` |
| CSS classes | `kebab-case` | `voice-pill`, `history-row`, `detected-tag` |

---

## API Patterns

### Flask Route (root app.py — form data)
```python
@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text", "").strip()
    voice_name = request.form.get("voice", "Maira")
    style = float(request.form.get("style", "0.3"))
    # Always validate: empty text → 400, len > 5000 → 400
    # Return: jsonify({"success": True, "audio_url": ..., "duration": ..., "voice": ..., ...})
    # Error: jsonify({"error": "message"}), 500
```

### Flask Route (backend/app.py — JSON body)
```python
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    text = data.get("text", "").strip()
    # Routes prefixed with /api/ for React proxy
    # Returns absolute URL: f"http://localhost:5000/api/audio/{filename}"
```

### React fetch call
```javascript
const res = await fetch(`${API_URL}/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text, voice: selectedVoice, style: 0.3 }),
})
const data = await res.json()
if (data.success) { /* handle */ } else { alert('Error: ' + data.error) }
```

### Vanilla JS fetch call (FormData)
```javascript
const formData = new FormData()
formData.append('text', text)
formData.append('voice', selectedVoice)
formData.append('style', document.getElementById('style').value / 100)
const res = await fetch('/generate', { method: 'POST', body: formData })
```

---

## Architectural Patterns

### Tag System (used in all 3 backend versions)
- `TAG_MAP` dict: `'[tag]'` → `(emotion_str, speed_float, prefix_text_str)`
- `TAG_PATTERN = re.compile(r'(\[[^\]]+\])')` — consistent regex across all files
- `parse_emotion_tags(text)` splits on tag boundaries, returns segments
- `extract_tags_info(text)` returns list of valid tag strings for UI display
- Tags are stateful: last seen tag applies to all following text until next tag

### Audio Generation Pipeline
```python
# Single emotion (no tags):
speed = EMOTION_SPEEDS[emotion] * (0.8 + style * 0.4)
samples, sr = kokoro.create(text, voice=voice_id, speed=speed, lang="en-us")

# Multi-segment (with tags):
segments = parse_emotion_tags(text)
all_audio = [kokoro.create(seg, voice=voice_id, speed=spd, lang="en-us")[0] for seg, spd in segments]
combined = np.concatenate(all_audio) if len(all_audio) > 1 else all_audio[0]
sf.write(filename, combined, sample_rate)
```

### Error Handling Pattern
- Per-segment try/except with `continue` (never fail entire generation for one bad segment)
- Route-level try/except with `traceback.format_exc()` printed to console
- Frontend: `try/catch` on fetch, `alert()` for user-facing errors
- Empty audio guard: `if len(combined) == 0: return jsonify({"error": "No audio generated"}), 500`

### History Pattern (JS)
```javascript
let historyItems = []  // module-level array
historyItems.unshift({ voice, emotion, duration, time: new Date().toLocaleTimeString(), audioUrl })
renderHistory()  // always re-render full list after mutation
```

### Download Pattern (JS)
```javascript
// Blob download (preferred in newer versions):
const blob = await response.blob()
const link = document.createElement('a')
link.href = URL.createObjectURL(blob)
link.download = `habib-lab-voiceover-${Date.now()}.wav`
link.click()
```

---

## Configuration Conventions

### Voice Mapping (consistent across all files)
```python
VOICES = {
    "Maira":  "af_heart",   # or "af" in older versions
    "Hania":  "af_bella",
    "Saniya": "af_nicole",
    "Fatma":  "af_sarah",
    "Ayesha": "af_sky",
}
```

### Slider → Backend Conversion
- UI sliders are 0–100 integers
- Backend expects 0.0–1.0 floats
- Conversion: `document.getElementById('stability').value / 100`

### Speed Formula
- Always: `final_speed = base_speed * (0.8 + style * 0.4)`
- Style range 0.0–1.0 maps to speed multiplier 0.8×–1.2×

---

## File Organization Rules
- New voice WAV files → `voice/` directory (root or `backend/voice/`)
- Model files (`.onnx`, `.bin`) → project root, referenced by relative path
- Backend for React uses `os.path.join(os.path.dirname(__file__), "..", "kokoro-v0_19.onnx")` to find root models
- No-cache headers applied globally via `@app.after_request` decorator (dev mode)
- `flask_cors.CORS(app)` only in `backend/app.py` (React backend), not root Flask app

---

## Download Script Pattern (`download_models.py`)
- `MODELS` dict: `filename → [primary_url, fallback_url]`
- Skip if file exists: check `os.path.exists(filename)` first
- Chunked download: 256KB chunks with progress bar using `\r` overwrite
- Retry logic: `MAX_RETRIES = 5` with exponential backoff `time.sleep(2 * (retry + 1))`
- Clean up partial file on failure: `os.remove(filename)` in except block
