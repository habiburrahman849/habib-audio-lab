# 🕌 Habib Lab's — AI Muslim Female TTS
**Powered by Habib Brains** · Kokoro TTS Engine

---

## ✨ Features

- **6 Muslim Female Voices** — Maira, Hania, Saniya, Fatma, Ayesha, Zara
- **8 Emotional Modes** — Neutral, Happy, Sad, Angry, Excited, Calm, Whisper, Loving
- **Kokoro TTS** — State-of-the-art neural TTS (American Female voices)
- **24kHz WAV output** — High quality audio
- **Voice Comparison** — Compare all 6 voices or all 8 emotions side by side
- **Premium Islamic UI** — Dark glassmorphism design with Arabic bismillah

---

## 🗂️ Project Structure

```
Ai Audio Advanced/
├── app.py                 ← Flask TTS server (Kokoro integration)
├── requirements.txt       ← Python dependencies
├── templates/
│   └── index.html         ← Premium Islamic-themed UI
├── voice/                 ← Generated WAV files (auto-created)
└── venv/                  ← Virtual environment (create manually)
```

---

## 🎙️ Voice Mapping

| Muslim Name | Kokoro Voice ID | Character              |
|-------------|-----------------|------------------------|
| **Maira**   | `af_heart`      | Warm & Expressive      |
| **Hania**   | `af_bella`      | Clear & Natural        |
| **Saniya**  | `af_nicole`     | Soft & Gentle          |
| **Fatma**   | `af_sarah`      | Professional           |
| **Ayesha**  | `af_sky`        | Bright & Youthful      |
| **Zara**    | `af_alloy`      | Modern & Balanced      |

---

## 🚀 Setup & Run

### 1. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

> **Windows users**: Also install eSpeak-NG from:
> https://github.com/espeak-ng/espeak-ng/releases

### 3. Run the server
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

### Frontend (Next.js studio)

**PowerShell** — use semicolon, not `&&`:
```powershell
cd frontend/habib-audio-studio; npx next dev
```

**CMD** or batch file:
```cmd
start_frontend.bat
```

Then open: `http://localhost:3000/studio`

---

## ⌨️ Keyboard Shortcut

- `Ctrl + Enter` — Generate speech instantly

---

## 🎭 Emotion Speed Table

| Emotion  | Speed  | Effect              |
|----------|--------|---------------------|
| Whisper  | 0.70×  | Softest, slowest    |
| Sad      | 0.75×  | Slow & melancholy   |
| Calm     | 0.85×  | Peaceful            |
| Loving   | 0.90×  | Warm & gentle       |
| Neutral  | 1.00×  | Normal              |
| Happy    | 1.05×  | Slightly cheerful   |
| Angry    | 1.15×  | Intense & fast      |
| Excited  | 1.20×  | Most energetic      |

---

*Habib Lab's · Powered by Habib Brains*
