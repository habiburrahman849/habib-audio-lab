'use client';

import { useState, useRef, useEffect, useCallback, useLayoutEffect } from 'react';
import { Play, Pause, Download, Settings, Mic, Zap, ChevronDown, Coffee, Check } from 'lucide-react';

// ─── Data ────────────────────────────────────────────────────────────────────

const VOICES = [
  { id: 'liam',   name: 'Maria',   role: 'Social Media Creator', style: 'Energetic',     color: 'bg-orange-400', emoji: '🎙️' },
  { id: 'sara',   name: 'Sara',   role: 'Storyteller',          style: 'Warm',          color: 'bg-pink-400',   emoji: '📖' },
  { id: 'james',  name: 'Hania',  role: 'News Anchor',          style: 'Authoritative', color: 'bg-blue-500',   emoji: '📰' },
  { id: 'mia',    name: 'salma',    role: 'Meditation Guide',     style: 'Calm',          color: 'bg-teal-400',   emoji: '🧘' },
  { id: 'carlos', name: 'Aneela', role: 'Podcast Host',         style: 'Casual',        color: 'bg-purple-500', emoji: '🎧' },
];

const EMOTION_COLORS: Record<string, { bg: string; text: string }> = {
  happy:   { bg: '#fef9c3', text: '#a16207' },
  excited: { bg: '#fce7f3', text: '#be185d' },
  sad:     { bg: '#dbeafe', text: '#1d4ed8' },
  angry:   { bg: '#fee2e2', text: '#b91c1c' },
  laughs:  { bg: '#dcfce7', text: '#15803d' },
  whisper: { bg: '#ede9fe', text: '#7c3aed' },
  pause:   { bg: '#f3f4f6', text: '#4b5563' },
};

const GEN_STEPS = [
  '✦ Reading your script...',
  '🎙 Selecting voice characteristics...',
  '🎭 Adding emotion layers...',
  '🔊 Synthesizing audio waveform...',
  '✨ Final quality check...',
  '🚀 Almost ready!',
];

const API_URL   = '/api';
const MAX_CHARS = 5000;

