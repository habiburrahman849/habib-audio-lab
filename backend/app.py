# -*- coding: utf-8 -*-
import re
import os
import sys
import uuid
import traceback
import numpy as np
import soundfile as sf
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from kokoro_onnx import Kokoro

sys.stdout.reconfigure(encoding="utf-8")

app = Flask(__name__)
CORS(app)

# --- GLOBAL JSON ERROR HANDLERS ---
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

# --- CONFIG ---
VOICES = {
    "Maira":  "af",
    "Hania":  "af_nicole",
    "Saniya": "af_nicole",
    "Fatma":  "af_sarah",
    "Ayesha": "af_sky",
    "Maria":  "af",
    "Sara":   "af_bella",
    "salma":  "af_sarah",
    "Aneela": "af_sky",
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

# --- TAG MAP ---
TAG_MAP = {
    '[happy]':         ('happy',   1.05, ''),
    '[sad]':           ('sad',     0.75, ''),
    '[angry]':         ('angry',   1.15, ''),
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
    '[pause]':         ('neutral', 0.8,  ''),
}

TAG_PATTERN = re.compile(r'(\[[^\]]+\])')

# --- PATHS (always relative to this file, never CWD) ---
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR   = os.path.join(BASE_DIR, "voice")
MODEL_PATH  = os.path.join(BASE_DIR, "..", "kokoro-v0_19.onnx")
VOICES_PATH = os.path.join(BASE_DIR, "..", "voices.bin")
os.makedirs(VOICE_DIR, exist_ok=True)

# --- INIT KOKORO ---
kokoro = None
try:
    print("Loading Kokoro TTS (ONNX)...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    print("Kokoro ready!")
except Exception as e:
    print(f"ERROR: Kokoro failed to load: {e}")
    print("Server will start but /api/generate will return an error.")


def preload_voices():
    """Warm up all voices on startup so generation does not fail mid-request."""
    if kokoro is None:
        return
    seen = set()
    for name, vid in VOICES.items():
        if vid in seen:
            continue
        seen.add(vid)
        try:
            kokoro.create("hi", voice=vid, speed=1.0, lang="en-us")
            print(f"Preloaded: {vid} ({name})")
        except Exception as e:
            print(f"Could not preload {vid} ({name}): {e}")
            print("   Internet may be needed for first download")


preload_voices()


def parse_emotion_tags(text):
    """Parse inline emotion tags. Always returns valid segments."""
    parts = TAG_PATTERN.split(text)
    segments = []
    current_speed = 1.0
    pending_prefix = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        tag_key = part.lower()
        if tag_key in TAG_MAP:
            current_speed = TAG_MAP[tag_key][1]
            prefix = TAG_MAP[tag_key][2]
            if prefix:
                if pending_prefix:
                    pending_prefix += " " + prefix
                else:
                    pending_prefix = prefix
        else:
            if pending_prefix:
                part = pending_prefix + part
                pending_prefix = ""
            segments.append({
                'text': part,
                'speed': current_speed
            })

    if pending_prefix:
        segments.append({
            'text': pending_prefix,
            'speed': current_speed
        })

    if not segments:
        segments = [{'text': text, 'speed': 1.0}]

    return segments


def extract_tags_info(text):
    """Extract all valid tags from text for UI display."""
    tags = TAG_PATTERN.findall(text)
    return [t.lower() for t in tags if t.lower() in TAG_MAP]


# --- ROUTES ---
@app.route("/api/voices")
def get_voices():
    return jsonify({
        "voices": [
            {"name": "Maria",  "id": "af",        "desc": "Warm & Expressive"},
            {"name": "Sara",   "id": "af_bella",  "desc": "Clear & Natural"},
            {"name": "Hania",  "id": "af_nicole", "desc": "Authoritative"},
            {"name": "salma",  "id": "af_sarah",  "desc": "Calm & Peaceful"},
            {"name": "Aneela", "id": "af_sky",    "desc": "Casual & Friendly"},
        ]
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        text       = str(data.get("text", "")).strip()
        voice_name = str(data.get("voice", "Maria"))
        style      = float(data.get("style", 0.3))

        print(f"Received: voice={voice_name}, text_len={len(text)}", flush=True)

        if not text:
            return jsonify({"error": "No text provided"}), 400
        if len(text) > 5000:
            return jsonify({"error": "Text too long (max 5000 characters)"}), 400
        if kokoro is None:
            return jsonify({"error": "TTS model not loaded. Run: python download_models.py"}), 503

        if voice_name not in VOICES:
            voice_name = "Maria"

        voice_id = VOICES[voice_name]
        print(f"Using voice_id={voice_id}", flush=True)


        detected_tags = extract_tags_info(text)
        has_tags      = bool(detected_tags)

        segments = parse_emotion_tags(text)
        print(f"Segments: {segments}", flush=True)

        if not segments:
            return jsonify({"error": "No valid text segments"}), 400

        all_audio   = []
        sample_rate = 24000

        for seg in segments:
            seg_text = seg['text']
            if not seg_text.strip():
                continue
            final_speed = seg['speed'] * (0.8 + style * 0.4)
            preview = seg_text[:50] + ('...' if len(seg_text) > 50 else '')
            print(f"Generating: '{preview}' speed={final_speed}", flush=True)
            try:
                samples, sr = kokoro.create(
                    seg_text, voice=voice_id, speed=final_speed, lang="en-us"
                )
                sample_rate = sr
                all_audio.append(samples)
                print(f"  Got audio chunk: {len(samples)} samples", flush=True)
            except Exception as e:
                print(f"Warning: segment failed: {e}", flush=True)
                continue

        if not all_audio:
            return jsonify({"error": "No audio generated"}), 500

        combined = np.concatenate(all_audio) if len(all_audio) > 1 else all_audio[0]

        if len(combined) == 0:
            return jsonify({"error": "No audio generated"}), 500

        filename = f"{uuid.uuid4().hex[:8]}.wav"
        filepath = os.path.join(VOICE_DIR, filename)
        sf.write(filepath, combined, sample_rate)
        print(f"Saved: {filepath}", flush=True)
        duration = len(combined) / sample_rate

        return jsonify({
            "success":         True,
            "audio_url":       f"/api/audio/{filename}",
            "duration":        f"{duration:.1f}s",
            "voice":           voice_name,
            "has_inline_tags": has_tags,
            "detected_tags":   detected_tags,
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print("=" * 50, flush=True)
        print("GENERATION ERROR:", flush=True)
        print(error_trace, flush=True)
        print("=" * 50, flush=True)
        return jsonify({
            "error": f"Generation failed: {str(e)}",
            "traceback": error_trace
        }), 500


@app.route("/api/audio/<filename>")
def serve_audio(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(VOICE_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="audio/wav")
    return jsonify({"error": "Audio file not found"}), 404


@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "kokoro": "loaded" if kokoro else "not loaded"
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  Habib Lab's AI - Backend Server")
    print("  Kokoro-ONNX + Inline Emotion Tags")
    print("  Server: http://localhost:5000")
    print("  Health: http://localhost:5000/api/health")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000)
