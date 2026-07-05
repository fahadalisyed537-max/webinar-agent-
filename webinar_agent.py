#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebinarAgent — all-in-one edition
==================================

Joins a webinar/meeting (Zoom, Google Meet, Teams, Webex, YouTube Live, or any
generic URL), records the audio, transcribes it locally with faster-whisper,
and saves a clean transcript as both .txt and .md — plus an optional AI
summary if you give it an OpenRouter API key.

WHY THIS VERSION IS DIFFERENT FROM THE ORIGINAL PROJECT
--------------------------------------------------------
- ONE file. No FastAPI backend, no React frontend, no separate agents/ folder.
- Uses Playwright's *sync* API instead of async. The vast majority of
  "Playwright works everywhere except my terminal on Windows" errors come
  from asyncio's event loop / subprocess handling on Windows (the async API
  needs a Proactor event loop to spawn the browser; a lot of setups end up on
  the wrong one). The sync API sidesteps that whole class of bugs.
- On Windows it captures system audio directly via WASAPI loopback
  (the "PyAudioWPatch" library) — no VB-Cable, no Stereo Mix, no driver
  install, no reboot. That was the original project's #1 reported pain
  point. ffmpeg + a virtual cable is kept only as an automatic fallback.
- No langchain, no python-dotenv, no requests. Summaries call OpenRouter
  with the standard library (urllib), so there's far less to install and
  far less that can break.
- Built-in self-check: `python webinar_agent.py --check` tells you exactly
  what's missing instead of you guessing from a stack trace.

QUICK START
-----------
    pip install -r requirements.txt
    python -m playwright install chromium
    python webinar_agent.py --check
    python webinar_agent.py https://meet.google.com/abc-defg-hij

Or just double-click run_webinar_agent.bat (Windows) — it does all of the
above for you and then asks you for a URL.

CONFIG
------
Edit the defaults below, or pass them as command-line flags
(run `python webinar_agent.py --help` to see all of them).

A NOTE ON RECORDING
--------------------
The bot joins with a visible name ("AI Note Taker" by default) so everyone
in the meeting can see it's there — make sure that's fine with the host and
complies with your meeting platform's terms and any recording-consent laws
that apply where you are before you hit record.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — edit these defaults if you don't want to type flags every time
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_NAME = "AI Note Taker"
DEFAULT_DURATION_MIN = 60
DEFAULT_WHISPER_MODEL = "base"          # tiny / base / small / medium / large
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-3-haiku"
DEFAULT_OUTPUT_DIR = "outputs"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def print_banner() -> None:
    print(r"""
 __        __   _     _                _                    _
 \ \      / /__| |__ (_)_ __   __ _ _ _| | __ _  __ _  ___ _ __ | |_
  \ \ /\ / / _ \ '_ \| | '_ \ / _` | '__| |/ _` |/ _` |/ _ \ '_ \| __|
   \ V  V /  __/ |_) | | | | | (_| | |  | | (_| | (_| |  __/ | | | |_
    \_/\_/ \___|_.__/|_|_| |_|\__,_|_|  |_|\__,_|\__, |\___|_| |_|\__|
                                                  |___/
""")


def read_key_file() -> str | None:
    """Look for a sibling openrouter_key.txt as a dependency-free alternative to .env."""
    key_file = Path(__file__).resolve().parent / "openrouter_key.txt"
    try:
        if key_file.exists():
            first_line = key_file.read_text(encoding="utf-8").strip().splitlines()
            if first_line:
                return first_line[0].strip()
    except Exception:
        pass
    return None


def format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# Platform detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_platform(url: str) -> str:
    u = url.lower()
    if "zoom.us" in u or "zoom.com" in u:
        return "zoom"
    if "teams.microsoft.com" in u or "teams.live.com" in u:
        return "teams"
    if "meet.google.com" in u:
        return "google_meet"
    if "webex.com" in u:
        return "webex"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "generic"


# ─────────────────────────────────────────────────────────────────────────────
# Audio recording — WASAPI loopback (Windows, no virtual cable) or ffmpeg
# ─────────────────────────────────────────────────────────────────────────────

