# Project Structure — Habib Lab's AI Muslim Female TTS

## Directory Layout
```
Ai audio Advanced/
├── app.py                    ← Root Flask server (primary, with inline tag support)
├── requirements.txt          ← Root Python deps (flask, kokoro-onnx, soundfile, numpy)
├── download_models.py        ← Script to download kokoro-v0_19.onnx + voices.bin
├── kokoro-v0_19.onnx         ← Kokoro TTS ONNX model file (binary, ~300MB)
├── voices.bin                ← Voice embeddings binary
├── debug.log                 ← Runtime debug output
├── README.md                 ← Project documentation
│
├── templates/
│   └── index.html            ← Jinja2 template for Flask UI (glassmorphism design)
│
├── static/
│   ├── script.js             ← Frontend JS for Flask app (fetch API, audio player)
│   └── style.css             ← Islamic dark glassmorphism CSS
│
├── voice/                    ← Generated WAV files (auto-created, gitignore candidate)
│   └── *.wav                 ← Named: {voice}_{emotion}_{uuid6}.wav
│
├── backend/                  ← React/SPA backend (Flask, mirrors root app.py)
│   ├── app.py                ← Backend Flask server for React frontend
│   ├── requirements.txt      ← Backend-specific deps
│   └── voice/                ← Backend WAV output directory
│
└── frontend/                 ← React + Vite SPA frontend
    ├── src/
    │   ├── App.jsx            ← Root React component, state management
    │   ├── main.jsx           ← React entry point
    │   ├── index.css          ← Global styles
    │   └── components/
    │       ├── Header.jsx         ← App header with branding
    │       ├── VoiceSidebar.jsx   ← Voice + emotion selector panel
    │       ├── ScriptEditor.jsx   ← Text input with tag insertion
    │       ├── TagButtons.jsx     ← Inline emotion tag buttons
    │       ├── AudioPlayer.jsx    ← Audio playback component
    │       └── GenerationHistory.jsx ← History of generated audio
    ├── index.html             ← Vite HTML entry
    ├── vite.config.js         ← Vite config (proxy to Flask backend)
    ├── package.json           ← Node deps (React, Vite)
    └── script.js / style.css  ← Legacy static assets (unused in React build)
```

## Core Components & Relationships

### Flask App (root `app.py`)
- Initializes `Kokoro` singleton at startup from `.onnx` + `.bin` files
- `VOICES` dict maps display names → Kokoro voice IDs
- `EMOTION_SPEEDS` dict maps emotion names → speed multipliers
- `TAG_MAP` dict maps `[tag]` strings → `(emotion, speed, prefix_text)` tuples
- `parse_emotion_tags(text)` → splits text into segments by tag boundaries
- `generate_speech_segments(segments, voice_id, style)` → concatenates numpy audio arrays
- Routes: `GET /`, `POST /generate`, `GET /audio`, `POST /preview_tags`

### React Frontend (`frontend/src/`)
- `App.jsx` holds all state: selected voice, emotion, text, generation history
- `VoiceSidebar` → voice/emotion selection → lifted state to App
- `ScriptEditor` + `TagButtons` → text input with tag insertion
- `AudioPlayer` → plays returned audio URL from backend
- `GenerationHistory` → displays past generations with replay

## Architectural Patterns
- **Singleton TTS engine**: Kokoro loaded once at module level, shared across requests
- **Segment-based generation**: Text split at tag boundaries, audio arrays concatenated with `np.concatenate`
- **Speed-as-emotion**: Emotion expressed purely through TTS speed multiplier
- **UUID filename collision avoidance**: `{voice}_{emotion}_{uuid4().hex[:6]}.wav`
- **No-cache headers**: Applied globally via `@app.after_request` for dev hot-reload
- **Dual architecture**: Same backend logic in both root `app.py` and `backend/app.py`
