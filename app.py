import re
import os
import sys
import uuid
import traceback
import numpy as np
import soundfile as sf
from flask import Flask, render_template, request, send_file, jsonify, make_response
from kokoro_onnx import Kokoro

# Force UTF-8 output on Windows console
sys.stdout.reconfigure(encoding="utf-8")

app = Flask(__name__)

# ─── NO-CACHE (dev) ───
@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ─── CONFIG ───
VOICES = {
    "Maira":  "af",
    "Hania":  "af_bella",
    "Saniya": "af_nicole",
    "Fatma":  "af_sarah",
    "Ayesha": "af_sky",
}

EMOTION_SPEEDS = {
    "neutral": 1.0,
    "happy":   1.05,
    "sad":     0.75,
    "angry":   1.15,
    "excited": 1.2,
    "calm":    0.85,
    "whisper": 0.7,
    "loving":  0.9,
}

# ─── TAG PARSER ───
TAG_MAP = {
    '[sad]':           ('sad',     0.75, ''),
    '[angry]':         ('angry',   1.15, ''),
    '[happy]':         ('happy',   1.05, ''),
    '[excited]':       ('excited', 1.2,  ''),
    '[calm]':          ('calm',    0.85, ''),
    '[whisper]':       ('whisper', 0.7,  ''),
    '[loving]':        ('loving',  0.9,  ''),
    '[neutral]':       ('neutral', 1.0,  ''),
    '[laughs]':        ('happy',   1.1,  'Ha ha ha! '),
    '[chuckles]':      ('happy',   1.05, 'He he! '),
    '[sighs]':         ('sad',     0.8,  '*sigh* '),
    '[gasps]':         ('excited', 1.3,  'Oh! '),
    '[clears throat]': ('neutral', 1.0,  'Ahem. '),
    '[coughs]':        ('neutral', 0.9,  '*cough* '),
    '[shouts]':        ('angry',   1.2,  ''),
    '[whispers]':      ('whisper', 0.65, ''),
    '[sings]':         ('happy',   1.1,  ''),
    '[cries]':         ('sad',     0.7,  ''),
    '[yawns]':         ('calm',    0.8,  ''),
    '[screams]':       ('angry',   1.3,  ''),
}

TAG_PATTERN = re.compile(r'(\[[^\]]+\])')

os.makedirs("voice", exist_ok=True)

# ─── INIT KOKORO-ONNX ───
print("Loading Kokoro TTS (ONNX)...")
kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
print("Kokoro ready!")


# ─── VOICE PRE-CHECK ───
def check_voices():
    """Verify all voice IDs are available in voices.bin."""
    print("Checking voice files...")
    for name, vid in VOICES.items():
        try:
            kokoro.create("hi", voice=vid, speed=1.0, lang="en-us")
            print(f"  ✅ {name} ({vid}) ready")
        except Exception as e:
            print(f"  ⚠️ {name} ({vid}): {e}")
    print("Voice check complete!")


def parse_emotion_tags(text):
    """Parse inline emotion tags like [sad], [laughs], [whispers].
    Returns list of segment dicts with text, emotion, speed."""
    parts = TAG_PATTERN.split(text)
    segments = []
    current_emotion = 'neutral'
    current_speed = 1.0

    for part in parts:
        part = part.strip()
        if not part:
            continue
        tag_key = part.lower()
        if tag_key in TAG_MAP:
            current_emotion, current_speed, _ = TAG_MAP[tag_key]
        else:
            segments.append({
                'text': part,
                'emotion': current_emotion,
                'speed': current_speed
            })

    if not segments:
        segments = [{'text': text, 'emotion': 'neutral', 'speed': 1.0}]

    return segments


