# Technology Stack — Habib Lab's AI Muslim Female TTS

## Backend (Python)
| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.x | Runtime |
| Flask | >=3.0 | HTTP server, routing, template rendering |
| kokoro-onnx | >=0.4 | Neural TTS engine (ONNX runtime) |
| soundfile | >=0.12 | WAV file writing |
| numpy | >=2.0 | Audio array manipulation & concatenation |

### Model Files
- `kokoro-v0_19.onnx` — Kokoro TTS ONNX model (~300MB, downloaded via `download_models.py`)
- `voices.bin` — Voice embedding binary (downloaded alongside model)

## Frontend (React SPA)
| Component | Version | Purpose |
|-----------|---------|---------|
| React | ^18.3.0 | UI framework |
| React DOM | ^18.3.0 | DOM rendering |
| wavesurfer.js | ^7.8.0 | Audio waveform visualization |
| Vite | ^5.4.0 | Build tool & dev server |
| @vitejs/plugin-react | ^4.3.0 | React JSX transform |

## Development Commands

### Flask App (root — primary)
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download TTS models (first run)
python download_models.py

# Run server
python app.py
# → http://localhost:5000
```

### React Frontend
```bash
cd frontend
npm install
npm run dev       # → http://localhost:5173 (proxies /api to :5000)
npm run build     # Production build
npm run preview   # Preview production build
```

### Backend (for React frontend)
```bash
cd backend
pip install -r requirements.txt
python app.py     # → http://localhost:5000
```

## Key Configuration
- **Vite proxy**: `/api` → `http://localhost:5000` (configured in `vite.config.js`)
- **Audio output**: 24kHz WAV, saved to `voice/` directory
- **Text limit**: 5000 characters max per request
- **Language**: `en-us` (American English, hardcoded in `kokoro.create()`)
- **Windows**: Requires eSpeak-NG from https://github.com/espeak-ng/espeak-ng/releases
- **UTF-8**: `sys.stdout.reconfigure(encoding="utf-8")` applied at startup for Windows console

## Audio Pipeline
```
Text Input → Tag Parser → Segments → kokoro.create() × N → np.concatenate() → sf.write() → WAV file
```
Speed formula: `final_speed = emotion_speed * (0.8 + style_slider * 0.4)`
