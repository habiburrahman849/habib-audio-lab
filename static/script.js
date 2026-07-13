// ─── CONFIG ───
const VOICES = {
    "Maira":  { id: "af_heart",  desc: "Warm & Expressive",  tags: ["American", "Female"], emoji: "💕" },
    "Hania":  { id: "af_bella",  desc: "Clear & Natural",    tags: ["American", "Female"], emoji: "🌸" },
    "Saniya": { id: "af_nicole", desc: "Soft & Gentle",      tags: ["American", "Female"], emoji: "🌙" },
    "Fatma":  { id: "af_sarah",  desc: "Professional",       tags: ["American", "Female"], emoji: "✨" },
    "Ayesha": { id: "af_sky",    desc: "Bright & Youthful",  tags: ["American", "Female"], emoji: "☀️" },
};

const TAG_COLORS = {
    '[happy]': 'blue', '[sad]': 'blue', '[angry]': 'red', '[excited]': 'yellow',
    '[calm]': 'green', '[whisper]': 'purple', '[loving]': 'purple', '[neutral]': 'blue',
    '[laughs]': 'green', '[chuckles]': 'green', '[sighs]': 'blue', '[gasps]': 'yellow',
    '[clears throat]': 'blue', '[coughs]': 'blue', '[shouts]': 'red', '[whispers]': 'purple',
    '[sings]': 'purple', '[cries]': 'red', '[yawns]': 'green', '[screams]': 'red',
};

// ─── GLOBAL STATE ───
let selectedVoice = "Maira";
let selectedEmotion = "neutral";
let historyItems = [];
let currentAudioUrl = null;
let audioElement = null;
let isPlaying = false;
let progressTimer = null;
let lastHighlightedIndex = -1;
let scriptWords = [];
let generationCount = parseInt(localStorage.getItem('genCount') || '0');

// ─── INIT ───
document.addEventListener('DOMContentLoaded', () => {
    renderVoiceList();
    handleInput();
});