const DEFAULT_SCRIPT =
  "Hey everyone, welcome back to another video! [happy] I'm so excited to show you the new features we've been working on. [excited] It's been a long journey, but we finally made it! [laughs] Let's dive right in.";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  return `${m}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
}

// Convert plain text → HTML with colored [tag] spans
function toHighlightedHTML(text: string): string {
  return text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/\n/g, '<br>')
    .replace(/\[([^\]\n]+)\]/g, (_, tag) => {
      const key = tag.toLowerCase();
      const c = EMOTION_COLORS[key] ?? { bg: '#f3f4f6', text: '#4b5563' };
      return `<span contenteditable="false" style="display:inline-block;background:${c.bg};color:${c.text};padding:0 6px;border-radius:4px;font-family:monospace;font-size:0.72rem;line-height:1.6;user-select:none;">[${tag}]</span>`;
    });
}

// Extract plain text back from contenteditable (spans → [tag], <br> → \n)
function toPlainText(el: HTMLElement): string {
  let text = '';
  el.childNodes.forEach(node => {
    if (node.nodeType === Node.TEXT_NODE) {
      text += node.textContent;
    } else if (node.nodeName === 'BR') {
      text += '\n';
    } else if (node.nodeName === 'SPAN') {
      // colored tag span — read its text content as-is
      text += node.textContent;
    } else if (node.nodeName === 'DIV') {
      text += '\n' + toPlainText(node as HTMLElement);
    }
  });
  return text;
}

// Save & restore caret position (offset in plain-text chars)
function getCaretOffset(el: HTMLElement): number {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return 0;
  const range = sel.getRangeAt(0);
  const pre = range.cloneRange();
  pre.selectNodeContents(el);
  pre.setEnd(range.endContainer, range.endOffset);
  return pre.toString().length;
}

function setCaretOffset(el: HTMLElement, offset: number) {
  const sel = window.getSelection();
  if (!sel) return;
  const range = document.createRange();
  let remaining = offset;
  let found = false;

  function walk(node: Node) {
    if (found) return;
    if (node.nodeType === Node.TEXT_NODE) {
      const len = node.textContent?.length ?? 0;
      if (remaining <= len) {
        range.setStart(node, remaining);
        range.collapse(true);
        found = true;
      } else {
        remaining -= len;
      }
    } else {
      node.childNodes.forEach(walk);
    }
  }
  walk(el);
  if (!found) range.selectNodeContents(el), range.collapse(false);
  sel.removeAllRanges();
  sel.addRange(range);
}

// ─── Waveform ─────────────────────────────────────────────────────────────────

function Waveform({ playing }: { playing: boolean }) {
  const bars = 40;
  // fixed heights so they don't re-randomise on every render
  const heights = useRef(
    Array.from({ length: bars }, () => 20 + Math.random() * 60)
  );
  return (
    <div className="flex items-center justify-center gap-[2px] h-10">
      {heights.current.map((h, i) => (
        <div
          key={i}
          className="rounded-full bg-black/70"
          style={{
            width: 3,
            height: playing ? h : h * 0.35,
            transition: 'height 0.15s ease',
            animationDelay: `${i * 30}ms`,
            animation: playing ? `wave 0.8s ease-in-out ${i * 0.04}s infinite alternate` : 'none',
          }}
        />
      ))}
      <style>{`
        @keyframes wave {
          from { transform: scaleY(0.4); }
          to   { transform: scaleY(1); }
        }
      `}</style>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function StudioPage() {
  const [activeVoice, setActiveVoice]   = useState(VOICES[0]);
  const [voiceOpen,   setVoiceOpen]     = useState(false);
  const [script,      setScript]        = useState(DEFAULT_SCRIPT);
  const [stability,   setStability]     = useState(45);
  const [clarity,     setClarity]       = useState(70);
  const [generated,   setGenerated]     = useState(false);
  const [generating,  setGenerating]    = useState(false);
  const [genStep,     setGenStep]       = useState(0);
  const [playing,     setPlaying]       = useState(false);
  const [elapsed,     setElapsed]       = useState(0);
  const [duration,    setDuration]      = useState(0);
  const [audioUrl,    setAudioUrl]      = useState<string | null>(null);
  const [genError,    setGenError]      = useState<string | null>(null);

  const intervalRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef     = useRef<HTMLAudioElement | null>(null);
  const editorRef    = useRef<HTMLDivElement>(null);
  const dropdownRef  = useRef<HTMLDivElement>(null);
  const isComposing  = useRef(false);

  const progress = duration > 0 ? (elapsed / duration) * 100 : 0;

  // Keep editor HTML in sync when script state changes externally (initial load)
  useLayoutEffect(() => {
    const el = editorRef.current;
    if (!el) return;
    const current = toPlainText(el);
    if (current !== script) {
      el.innerHTML = toHighlightedHTML(script);
    }
  }, [script]);

  // close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setVoiceOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const stopInterval = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, []);

  useEffect(() => () => stopInterval(), [stopInterval]);

  // generation steps ticker
  useEffect(() => {
    if (!generating) return;
    setGenStep(0);
    let step = 0;
    const id = setInterval(() => {
      step++;
      if (step >= GEN_STEPS.length) { clearInterval(id); return; }
      setGenStep(step);
    }, 600);
    return () => clearInterval(id);
  }, [generating]);

  const handleGenerate = async () => {
    if (!script.trim() || script.length > MAX_CHARS) return;
    setGenerating(true);
    setGenerated(false);
    setGenError(null);
    setElapsed(0);
    setPlaying(false);
    stopInterval();
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }

    // Run step ticker in parallel
    let step = 0;
    setGenStep(0);
    const ticker = setInterval(() => {
      step++;
      if (step < GEN_STEPS.length) setGenStep(step);
    }, 600);

    try {
      const res = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text:  script,
          voice: activeVoice.name,
          style: (clarity / 100) * 0.4 + 0.1,
        }),
      });

      // Always parse as text first — never call res.json() directly
      const raw = await res.text();
      let data: { success?: boolean; error?: string; traceback?: string; audio_url?: string; duration?: string; detected_tags?: string[] } = {};
      try {
        data = JSON.parse(raw);
      } catch {
        clearInterval(ticker);
        // Backend is down or returned HTML — show a clean message
        if (res.status === 502 || res.status === 503 || res.status === 0) {
          setGenError('Backend server is not running. Please start the Flask server on port 5000.');
        } else {
          setGenError(`Server error (${res.status}): ${raw.substring(0, 150)}`);
        }
        setGenerating(false);
        return;
      }

      clearInterval(ticker);

      if (!res.ok || !data.success) {
        const detail = data.traceback ? `\n${data.traceback.split('\n').slice(-3).join('\n')}` : '';
        setGenError((data.error || `Server error ${res.status}`) + detail);
        setGenerating(false);
        return;
      }

      // data.audio_url is relative e.g. /api/audio/abc123.wav
      setAudioUrl(data.audio_url);

      // Pre-load audio to get real duration
      const audio = new Audio(data.audio_url);
      audioRef.current = audio;
      audio.addEventListener('loadedmetadata', () => setDuration(Math.floor(audio.duration)));
      audio.addEventListener('timeupdate', () => setElapsed(Math.floor(audio.currentTime)));
      audio.addEventListener('ended', () => { setPlaying(false); setElapsed(0); });

      setGenerated(true);
    } catch (err: unknown) {
      clearInterval(ticker);
      const msg = err instanceof Error ? err.message : 'Network error';
      // "Failed to fetch" = backend not running
      setGenError(msg.includes('fetch') ? 'Cannot connect to backend. Is the Flask server running on port 5000?' : msg);
    } finally {
      setGenerating(false);
    }
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play();
      setPlaying(true);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setElapsed(val);
    if (audioRef.current) audioRef.current.currentTime = val;
  };

  const handleDownload = async () => {
    if (!audioUrl) return;
    try {
      const res  = await fetch(audioUrl);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `habib-lab-${activeVoice.name.toLowerCase()}-${Date.now()}.wav`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert('Download failed. Please try again.');
    }
  };

  // Called on every keystroke in the contenteditable
  const handleEditorInput = useCallback(() => {
    if (isComposing.current) return;
    const el = editorRef.current;
    if (!el) return;
    const plain = toPlainText(el);
    if (plain.length > MAX_CHARS) return; // block over-limit
    const caret = getCaretOffset(el);
    const html  = toHighlightedHTML(plain);
    el.innerHTML = html;
    setScript(plain);
    setCaretOffset(el, caret);
  }, []);

  const charPct   = (script.length / MAX_CHARS) * 100;
  const charColor = script.length > MAX_CHARS * 0.9 ? 'text-red-500' : 'text-gray-400';

  return (
    <div className="flex flex-col h-screen bg-white overflow-hidden">

      {/* ── Header ── */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <h1 className="text-xl font-bold tracking-tight">Habib Audio Studio</h1>
        <a href="#" className="flex items-center gap-1.5 text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full hover:bg-amber-100 transition">
          <Coffee className="w-3.5 h-3.5" /> Buy Me Coffee
        </a>
      </header>

      {/* ── Voice Bar ── */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 py-3 flex items-center gap-3 shrink-0 overflow-x-auto">
        <span className="text-xs font-bold text-gray-400 tracking-wider shrink-0">VOICES</span>
        {VOICES.map(v => (
          <button
            key={v.id}
            onClick={() => setActiveVoice(v)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-medium transition shrink-0 ${
              activeVoice.id === v.id
                ? 'bg-black text-white border-black shadow'
                : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'
            }`}
          >
            <span className={`w-6 h-6 rounded-full ${v.color} flex items-center justify-center text-xs`}>{v.emoji}</span>
            <span>{v.name}</span>
            <span className={`text-xs ${activeVoice.id === v.id ? 'text-gray-300' : 'text-gray-400'}`}>{v.style}</span>
          </button>
        ))}
      </div>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Editor ── */}
        <main className="flex-1 flex flex-col p-6 overflow-y-auto gap-4">

          {/* Active voice badge */}
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-full ${activeVoice.color} flex items-center justify-center text-base shrink-0`}>
              {activeVoice.emoji}
            </div>
            <div>
              <p className="font-bold text-sm leading-none">{activeVoice.name}</p>
              <p className="text-xs text-gray-500">{activeVoice.style} · {activeVoice.role}</p>
            </div>
          </div>

          {/* Script label + char count */}
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold">Script</h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400">Use <code className="bg-gray-100 px-1 rounded">[emotion]</code> tags</span>
              <span className={`text-xs font-mono font-medium ${charColor}`}>
                {script.length} / {MAX_CHARS}
              </span>
            </div>
          </div>

          {/* Contenteditable script editor with live [tag] highlighting */}
          <div className="relative flex-1 min-h-[220px]">
            <div
              ref={editorRef}
              contentEditable
              suppressContentEditableWarning
              onInput={handleEditorInput}
              onCompositionStart={() => { isComposing.current = true; }}
              onCompositionEnd={() => { isComposing.current = false; handleEditorInput(); }}
              onPaste={e => {
                e.preventDefault();
                const text = e.clipboardData.getData('text/plain');
                document.execCommand('insertText', false, text);
              }}
              data-placeholder="Paste or type your script here… Use [happy], [excited], [sad], [laughs], [whisper], [pause] tags."
              className="w-full h-full min-h-[220px] border border-gray-200 rounded-xl p-4 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-black/10 focus:border-gray-400 transition overflow-y-auto"
              style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', caretColor: '#000' }}
            />
            {/* placeholder via CSS */}
            <style>{`
              [data-placeholder]:empty:before {
                content: attr(data-placeholder);
                color: #9ca3af;
                pointer-events: none;
              }
            `}</style>
            {/* char progress bar */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-xl bg-gray-100 overflow-hidden pointer-events-none">
              <div
                className={`h-full transition-all ${charPct > 90 ? 'bg-red-400' : 'bg-black'}`}
                style={{ width: `${charPct}%` }}
              />
            </div>
          </div>

          {/* Error message */}
          {genError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
              ⚠️ {genError}
            </div>
          )}

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={generating || !script.trim() || script.length > MAX_CHARS}
            className="w-full bg-black text-white py-3 rounded-xl font-bold text-base hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin shrink-0" />
                <span className="truncate">{GEN_STEPS[genStep]}</span>
              </>
            ) : (
              <><Zap className="w-4 h-4" /> Generate Audio</>
            )}
          </button>

          {/* ── Audio Player ── */}
          {generated && (
            <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-5 text-white">

              {/* Voice info */}
              <div className="flex items-center gap-2 mb-4">
                <div className={`w-7 h-7 rounded-full ${activeVoice.color} flex items-center justify-center text-sm`}>
                  {activeVoice.emoji}
                </div>
                <div>
                  <p className="text-xs font-bold leading-none">{activeVoice.name}</p>
                  <p className="text-[10px] text-gray-400">{activeVoice.role} · American English</p>
                </div>
                <span className="ml-auto flex items-center gap-1 text-[10px] text-green-400 font-medium">
                  <Check className="w-3 h-3" /> Ready
                </span>
              </div>

              {/* Waveform */}
              <div className="mb-3">
                <Waveform playing={playing} />
              </div>

              {/* Seekbar */}
              <div className="relative h-2 bg-white/20 rounded-full mb-2 cursor-pointer">
                <div
                  className="absolute left-0 top-0 h-full bg-white rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
                {/* thumb dot */}
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow transition-all"
                  style={{ left: `calc(${progress}% - 6px)` }}
                />
                <input
                  type="range"
                  min={0}
                  max={duration || 1}
                  value={elapsed}
                  onChange={handleSeek}
                  className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
                />
              </div>

              {/* Time */}
              <div className="flex justify-between text-[10px] font-mono text-gray-400 mb-4">
                <span>{formatTime(elapsed)}</span>
                <span>{formatTime(duration)}</span>
              </div>

              {/* Controls */}
              <div className="flex items-center justify-between">
                <button
                  onClick={togglePlay}
                  className="bg-white text-black p-3 rounded-full hover:scale-105 transition"
                >
                  {playing
                    ? <Pause className="w-5 h-5 fill-black" />
                    : <Play  className="w-5 h-5 fill-black" />
                  }
                </button>

                <button
                  onClick={handleDownload}
                  className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-4 py-2 rounded-full transition"
                >
                  <Download className="w-3.5 h-3.5" /> Download WAV
                </button>
              </div>
            </div>
          )}
        </main>

        {/* ── Settings Panel ── */}
        <aside className="w-72 bg-gray-50 border-l border-gray-200 flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-gray-200 flex items-center gap-2 font-bold text-sm">
            <Settings className="w-4 h-4" /> Settings
          </div>

          <div className="p-5 space-y-6">

            {/* Coffee */}
            <div className="bg-amber-50 border border-amber-200 p-3 rounded-xl">
              <p className="font-bold text-xs text-amber-800">☕ If you love this,</p>
              <p className="text-xs text-amber-700 mt-0.5">Buy Me Coffee to keep it energetic. Thanks!</p>
            </div>

            {/* Voice Dropdown */}
            <div>
              <p className="text-xs font-bold text-gray-400 tracking-wider mb-2">VOICE</p>
              <div ref={dropdownRef} className="relative">
                <button
                  onClick={() => setVoiceOpen(o => !o)}
                  className="w-full flex items-center gap-3 bg-white border border-gray-200 rounded-xl p-3 shadow-sm hover:border-gray-300 transition"
                >
                  <div className={`w-9 h-9 rounded-full ${activeVoice.color} flex items-center justify-center text-base shrink-0`}>
                    {activeVoice.emoji}
                  </div>
                  <div className="flex-1 text-left min-w-0">
                    <p className="font-bold text-sm leading-none">{activeVoice.name}</p>
                    <p className="text-xs text-gray-500 truncate">{activeVoice.role}</p>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${voiceOpen ? 'rotate-180' : ''}`} />
                </button>

                {voiceOpen && (
                  <div className="absolute z-20 top-full mt-1 left-0 right-0 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                    {VOICES.map(v => (
                      <button
                        key={v.id}
                        onClick={() => { setActiveVoice(v); setVoiceOpen(false); }}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 transition text-left ${
                          activeVoice.id === v.id ? 'bg-gray-50' : ''
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-full ${v.color} flex items-center justify-center text-sm shrink-0`}>
                          {v.emoji}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-xs">{v.name}</p>
                          <p className="text-xs text-gray-500 truncate">{v.role}</p>
                        </div>
                        {activeVoice.id === v.id && <Check className="w-3.5 h-3.5 text-black shrink-0" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Model */}
            <div className="flex justify-between items-center bg-white border border-gray-200 p-3 rounded-xl shadow-sm">
              <div className="flex items-center gap-2">
                <Mic className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">H1 New Model</span>
              </div>
              <span className="bg-black text-white text-[10px] font-bold px-2 py-0.5 rounded">LATEST</span>
            </div>

            {/* Language — fixed */}
            <div className="flex justify-between items-center bg-white border border-gray-200 p-3 rounded-xl shadow-sm">
              <div className="flex items-center gap-2">
                <span className="text-base">🇺🇸</span>
                <div>
                  <p className="text-sm font-medium leading-none">American English</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">en-US</p>
                </div>
              </div>
            </div>

            {/* Stability */}
            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span>Stability</span><span>{stability}%</span>
              </div>
              <input type="range" className="w-full accent-black" min={0} max={100} value={stability}
                onChange={e => setStability(Number(e.target.value))} />
              <p className="text-xs text-gray-400 mt-1">Higher = more consistent tone</p>
            </div>

            {/* Clarity */}
            <div>
              <div className="flex justify-between text-xs font-medium mb-1.5">
                <span>Clarity + Similarity</span><span>{clarity}%</span>
              </div>
              <input type="range" className="w-full accent-black" min={0} max={100} value={clarity}
                onChange={e => setClarity(Number(e.target.value))} />
              <p className="text-xs text-gray-400 mt-1">Higher = closer to original voice</p>
            </div>

            {/* Emotion tag reference */}
            <div>
              <p className="text-xs font-bold text-gray-400 tracking-wider mb-2">EMOTION TAGS</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(EMOTION_COLORS).map(([tag, c]) => (
                  <span
                    key={tag}
                    className="text-xs px-2 py-0.5 rounded font-mono cursor-default"
                    style={{ background: c.bg, color: c.text }}
                  >
                    [{tag}]
                  </span>
                ))}
              </div>
            </div>

          </div>
        </aside>
      </div>
    </div>
  );
}