class WasapiLoopbackRecorder:
    """Records 'what you hear' on Windows via WASAPI loopback. No VB-Cable,
    no Stereo Mix, no driver install needed — works on a stock Windows box."""

    def __init__(self, output_path):
        self.output_path = str(output_path)
        self._pa = None
        self._stream = None
        self._wave_file = None

    def start(self) -> str:
        import wave
        import pyaudiowpatch as pyaudio

        self._pa = pyaudio.PyAudio()
        wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        speakers = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if not speakers.get("isLoopbackDevice"):
            match = None
            for loopback in self._pa.get_loopback_device_info_generator():
                if speakers["name"] in loopback["name"]:
                    match = loopback
                    break
            if match is None:
                self._pa.terminate()
                raise RuntimeError("No WASAPI loopback device found for the default speakers.")
            speakers = match

        self._wave_file = wave.open(self.output_path, "wb")
        self._wave_file.setnchannels(speakers["maxInputChannels"])
        self._wave_file.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
        self._wave_file.setframerate(int(speakers["defaultSampleRate"]))

        def callback(in_data, frame_count, time_info, status):
            self._wave_file.writeframes(in_data)
            return (in_data, pyaudio.paContinue)

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=speakers["maxInputChannels"],
            rate=int(speakers["defaultSampleRate"]),
            input=True,
            input_device_index=speakers["index"],
            stream_callback=callback,
        )
        self._stream.start_stream()
        return speakers["name"]

    def stop(self) -> None:
        try:
            if self._stream is not None:
                self._stream.stop_stream()
                self._stream.close()
        except Exception:
            pass
        try:
            if self._wave_file is not None:
                self._wave_file.close()
        except Exception:
            pass
        try:
            if self._pa is not None:
                self._pa.terminate()
        except Exception:
            pass


