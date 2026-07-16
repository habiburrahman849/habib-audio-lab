# -*- coding: utf-8 -*-
import re
import os
import sys
import uuid
import traceback
import random
import time
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
    '[happy]':         ('happy',   1.0, ''),
    '[sad]':           ('sad',     1.0, ''),
    '[angry]':         ('angry',   1.0, ''),
    '[excited]':       ('excited', 1.0,  ''),
    '[calm]':          ('calm',    1.0,  ''),
    '[whisper]':       ('whisper', 1.0,  ''),
    '[loving]':        ('loving',  1.0,  ''),
    '[neutral]':       ('neutral', 1.0,  ''),
    '[laughs]':        ('laughs',  1.0,  ''),
    '[chuckles]':      ('laughs',  1.0,  ''),
    '[sighs]':         ('sighs',   1.0,  ''),
    '[gasps]':         ('gasps',   1.0,  ''),
    '[clears throat]': ('neutral', 1.0,  ''),
    '[coughs]':        ('neutral', 1.0,  ''),
    '[shouts]':        ('shouts',  1.0,  ''),
    '[whispers]':      ('whisper', 1.0,  ''),
    '[sings]':         ('sings',   1.0,  ''),
    '[cries]':         ('sad',     1.0,  ''),
    '[yawns]':         ('calm',    1.0,  ''),
    '[screams]':       ('angry',   1.0,  ''),
    '[pause]':         ('neutral', 1.0,  ''),
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
GENERATION_PROGRESS = {}
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


def get_blended_style(base_voice_id, emotion):
    if kokoro is None:
        return base_voice_id
    try:
        base_style = kokoro.get_voice_style(base_voice_id)
        
        # Determine gender based on prefix
        is_male = base_voice_id.startswith('am_') or base_voice_id.startswith('bm_')
        
        target_voice = None
        blend_weight = 0.0
        
        if emotion in ['happy', 'excited']:
            target_voice = 'am_michael' if is_male else 'af_sky'
            blend_weight = 0.45
        elif emotion in ['sad', 'whisper', 'calm']:
            target_voice = 'bm_lewis' if is_male else 'af_sarah'
            blend_weight = 0.55
        elif emotion in ['angry', 'screams', 'shouts']:
            target_voice = 'am_adam' if is_male else 'af_nicole'
            blend_weight = 0.45
            
        if target_voice and target_voice != base_voice_id:
            target_style = kokoro.get_voice_style(target_voice)
            # Blend style vectors (numpy array interpolation)
            blended_style = (1.0 - blend_weight) * base_style + blend_weight * target_style
            return blended_style
            
        return base_style
    except Exception as e:
        print(f"Error blending styles: {e}", flush=True)
        return base_voice_id