// ─── VOICE LIST ───
function renderVoiceList(filter = '') {
    const list = document.getElementById('voiceList');
    if (!list) return;
    const filtered = Object.entries(VOICES).filter(([name]) =>
        name.toLowerCase().includes(filter.toLowerCase())
    );
    list.innerHTML = filtered.map(([name, info]) => `
        <div class="voice-item ${name === selectedVoice ? 'active' : ''}" onclick="selectVoice('${name}')">
            <div class="voice-avatar">${info.emoji}</div>
            <div class="voice-info">
                <div class="voice-name">${name}</div>
                <div class="voice-tags">
                    ${info.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                    <span class="tag accent">${info.desc}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function selectVoice(name) {
    selectedVoice = name;
    const searchEl = document.getElementById('voiceSearch');
    renderVoiceList(searchEl ? searchEl.value : '');
}

function filterVoices() {
    const q = document.getElementById('voiceSearch').value;
    renderVoiceList(q);
}

// ─── EMOTIONS ───
function selectEmotion(el, emotion) {
    document.querySelectorAll('.emotion-card').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    selectedEmotion = emotion;
}

// ─── TAG HIGHLIGHTING ───
function handleInput() {
    const textarea = document.getElementById('textInput');
    const backdrop = document.getElementById('editorBackdrop');
    if (!textarea || !backdrop) return;
    const text = textarea.value;

    const charCount = document.getElementById('charCount');
    if (charCount) charCount.textContent = text.length;

    let highlighted = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    Object.keys(TAG_COLORS).forEach(tag => {
        const color = TAG_COLORS[tag];
        const regex = new RegExp(tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        highlighted = highlighted.replace(regex, `<span class="tag-${color}">${tag}</span>`);
    });

    backdrop.innerHTML = highlighted + '<br>&nbsp;';
    updateDetectedTags(text);
}

function syncScroll() {
    const textarea = document.getElementById('textInput');
    const backdrop = document.getElementById('editorBackdrop');
    if (textarea && backdrop) backdrop.scrollTop = textarea.scrollTop;
}

function updateDetectedTags(text) {
    const container = document.getElementById('detectedTags');
    if (!container) return;
    const found = text.match(/\[[^\]]+\]/g) || [];
    const validTags = found.filter(t => TAG_COLORS[t.toLowerCase()]);

    if (validTags.length === 0) {
        container.innerHTML = '<span class="detected-hint">None yet — add tags above</span>';
        return;
    }

    container.innerHTML = validTags.map(tag => {
        const color = TAG_COLORS[tag.toLowerCase()] || 'blue';
        return `<span class="detected-tag ${color}">${tag}</span>`;
    }).join('');
}

// ─── INSERT TAG ───
function insertTag(tag) {
    const textarea = document.getElementById('textInput');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const insert = tag + ' ';

    textarea.value = text.substring(0, start) + insert + text.substring(end);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = start + insert.length;
    handleInput();
}

// ─── SLIDERS ───
function updateSliderVal(id) {
    const el = document.getElementById(id);
    const valEl = document.getElementById(id + 'Val');
    if (el && valEl) valEl.textContent = el.value + '%';
}

// ─── GENERATE ───
async function generateSpeech() {
    const textarea = document.getElementById('textInput');
    if (!textarea) return;
    const text = textarea.value.trim();
    if (!text) { alert('Please enter your script!'); return; }
    if (text.length > 5000) { alert('Text too long! Max 5000 characters.'); return; }

    const loadingOverlay = document.getElementById('loadingOverlay');
    const genBtn = document.getElementById('genBtn');
    if (loadingOverlay) loadingOverlay.classList.add('show');
    if (genBtn) genBtn.disabled = true;

    const formData = new FormData();
    formData.append('text', text);
    formData.append('voice', selectedVoice);
    formData.append('emotion', selectedEmotion);
    formData.append('stability', (document.getElementById('stability')?.value ?? 50) / 100);
    formData.append('clarity', (document.getElementById('clarity')?.value ?? 75) / 100);
    formData.append('style', (document.getElementById('style')?.value ?? 30) / 100);

    try {
        const res = await fetch('/generate', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            currentAudioUrl = data.audio_url;
            const audioEl = document.getElementById('audioElement');
            if (audioEl) {
                audioEl.src = data.audio_url;
                document.getElementById('audioPlayer')?.classList.add('show');
            }

            const meta = document.getElementById('resultMeta');
            if (meta) {
                let tagsHtml = '';
                if (data.detected_tags && data.detected_tags.length > 0) {
                    tagsHtml = data.detected_tags.map(t => {
                        const color = TAG_COLORS[t] || 'blue';
                        return `<span class="detected-tag ${color}">${t}</span>`;
                    }).join('');
                }
                meta.innerHTML = `
                    <span class="result-badge">👩 ${data.voice}</span>
                    <span class="result-badge">🎭 ${data.emotion}</span>
                    <span class="result-badge">⏱️ ${data.duration}</span>
                    ${data.has_inline_tags ? '<span class="result-badge">🏷️ Inline Tags</span>' : ''}
                    ${tagsHtml}
                `;
            }

            addToHistory(selectedVoice, selectedEmotion, data.duration, data.audio_url);
            document.getElementById('audioPlayer')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed: ' + err.message);
    } finally {
        if (loadingOverlay) loadingOverlay.classList.remove('show');
        if (genBtn) genBtn.disabled = false;
    }
}

// ─── DOWNLOAD ───
async function downloadAudio() {
    if (!currentAudioUrl) { alert('No audio generated yet.'); return; }
    try {
        const response = await fetch(currentAudioUrl);
        if (!response.ok) throw new Error('Download failed');
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `habib-lab-voiceover-${Date.now()}.wav`;
        link.click();
    } catch (err) {
        alert('Download failed: ' + err.message);
    }
}

function generateAgain() {
    generateSpeech();
}

// ─── HISTORY ───
function addToHistory(voice, emotion, duration, audioUrl) {
    historyItems.unshift({
        voice, emotion, duration,
        time: new Date().toLocaleTimeString(),
        audioUrl
    });
    renderHistory();
}

function renderHistory() {
    const list = document.getElementById('historyList');
    if (!list) return;
    if (historyItems.length === 0) {
        list.innerHTML = '<p class="empty-history">Your generated voiceovers will appear here</p>';
        return;
    }
    list.innerHTML = historyItems.map((item, i) => `
        <div class="history-row">
            <span class="history-tag">${item.voice}</span>
            <span class="history-tag">${item.emotion}</span>
            <span class="history-tag">${item.duration}</span>
            <span class="history-time">${item.time}</span>
            <button onclick="playHistory(${i})">▶️</button>
            <button onclick="downloadHistory(${i})">⬇️</button>
        </div>
    `).join('');
}

function playHistory(i) {
    const audioEl = document.getElementById('audioElement');
    if (!audioEl) return;
    audioEl.src = historyItems[i].audioUrl;
    document.getElementById('audioPlayer')?.classList.add('show');
    audioEl.play();
}

async function downloadHistory(i) {
    currentAudioUrl = historyItems[i].audioUrl;
    await downloadAudio();
}

// ─── SOCIAL SHARING ───
function shareOn(platform) {
    const url = encodeURIComponent(window.location.href);
    const text = encodeURIComponent("Check out this free AI text-to-speech tool — turn text into emotional voiceovers!");
    const title = encodeURIComponent("Habib Lab's AI - Emotional TTS");

    const links = {
        facebook: `https://www.facebook.com/sharer/sharer.php?u=${url}`,
        twitter:  `https://twitter.com/intent/tweet?url=${url}&text=${text}`,
        whatsapp: `https://wa.me/?text=${text}%20${url}`,
        email:    `mailto:?subject=${title}&body=${text}%20${url}`
    };

    if (!links[platform]) return;
    if (platform === 'email') {
        window.location.href = links[platform];
    } else {
        window.open(links[platform], '_blank', 'width=600,height=400');
    }
}