def _detect_windows_dshow_device() -> str | None:
    """Ask ffmpeg what audio input devices it can see and pick a sensible one."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stderr or ""
        names = re.findall(r'"([^"]+)"\s*\(audio\)', output)
        for preferred in ("CABLE Output", "Stereo Mix"):
            for n in names:
                if preferred.lower() in n.lower():
                    return n
        return names[0] if names else None
    except Exception:
        return None


class FfmpegRecorder:
    """Cross-platform fallback. Needs ffmpeg, and on Windows needs a virtual
    audio device (VB-Cable) or Stereo Mix enabled — see README."""

    def __init__(self, output_path, device_override=None):
        self.output_path = str(output_path)
        self.device_override = device_override
        self.process = None

    def _build_cmd(self):
        system = platform.system()
        if system == "Windows":
            device = self.device_override or _detect_windows_dshow_device() or "Stereo Mix"
            return ["ffmpeg", "-y", "-f", "dshow", "-i", f"audio={device}",
                     "-ar", "16000", "-ac", "1", "-codec:a", "pcm_s16le", self.output_path]
        if system == "Darwin":
            device = self.device_override or ":BlackHole 2ch"
            return ["ffmpeg", "-y", "-f", "avfoundation", "-i", device,
                     "-ar", "16000", "-ac", "1", "-codec:a", "pcm_s16le", self.output_path]
        device = self.device_override or "default.monitor"
        return ["ffmpeg", "-y", "-f", "pulse", "-i", device,
                 "-ar", "16000", "-ac", "1", "-codec:a", "pcm_s16le", self.output_path]

    def start(self) -> None:
        cmd = self._build_cmd()
        self.process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if not self.process:
            return
        try:
            self.process.stdin.write(b"q")
            self.process.stdin.flush()
        except Exception:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


def get_recorder(output_path, args):
    """Pick the least-hassle recorder available."""
    system = platform.system()
    if system == "Windows" and not args.force_ffmpeg:
        try:
            import pyaudiowpatch  # noqa: F401
            return WasapiLoopbackRecorder(output_path), "wasapi (no virtual cable needed)"
        except ImportError:
            log("PyAudioWPatch isn't installed — falling back to ffmpeg + a virtual audio device.")
            log("Tip: `pip install PyAudioWPatch` removes the need for VB-Cable/Stereo Mix entirely.")
    return FfmpegRecorder(str(output_path), device_override=args.audio_device), "ffmpeg"


# ─────────────────────────────────────────────────────────────────────────────
# Browser bot (Playwright SYNC API — see module docstring for why)
# ─────────────────────────────────────────────────────────────────────────────

def try_click_any(page, selectors, timeout=3000) -> bool:
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                el.click(timeout=timeout)
                return True
        except Exception:
            continue
    return False


def fill_if_exists(page, selector, value, timeout=3000) -> bool:
    try:
        el = page.locator(selector).first
        if el.count() > 0:
            el.fill(value, timeout=timeout)
            return True
    except Exception:
        pass
    return False


def join_zoom(page, url, name) -> bool:
    if "/j/" in url and "browser=1" not in url:
        url = url + ("&" if "?" in url else "?") + "browser=1"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    try_click_any(page, ['a[href*="browser=1"]', 'text="join from your browser"',
                          'text="Join from Your Browser"', '.join-browser-link'])
    page.wait_for_timeout(2000)
    fill_if_exists(page, "#inputname", name)
    fill_if_exists(page, 'input[placeholder*="name" i]', name)
    try_click_any(page, ["#joinBtn", 'button[type="submit"]', 'text="Join"', ".zm-btn--primary"])
    page.wait_for_timeout(3000)
    try_click_any(page, ['button[aria-label*="mute" i]', ".join-audio-by-voip__join-btn"])
    return True


def join_google_meet(page, url, name) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)
    try_click_any(page, ['text="Continue without signing in"'])
    page.wait_for_timeout(1000)
    fill_if_exists(page, 'input[placeholder*="name" i]', name)
    fill_if_exists(page, '[data-placeholder*="name" i]', name)
    try_click_any(page, ['[data-is-muted="false"][aria-label*="micro" i]'])
    try_click_any(page, ['[data-is-muted="false"][aria-label*="cam" i]'])
    page.wait_for_timeout(1000)
    try_click_any(page, ['text="Ask to join"', 'text="Join now"', 'text="Request to join"',
                          '[jsname="Qx7uuf"]'])
    page.wait_for_timeout(3000)
    return True


def join_teams(page, url, name) -> bool:
    if "launchAgent=false" not in url and "launchAgent=true" not in url:
        url = url + ("&" if "?" in url else "?") + "launchAgent=false"
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    try_click_any(page, ['text="Continue on this browser"', 'text="Join on the web instead"',
                          '[data-tid="joinOnWeb"]'])
    page.wait_for_timeout(2000)
    fill_if_exists(page, "#username", name)
    fill_if_exists(page, 'input[type="text"][placeholder*="name" i]', name)
    try_click_any(page, ['[data-tid="toggle-mute"]'])
    try_click_any(page, ['[data-tid="toggle-video"]'])
    try_click_any(page, ['[data-tid="prejoin-join-button"]', 'text="Join now"', 'text="Join meeting"'])
    return True


def join_webex(page, url, name) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    try_click_any(page, ['text="Join from your browser"', "#joinBtn"])
    fill_if_exists(page, "#yourName", name)
    fill_if_exists(page, 'input[placeholder*="name" i]', name)
    try_click_any(page, ['text="Next"', 'text="Join"', "#joinButton"])
    return True


def join_youtube(page, url, name) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)
    try_click_any(page, ['.ytp-play-button[aria-label="Play"]'])
    try_click_any(page, [".ytp-skip-ad-button", ".ytp-ad-skip-button"])
    return True


def join_generic(page, url, name) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    fill_if_exists(page, 'input[placeholder*="name" i]', name)
    try_click_any(page, ['text="Join"', 'text="Enter"', 'text="Start"', 'button[type="submit"]'])
    return True


JOIN_HANDLERS = {
    "zoom": join_zoom,
    "google_meet": join_google_meet,
    "teams": join_teams,
    "webex": join_webex,
    "youtube": join_youtube,
    "generic": join_generic,
}


def run_bot(url, name, platform_name, duration_minutes, headless=False) -> bool:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    handler = JOIN_HANDLERS.get(platform_name, join_generic)

    def _launch(pw):
        return pw.chromium.launch(
            headless=headless,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--start-maximized",
            ],
        )

    try:
        with sync_playwright() as pw:
            try:
                browser = _launch(pw)
            except PlaywrightError as e:
                if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                    log("Chromium isn't installed for this environment yet — installing now (one-time, ~150MB)...")
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
                    browser = _launch(pw)
                else:
                    raise

            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
                permissions=["microphone", "camera"],
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            try:
                success = handler(page, url, name)
            except Exception as e:
                log(f"[WARN] Join flow hit a snag, recording will continue anyway: {e}")
                success = True

            if success:
                log(f"Recording for up to {duration_minutes} minute(s). Press Ctrl+C any time to stop early and process now.")
                total_seconds = duration_minutes * 60
                elapsed = 0
                try:
                    while elapsed < total_seconds:
                        time.sleep(min(1, total_seconds - elapsed))
                        elapsed += 1
                except KeyboardInterrupt:
                    log("Stopping early...")

            context.close()
            browser.close()
            return success
    except Exception as e:
        log(f"[ERROR] Browser automation failed: {e}")
        log("Run `python webinar_agent.py --check` for a diagnostic report.")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Transcription (faster-whisper, fully local)
# ─────────────────────────────────────────────────────────────────────────────

def transcribe(audio_path, model_size=DEFAULT_WHISPER_MODEL):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        language=None,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
        word_timestamps=False,
    )

    chunks = []
    for seg in segments:
        chunks.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "timestamp": format_time(seg.start),
        })
    return chunks, info


# ─────────────────────────────────────────────────────────────────────────────
# Optional AI summary (OpenRouter, plain urllib — no langchain/requests)
# ─────────────────────────────────────────────────────────────────────────────

CHUNK_SUMMARY_PROMPT = """You are an expert note-taker. Summarize this webinar segment concisely.
Extract only what matters: key points, numbers, frameworks, and actionable advice.
Ignore filler, repetition, and small talk.