# New slang-rich modifiers for authentic YouTube styles
emotion_modifiers = {
    'happy': {
        'speed': 1.15,
        'prefixes': [
            'Yo! ', 'Hey hey! ', 'What\'s up! ', 'Ayy! ', 
            'Let\'s gooo! ', 'Yooo! ', 'Hyped! ', 'Yasss! '
        ],
        'suffixes': [
            '! Let\'s gooo! 🔥', '! So hyped right now!', 
            '! This is fire! 🔥', '! Love it! ❤️', 
            '! Best day ever!', '! Vibes! ✨'
        ],
        'punctuation': '!',
        'slang_words': ['hyped', 'fire', 'lit', 'vibes', 'goat', 'iconic'],
    },
    'sad': {
        'speed': 0.75,
        'prefixes': [
            '*sigh* ', 'Man... ', 'Ugh... ', 'Honestly... ', 
            'Not gonna lie... ', 'Lowkey... '
        ],
        'suffixes': [
            '... it is what it is', '... rough times', 
            '... sending love 💔', '... need a hug', 
            '... why though', '... hurts different'
        ],
        'punctuation': '...',
        'slang_words': ['sus', 'oof', 'yikes', 'mood', 'big sad', 'rip'],
    },
    'angry': {
        'speed': 1.25,
        'prefixes': [
            'BRUH! ', 'ARE YOU KIDDING?! ', 'NO WAY! ', 
            'Hold up! ', 'Excuse me?! ', 'Nah nah nah! '
        ],
        'suffixes': [
            '! I\'m done! 😤', '! This is ridiculous!', 
            '! Cancel that! ❌', '! Fix it NOW!', 
            '! Unacceptable!', '! I\'m heated! 🔥'
        ],
        'punctuation': '!!',
        'slang_words': ['bruh', 'cap', 'sus', 'pressed', 'heated', 'mad'],
    },
    'excited': {
        'speed': 1.3,
        'prefixes': [
            'BROOO! ', 'OH MY GOD! ', 'NO WAY! ', 
            'YOOO! ', 'HOLD UP! ', 'WAIT WAIT WAIT! '
        ],
        'suffixes': [
            '! I\'m SHOOK! 🤯', '! This is INSANE!', 
            '! Mind = blown! 💥', '! I can\'t even!', 
            '! Best thing ever!', '! We eating good! 🍽️'
        ],
        'punctuation': '!!',
        'slang_words': ['shook', 'insane', 'bussin', 'fire', 'goated', 'slaps'],
    },
    'calm': {
        'speed': 0.8,
        'prefixes': [
            'Breathe... ', 'Chill... ', 'Relax... ', 
            'Softly... ', 'Gently... ', 'Easy now... '
        ],
        'suffixes': [
            '... peacefully...', '... take it slow...', 
            '... all good... ✨', '... no stress...', 
            '... zen mode... 🧘', '... smooth...'
        ],
        'punctuation': '...',
        'slang_words': ['chill', 'vibing', 'zen', 'lowkey', 'smooth', 'clean'],
    },
    'whisper': {
        'speed': 0.65,
        'prefixes': [
            'Psst... ', 'Between us... ', 'Secret... ', 
            'Don\'t tell anyone... ', 'Lowkey... ', 'Real talk... '
        ],
        'suffixes': [
            '... just saying...', '... you didn\'t hear this...', 
            '... on the down low... 🤫', '... trust me on this...', 
            '... real ones know...', '... keep it quiet...'
        ],
        'punctuation': '...',
        'slang_words': ['tea', 'spill', 'lowkey', 'real', 'facts', 'no cap'],
    },
    'loving': {
        'speed': 0.9,
        'prefixes': [
            'My love... ', 'Babe... ', 'Sweetheart... ', 
            'Honey... ', 'Darling... ', 'My heart... '
        ],
        'suffixes': [
            '... forever... ❤️', '... always...', 
            '... you mean everything...', '... never letting go...', 
            '... my everything... 💕', '... pure love...'
        ],
        'punctuation': '...',
        'slang_words': ['bae', 'simp', 'goals', 'ship', 'otp', 'main'],
    },
    'laughs': {
        'speed': 1.1,
        'prefixes': [
            'LMAO! ', 'DEAD! 💀 ', 'I\'m crying! ', 
            'NOOO! ', 'STOP! ', 'BROOO! '
        ],
        'suffixes': [
            '! I\'m deceased! 💀', '! Can\'t breathe!', 
            '! Comedy gold! 🏆', '! Who did this?!', 
            '! I\'m weak! 😂', '! Send help! 🚑'
        ],
        'punctuation': '!',
        'slang_words': ['lmao', 'dead', 'crying', 'weak', 'savage', 'comedy'],
    },
    'sighs': {
        'speed': 0.7,
        'prefixes': [
            '*deep sigh* ', '*exhales* ', 'Here we go... ', 
            'Again... ', 'Really... ', 'Smh... '
        ],
        'suffixes': [
            '... here we go again...', '... same old...', 
            '... tired... 😔', '... when will it end...', 
            '... exhausted...', '... no energy left...'
        ],
        'punctuation': '...',
        'slang_words': ['smh', 'bruh', 'tired', 'done', 'over it', 'mood'],
    },
    'gasps': {
        'speed': 1.2,
        'prefixes': [
            'GASP! ', 'WAIT! ', 'HOLD UP! ', 
            'NO WAY! ', 'SHUT UP! ', 'GET OUT! '
        ],
        'suffixes': [
            '! I\'m SHOOK! 😱', '! Plot twist!', 
            '! Did that just happen?!', '! I can\'t believe it!', 
            '! My jaw dropped! 📉', '! Unbelievable!'
        ],
        'punctuation': '!!',
        'slang_words': ['shook', 'plot twist', 'sus', 'wild', 'crazy', 'insane'],
    },
    'shouts': {
        'speed': 1.35,
        'prefixes': [
            'AYO! ', 'LISTEN UP! ', 'EVERYBODY! ', 
            'YO YO YO! ', 'CHECK THIS! ', 'HOLD UP! '
        ],
        'suffixes': [
            '! MAKE SOME NOISE! 📢', '! LET\'S GOOO!', 
            '! TURN IT UP! 🔊', '! WE OUT HERE!', 
            '! BIG ENERGY! ⚡', '! RUN IT BACK!'
        ],
        'punctuation': '!!!',
        'slang_words': ['ayo', 'lets go', 'run it', 'big', 'energy', 'loud'],
    },
    'sings': {
        'speed': 1.15,
        'prefixes': [
            '~ 🎵 ', '*hums* ', 'La la la~ ', 
            '♪♪♪ ', 'Melody... ', 'Sing it! '
        ],
        'suffixes': [
            ' ~ 🎶', ' ~ la la la! 🎵', 
            ' ~ hit the notes! 🎤', ' ~ harmony! ✨', 
            ' ~ vibes! 🎧', ' ~ music to my ears! 🎼'
        ],
        'punctuation': '~',
        'slang_words': ['vibes', 'bop', 'slaps', 'hit', 'fire', 'goated'],
    },
    'neutral': {
        'speed': 1.0,
        'prefixes': [''],
        'suffixes': [''],
        'punctuation': '',
        'slang_words': [],
    }
}

