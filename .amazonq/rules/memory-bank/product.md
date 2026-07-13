# Product Overview — Habib Lab's AI Muslim Female TTS

## Purpose
VoiceForge AI is a browser-based Text-to-Speech application powered by the Kokoro-ONNX neural TTS engine. It provides high-quality, emotionally expressive speech synthesis using Muslim female voice personas, built for Islamic content creators, educators, and developers.

## Key Features
- **5–6 Muslim Female Voices**: Maira, Hania, Saniya, Fatma, Ayesha (+ Zara in README)
  - Mapped to Kokoro voice IDs: af_heart, af_bella, af_nicole, af_sarah, af_sky
- **8 Emotional Modes**: neutral, happy, sad, angry, excited, calm, whisper, loving
  - Controlled via speed multipliers (0.70× whisper → 1.20× excited)
- **Inline Emotion Tags**: `[sad]`, `[laughs]`, `[whispers]`, `[sighs]`, etc. embedded in text
  - 22 supported tags covering emotions, non-verbal reactions, and delivery styles
- **Style Exaggeration Slider**: Fine-tunes speed via formula `speed * (0.8 + style * 0.4)`
- **24kHz WAV Output**: High-quality audio saved to `voice/` directory
- **Tag Preview**: `/preview_tags` endpoint parses tags without generating audio
- **Premium Islamic UI**: Dark glassmorphism design with Arabic bismillah (Flask + React versions)

## Target Users
- Islamic content creators needing expressive Arabic/English voiceovers
- Developers building Muslim-focused audio applications
- Educators producing Islamic learning materials

## Use Cases
- Quran/hadith narration with emotional delivery
- Islamic podcast and video voiceovers
- Accessibility tools for Muslim communities
- TTS prototyping with named voice personas

## Dual Architecture
The project has two parallel implementations:
1. **Flask + Jinja2** (root `app.py` + `templates/index.html`) — production server
2. **React + Vite frontend** (`frontend/`) + **Flask backend** (`backend/app.py`) — modern SPA architecture