Segment:
{text}

Concise Summary:"""

FINAL_BITES_PROMPT = """You are a world-class webinar analyst. Based on the webinar content below, create structured "bites" — the highest-value extractions from this session.

Webinar Content:
{text}

Return ONLY a valid JSON object with this exact structure:
{{
  "executive_summary": "3-4 sentence summary of the entire webinar. What was it about and why does it matter?",
  "key_insights": [
    {{"insight": "The insight statement", "context": "Why this matters"}}
  ],
  "action_items": [
    {{"action": "Specific thing to do", "priority": "high/medium/low"}}
  ],
  "memorable_quotes": [
    {{"quote": "Exact or near-exact quote", "speaker": "if identifiable"}}
  ],
  "frameworks_and_models": [
    {{"name": "Name of framework/model if any", "description": "What it is and how to apply it"}}
  ],
  "numbers_and_stats": [
    {{"stat": "The number or statistic", "context": "What it means"}}
  ],
  "missed_if_asleep": "Single sentence: the ONE thing you absolutely cannot miss from this webinar"
}}

JSON only, no markdown, no preamble:"""


def _call_openrouter(prompt, api_key, model) -> str:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2048,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://webinar-agent.local",
            "X-Title": "WebinarAgent",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def parse_bites(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return json.loads(clean.strip())
    except Exception:
        return {
            "executive_summary": "Could not parse the AI summary output.",
            "key_insights": [], "action_items": [], "memorable_quotes": [],
            "frameworks_and_models": [], "numbers_and_stats": [],
            "missed_if_asleep": (raw[:300] if raw else ""),
        }


def summarize_with_openrouter(transcript_text, api_key, model) -> dict | None:
    try:
        if len(transcript_text) > 9000:
            chunk_size = 6000
            parts = [transcript_text[i:i + chunk_size] for i in range(0, len(transcript_text), chunk_size)]
            summaries = [_call_openrouter(CHUNK_SUMMARY_PROMPT.format(text=p), api_key, model) for p in parts]
            combined = "\n\n---\n\n".join(summaries)[:12000]
        else:
            combined = transcript_text
        raw = _call_openrouter(FINAL_BITES_PROMPT.format(text=combined), api_key, model)
        return parse_bites(raw)
    except Exception as e:
        log(f"AI summary skipped (couldn't reach OpenRouter or parse the reply): {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Output files — the new .txt / .md transcript feature
# ─────────────────────────────────────────────────────────────────────────────

def build_txt(chunks, meta) -> str:
    lines = [
        "Webinar Transcript",
        f"URL: {meta['url']}",
        f"Platform: {meta['platform']}",
        f"Date: {meta['date']}",
        "-" * 50,
        "",
    ]
    if not chunks:
        lines.append("[No speech was transcribed — run `python webinar_agent.py --check` to diagnose audio capture]")
    for c in chunks:
        if c.get("text"):
            lines.append(f"[{c['timestamp']}] {c['text']}")
    return "\n".join(lines) + "\n"


def build_md(chunks, meta, bites=None) -> str:
    md = [
        "# Webinar Transcript",
        "",
        "| | |",
        "|---|---|",
        f"| **URL** | {meta['url']} |",
        f"| **Platform** | {meta['platform']} |",
        f"| **Date** | {meta['date']} |",
        "",
    ]

    if bites:
        md += ["## AI Summary", "", f"**Executive summary:** {bites.get('executive_summary', '')}", ""]

        insights = bites.get("key_insights") or []
        if insights:
            md.append("### Key Insights")
            for i in insights:
                md.append(f"- {i.get('insight', '')} _({i.get('context', '')})_")
            md.append("")

        actions = bites.get("action_items") or []
        if actions:
            md.append("### Action Items")
            for a in actions:
                md.append(f"- [{a.get('priority', '')}] {a.get('action', '')}")
            md.append("")

        quotes = bites.get("memorable_quotes") or []
        if quotes:
            md.append("### Memorable Quotes")
            for q in quotes:
                md.append(f"> {q.get('quote', '')} — {q.get('speaker') or 'unknown speaker'}")
            md.append("")

        frameworks = bites.get("frameworks_and_models") or []
        if frameworks:
            md.append("### Frameworks & Models")
            for f in frameworks:
                md.append(f"- **{f.get('name', '')}**: {f.get('description', '')}")
            md.append("")

        stats = bites.get("numbers_and_stats") or []
        if stats:
            md.append("### Numbers & Stats")
            for s in stats:
                md.append(f"- {s.get('stat', '')} — {s.get('context', '')}")
            md.append("")

        if bites.get("missed_if_asleep"):
            md.append(f"> **Don't miss this:** {bites['missed_if_asleep']}")
            md.append("")

        md += ["---", ""]

    md += ["## Full Transcript", ""]
    if not chunks:
        md.append("_No speech was transcribed. Run `python webinar_agent.py --check` to diagnose audio capture._")
    for c in chunks:
        if c.get("text"):
            md.append(f"**[{c['timestamp']}]** {c['text']}")
            md.append("")
    return "\n".join(md)


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostics — `python webinar_agent.py --check`
# ─────────────────────────────────────────────────────────────────────────────

def run_diagnostics() -> None:
    log("Running WebinarAgent diagnostics...\n")
    log(f"Python:   {sys.version.split()[0]}  ({sys.executable})")
    log(f"OS:       {platform.system()} {platform.release()}")

    try:
        import playwright  # noqa: F401
        log("[OK]   playwright package is importable")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                browser.close()
            log("[OK]   Chromium launches successfully")
        except Exception as e:
            log(f"[FAIL] Chromium failed to launch: {e}")
            log("       Fix: python -m playwright install chromium")
    except ImportError:
        log("[FAIL] playwright is not installed. Fix: pip install playwright")

    if shutil.which("ffmpeg"):
        log("[OK]   ffmpeg found on PATH")
    else:
        log("[INFO] ffmpeg not found (only needed if WASAPI loopback / BlackHole isn't used)")

    if platform.system() == "Windows":
        try:
            import pyaudiowpatch  # noqa: F401
            log("[OK]   PyAudioWPatch installed — WASAPI loopback ready, no VB-Cable needed")
        except ImportError:
            log("[INFO] PyAudioWPatch not installed — will fall back to ffmpeg + Stereo Mix/VB-Cable")
            log("       Recommended fix: pip install PyAudioWPatch")

    try:
        import faster_whisper  # noqa: F401
        log("[OK]   faster-whisper is installed")
    except ImportError:
        log("[FAIL] faster-whisper is not installed. Fix: pip install faster-whisper")

    key = read_key_file() or os.environ.get("OPENROUTER_API_KEY")
    log("[OK]   OpenRouter key found (AI summaries enabled)" if key else
        "[INFO] No OpenRouter key found — transcripts will still work, summaries will be skipped")

    log("\nDiagnostics complete.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI / main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="WebinarAgent — join a webinar, record it, transcribe it, save notes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python webinar_agent.py https://meet.google.com/abc-defg-hij\n"
            "  python webinar_agent.py --check\n"
            "  python webinar_agent.py URL --duration 90 --whisper-model small\n"
        ),
    )
    p.add_argument("url", nargs="?", default=None, help="Webinar/meeting URL")
    p.add_argument("--name", default=DEFAULT_NAME, help="Display name the bot joins with")
    p.add_argument("--duration", type=int, default=DEFAULT_DURATION_MIN, help="Max minutes to record")
    p.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL,
                    choices=["tiny", "base", "small", "medium", "large"],
                    help="Local transcription model: bigger = more accurate, slower")
    p.add_argument("--no-summary", action="store_true", help="Skip the AI summary, just save the transcript")
    p.add_argument("--api-key", default=None, help="OpenRouter API key (optional)")
    p.add_argument("--model", default=DEFAULT_OPENROUTER_MODEL, help="OpenRouter model id for the summary")
    p.add_argument("--audio-device", default=None, help="Override ffmpeg audio device name (fallback mode only)")
    p.add_argument("--force-ffmpeg", action="store_true", help="Use ffmpeg instead of WASAPI loopback on Windows")
    p.add_argument("--headless", action="store_true", help="Run the browser headless (less reliable on some sites)")
    p.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Where transcripts/audio get saved")
    p.add_argument("--check", action="store_true", help="Run setup diagnostics and exit")
    return p.parse_args()


def main():
    args = parse_args()

    if args.check:
        run_diagnostics()
        return

    url = args.url
    if not url:
        print_banner()
        choice = input("No URL given. Press Enter to type one now, or type 'check' to run diagnostics: ").strip()
        if choice.lower() == "check":
            run_diagnostics()
            return
        url = choice if choice and choice.lower() != "check" else input("Webinar / meeting URL: ").strip()
        if not url:
            log("No URL provided. Exiting.")
            return

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    platform_name = detect_platform(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"{platform_name}_{timestamp}"
    audio_path = out_dir / f"{session_name}.wav"

    log(f"Platform detected: {platform_name}")
    log(f"Output folder:     {out_dir.resolve()}")

    recorder, backend = get_recorder(audio_path, args)
    log(f"Audio backend:     {backend}")

    try:
        recorder.start()
    except Exception as e:
        log(f"[ERROR] Could not start audio recording: {e}")
        log("Continuing without audio — the transcript will be empty. Run --check to diagnose.")
        recorder = None

    join_ok = run_bot(url, args.name, platform_name, args.duration, headless=args.headless)

    if recorder:
        recorder.stop()

    if not join_ok:
        log("[WARN] The bot may not have joined successfully — check the browser window that opened.")

    chunks = []
    if not audio_path.exists() or audio_path.stat().st_size < 1000:
        log("[WARN] No usable audio was recorded.")
    else:
        log(f"Transcribing locally with faster-whisper ({args.whisper_model})... no internet needed for this step.")
        try:
            chunks, info = transcribe(audio_path, args.whisper_model)
            log(f"Transcribed {len(chunks)} segment(s).")
        except ImportError:
            log("[ERROR] faster-whisper isn't installed. Fix: pip install faster-whisper")
        except Exception as e:
            log(f"[ERROR] Transcription failed: {e}")

    bites = None
    api_key = args.api_key or os.environ.get("OPENROUTER_API_KEY") or read_key_file()
    if args.no_summary:
        pass
    elif not chunks:
        pass
    elif not api_key:
        log("No OpenRouter key found — skipping AI summary (transcript files are still created).")
        log("Add one via --api-key, the OPENROUTER_API_KEY env var, or a file named openrouter_key.txt")
    else:
        log("Generating AI summary via OpenRouter...")
        transcript_text = "\n".join(f"[{c['timestamp']}] {c['text']}" for c in chunks if c.get("text"))
        bites = summarize_with_openrouter(transcript_text, api_key, args.model)

    meta = {
        "url": url,
        "platform": platform_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    txt_path = out_dir / f"{session_name}.txt"
    md_path = out_dir / f"{session_name}.md"
    txt_path.write_text(build_txt(chunks, meta), encoding="utf-8")
    md_path.write_text(build_md(chunks, meta, bites), encoding="utf-8")

    log("\nDone! Files saved:")
    log(f"  Transcript (.txt): {txt_path.resolve()}")
    log(f"  Transcript (.md):  {md_path.resolve()}")
    if audio_path.exists():
        log(f"  Audio (.wav):      {audio_path.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nInterrupted by user.")
    except Exception as e:
        tb = traceback.format_exc()
        Path(DEFAULT_OUTPUT_DIR).mkdir(exist_ok=True)
        err_path = Path(DEFAULT_OUTPUT_DIR) / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        try:
            err_path.write_text(tb, encoding="utf-8")
        except Exception:
            pass
        log(f"[FATAL] {e}")
        log(f"Full error details saved to: {err_path.resolve()}")
        log("Run `python webinar_agent.py --check` to verify your setup.")
        sys.exit(1)