def emotionalize_text(text, emotion):
    """Add slang and natural expressions to make emotions obvious."""
    mod = emotion_modifiers.get(emotion, emotion_modifiers['neutral'])
    
    # If the modifier is completely empty (like neutral), do nothing
    if not mod['prefixes'] or (len(mod['prefixes']) == 1 and mod['prefixes'][0] == ''):
        return text, mod['speed']
        
    prefix = random.choice(mod['prefixes'])
    suffix = random.choice(mod['suffixes'])
    
    result = text
    
    # Add prefix if not already there
    if not result.startswith(prefix.strip()):
        result = prefix + result
    
    # Add suffix
    result = result + suffix
    
    # Apply punctuation style
    if mod['punctuation'] == '!':
        result = result.replace('.', '!').replace('?', '!')
    elif mod['punctuation'] == '...':
        result = result.replace('.', '...').replace(',', '...')
    elif mod['punctuation'] == '~':
        result = result.replace('.', '~').replace('!', '~')
    
    # Occasionally inject slang words naturally
    if mod['slang_words']:
        slang = random.choice(mod['slang_words'])
        if random.random() > 0.5 and slang not in result.lower():
            # Inject slang word at first punctuation
            for punct in ['!', '...', '~']:
                if punct in result:
                    result = result.replace(punct, f'{punct} That\'s {slang}!', 1)
                    break
    
    return result, mod['speed']


def parse_emotion_tags(text):
    """Parse inline emotion tags. Always returns valid segments."""
    parts = TAG_PATTERN.split(text)
    segments = []
    current_speed = 1.0
    current_emotion = 'neutral'
    pending_prefix = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue

        tag_key = part.lower()
        if tag_key in TAG_MAP:
            current_emotion = TAG_MAP[tag_key][0]
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
                'speed': current_speed,
                'emotion': current_emotion
            })

    if pending_prefix:
        segments.append({
            'text': pending_prefix,
            'speed': current_speed,
            'emotion': current_emotion
        })

    if not segments:
        segments = [{'text': text, 'speed': 1.0, 'emotion': 'neutral'}]

    return segments


def extract_tags_info(text):
    """Extract all valid tags from text for UI display."""
    tags = TAG_PATTERN.findall(text)
    return [t.lower() for t in tags if t.lower() in TAG_MAP]