def generate_speech_segments(segments, voice_id, style):
    """Generate audio for each segment and concatenate."""
    all_audio = []
    sample_rate = 24000

    for seg in segments:
        seg_text = seg['text']
        seg_speed = seg['speed'] * (0.8 + style * 0.4)

        if not seg_text.strip():
            continue

        try:
            samples, sr = kokoro.create(
                seg_text, voice=voice_id, speed=seg_speed, lang="en-us"
            )
            sample_rate = sr
            all_audio.append(samples)
        except Exception as e:
            print(f"Warning: segment failed: {e}")
            continue

    if not all_audio:
        return np.array([]), sample_rate

    combined = np.concatenate(all_audio) if len(all_audio) > 1 else all_audio[0]
    return combined, sample_rate


def extract_tags_info(text):
    """Extract all tags from text for UI display."""
    tags = TAG_PATTERN.findall(text)
    return [t.lower() for t in tags if t.lower() in TAG_MAP]


# ─── ROUTES ───
@app.route("/")
def index():
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("text", "").strip()
    voice_name = request.form.get("voice", "Maira")
    base_emotion = request.form.get("emotion", "neutral")
    style = float(request.form.get("style", "0.3"))

    if not text:
        return jsonify({"error": "Please enter your script"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Text too long (max 5000 characters)"}), 400

    # Validate inputs — fall back to safe defaults
    if voice_name not in VOICES:
        voice_name = "Maira"
    if base_emotion not in EMOTION_SPEEDS:
        base_emotion = "neutral"

    voice_id = VOICES[voice_name]
    has_tags = bool(TAG_PATTERN.search(text))

    try:
        if has_tags:
            segments = parse_emotion_tags(text)
            combined, sample_rate = generate_speech_segments(segments, voice_id, style)
            detected_tags = extract_tags_info(text)
        else:
            speed = EMOTION_SPEEDS[base_emotion] * (0.8 + style * 0.4)
            samples, sample_rate = kokoro.create(
                text, voice=voice_id, speed=speed, lang="en-us"
            )
            combined = samples
            detected_tags = []

        if len(combined) == 0:
            return jsonify({"error": "No audio generated"}), 500

        # Build safe filename — no path components in the name
        filename = f"{voice_name.lower()}_{base_emotion}_{uuid.uuid4().hex[:6]}.wav"
        filepath = os.path.join("voice", filename)
        sf.write(filepath, combined, sample_rate)
        duration = len(combined) / sample_rate

        return jsonify({
            "success": True,
            "audio_url": f"/audio?file={filename}",
            "duration": f"{duration:.1f}s",
            "voice": voice_name,
            "emotion": base_emotion,
            "has_inline_tags": has_tags,
            "detected_tags": detected_tags,
            "segment_count": len(parse_emotion_tags(text)) if has_tags else 1
        })

    except Exception:
        print("GENERATION ERROR:", traceback.format_exc())
        return jsonify({"error": "Generation failed. Check server logs."}), 500


@app.route("/audio")
def serve_audio():
    filename = request.args.get("file", "")
    # Security: strip path separators to prevent directory traversal
    filename = os.path.basename(filename)
    if not filename:
        return jsonify({"error": "No file specified"}), 400
    filepath = os.path.join("voice", filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="audio/wav")
    return jsonify({"error": "File not found"}), 404


@app.route("/preview_tags", methods=["POST"])
def preview_tags():
    """Preview how tags will be parsed without generating audio."""
    text = request.form.get("text", "")
    segments = parse_emotion_tags(text)
    tags = extract_tags_info(text)

    return jsonify({
        "has_tags": bool(tags),
        "detected_tags": tags,
        "segments": [
            {"text": s["text"], "emotion": s["emotion"], "speed": s["speed"]}
            for s in segments
        ]
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  VoiceForge AI — Powered by Habib Brains")
    print("  Kokoro-ONNX Backend + Inline Emotion Tags")
    print("  Server URL: http://localhost:5000")
    print("=" * 50)
    check_voices()
    app.run(debug=True, host="0.0.0.0", port=5000)