# --- ROUTES ---
@app.route("/api/preview", methods=["POST"])
def preview():
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get("text", "")).strip()
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        segments = parse_emotion_tags(text)
        preview_segments = []
        emotionalized_parts = []
        
        for seg in segments:
            seg_text = seg['text']
            if not seg_text.strip():
                continue
            seg_emotion = seg.get('emotion', 'neutral')
            emotional_text, emotion_speed = emotionalize_text(seg_text, seg_emotion)
            emotionalized_parts.append(emotional_text)
            
            # Detect which slang words are in the emotionalized segment
            mod = emotion_modifiers.get(seg_emotion, emotion_modifiers['neutral'])
            detected_slang = [w for w in mod.get('slang_words', []) if w.lower() in emotional_text.lower()]
            
            preview_segments.append({
                "original": seg_text,
                "emotionalized": emotional_text,
                "emotion": seg_emotion,
                "speed": emotion_speed,
                "slang_used": detected_slang
            })
            
        return jsonify({
            "success": True,
            "preview": preview_segments,
            "original_text": text,
            "emotionalized_text": " ".join(emotionalized_parts),
            "segments": segments
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_remaining_time(seconds):
    seconds = int(round(seconds))
    if seconds <= 0:
        return "1 second"
    if seconds < 60:
        return f"{seconds} seconds"
    minutes = seconds // 60
    secs = seconds % 60
    if secs == 0:
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    return f"{minutes}m {secs}s"

@app.route("/api/progress/<request_id>", methods=["GET"])
def get_progress(request_id):
    progress = GENERATION_PROGRESS.get(request_id)
    if not progress:
        return jsonify({
            "status": "starting",
            "completed": 0,
            "total": 1,
            "percent": 0,
            "estimated_remaining": "Calculating...",
            "done": False,
        })
    
    elapsed = time.time() - progress.get('started_at', time.time())
    completed_chars = progress.get('completed_chars', 0)
    total_chars = progress.get('total_chars', 1)
    status = progress.get('status')
    
    if status == 'complete':
        remaining = 0.0
        percent = 100
    elif completed_chars > 0 and total_chars > 0:
        ratio = completed_chars / total_chars
        percent = int(ratio * 99) # Limit to 99% until complete
        if ratio >= 1.0:
            remaining = 1.0  # compiling/writing
        else:
            total_est = elapsed / ratio
            remaining = max(1.0, total_est - elapsed)
    else:
        # Initial estimate: 0.65 seconds per character (realistic CPU speed)
        initial_est = max(3.0, total_chars * 0.65)
        remaining = max(1.0, initial_est - elapsed)
        percent = min(99, int((elapsed / initial_est) * 99)) if initial_est > 0 else 0
        
    # Enforce monotonically decreasing remaining time
    last_remaining = progress.get('last_remaining')
    if last_remaining is not None:
        remaining = min(remaining, last_remaining)
    progress['last_remaining'] = remaining

    return jsonify({
        "status": progress.get('status'),
        "completed": progress.get('completed_segments', 0),
        "total": progress.get('total_segments', 1),
        "percent": percent,
        "estimated_remaining": format_remaining_time(remaining),
        "done": status == 'complete',
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    request_id = None
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
        request_id = data.get("request_id")
        use_preview = data.get("use_preview", False)

        print(f"Received: voice={voice_name}, text_len={len(text)}, request_id={request_id}, use_preview={use_preview}", flush=True)

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

        if use_preview:
            # Pre-emotionalized text directly from preview editor
            # Split into sentences to allow progress tracking and better synthesis
            raw_sentences = re.split(r'(?<=[.!?])\s+', text)
            segments = []
            for s in raw_sentences:
                s_strip = s.strip()
                if s_strip:
                    segments.append({"text": s_strip, "speed": 1.0, "emotion": "neutral"})
            has_tags = False
            detected_tags = []
        else:
            detected_tags = extract_tags_info(text)
            has_tags      = bool(detected_tags)
            segments = parse_emotion_tags(text)

        print(f"Segments: {segments}", flush=True)

        if not segments:
            return jsonify({"error": "No valid text segments"}), 400

        # Initialize progress entry if request_id provided
        if request_id:
            total_chars = sum(len(s['text']) for s in segments)
            estimated_seconds = max(3.0, total_chars * 0.65)  # 0.65s per character for CPU, min 3s
            GENERATION_PROGRESS[request_id] = {
                'status': 'starting',
                'total_segments': len(segments),
                'completed_segments': 0,
                'total_chars': total_chars,
                'completed_chars': 0,
                'estimated_total': estimated_seconds,
                'started_at': time.time(),
            }

        all_audio   = []
        sample_rate = 24000

        for i, seg in enumerate(segments):
            if request_id and request_id in GENERATION_PROGRESS:
                GENERATION_PROGRESS[request_id]['status'] = f'generating segment {i+1}/{len(segments)}'

            seg_text = seg['text']
            if not seg_text.strip():
                if request_id and request_id in GENERATION_PROGRESS:
                    GENERATION_PROGRESS[request_id]['completed_segments'] = i + 1
                    GENERATION_PROGRESS[request_id]['completed_chars'] += len(seg_text)
                continue
            
            seg_emotion = seg.get('emotion', 'neutral')
            
            if use_preview:
                # Text is already emotionalized by preview step/user edits
                emotional_text = seg_text
                emotion_speed = 1.0
            else:
                emotional_text, emotion_speed = emotionalize_text(seg_text, seg_emotion)
            
            # Combine base speed with emotion speed (average them) and apply style multiplier
            base_speed = seg.get('speed', 1.0)
            avg_speed = (base_speed + emotion_speed) / 2
            final_speed = avg_speed * (0.8 + style * 0.4)
            
            print(f"  Original: '{seg_text[:40]}...'")
            print(f"  Emotional: '{emotional_text[:60]}...'")
            print(f"  Speed: {final_speed} (emotion: {seg_emotion})", flush=True)
            
            try:
                # Blend voice style for emotion
                voice_style = get_blended_style(voice_id, seg_emotion)
                
                samples, sr = kokoro.create(
                    emotional_text, voice=voice_style, speed=final_speed, lang="en-us"
                )
                sample_rate = sr
                all_audio.append(samples)
                print(f"  Got audio chunk: {len(samples)} samples", flush=True)
            except Exception as e:
                print(f"Warning: segment failed: {e}", flush=True)
                
            if request_id and request_id in GENERATION_PROGRESS:
                GENERATION_PROGRESS[request_id]['completed_segments'] = i + 1
                GENERATION_PROGRESS[request_id]['completed_chars'] += len(seg_text)

        if not all_audio:
            if request_id and request_id in GENERATION_PROGRESS:
                GENERATION_PROGRESS[request_id]['status'] = 'failed'
            return jsonify({"error": "No audio generated"}), 500

        combined = np.concatenate(all_audio) if len(all_audio) > 1 else all_audio[0]

        if len(combined) == 0:
            if request_id and request_id in GENERATION_PROGRESS:
                GENERATION_PROGRESS[request_id]['status'] = 'failed'
            return jsonify({"error": "No audio generated"}), 500

        # Resample from 24000 Hz to 44100 Hz to fix compatibility issues in MP3 encoding/playback
        original_sample_rate = sample_rate
        target_sample_rate = 44100
        num_samples = int(len(combined) * target_sample_rate / original_sample_rate)
        
        # Pure numpy linear interpolation resampler
        combined = np.interp(
            np.linspace(0, len(combined), num_samples, endpoint=False),
            np.arange(len(combined)),
            combined
        )
        sample_rate = target_sample_rate

        import lameenc
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(192)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(1)
        encoder.set_quality(2)
        pcm_data = np.clip(combined * 32767, -32768, 32767).astype(np.int16).tobytes()
        mp3_data = encoder.encode(pcm_data) + encoder.flush()

        filename = f"{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(VOICE_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(mp3_data)
        print(f"Saved: {filepath}", flush=True)
        duration = len(combined) / sample_rate

        if request_id and request_id in GENERATION_PROGRESS:
            GENERATION_PROGRESS[request_id]['status'] = 'complete'

        return jsonify({
            "success":         True,
            "audio_url":       f"/api/audio/{filename}",
            "duration":        f"{duration:.1f}s",
            "voice":           voice_name,
            "has_inline_tags": has_tags,
            "detected_tags":   detected_tags,
            "request_id":      request_id
        })

    except Exception as e:
        error_trace = traceback.format_exc()
        print("=" * 50, flush=True)
        print("GENERATION ERROR:", flush=True)
        print(error_trace, flush=True)
        print("=" * 50, flush=True)
        if request_id and request_id in GENERATION_PROGRESS:
            GENERATION_PROGRESS[request_id]['status'] = 'failed'
        return jsonify({
            "error": f"Generation failed: {str(e)}",
            "traceback": error_trace
        }), 500


@app.route("/api/audio/<filename>")
def serve_audio(filename):
    filename = os.path.basename(filename)
    filepath = os.path.join(VOICE_DIR, filename)
    if os.path.exists(filepath):
        if filename.endswith(".mp3"):
            return send_file(filepath, mimetype="audio/mpeg")
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
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
