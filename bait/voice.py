"""
voice.py – Voice I/O for BAIT.

STT  : SpeechRecognition (Google free API)
TTS  : ElevenLabs (most realistic voice)
"""

import os
import io
import tempfile
import threading
import subprocess
from typing import Optional, List

import speech_recognition as sr
import requests

from bait.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID


# ─────────────────────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH  (ElevenLabs)
# ─────────────────────────────────────────────────────────────────────────────

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

_active_play_process = None

def stop_speech():
    """Immediately stop any ongoing ElevenLabs/say playback."""
    global _active_play_process
    if _active_play_process:
        try:
            _active_play_process.terminate()
            _active_play_process = None
        except Exception:
            pass
    # Also kill any lingering afplay/say processes just in case
    subprocess.run(["pkill", "-x", "afplay"], capture_output=True)
    subprocess.run(["pkill", "-x", "say"], capture_output=True)

def speak(text: str, blocking: bool = True) -> None:
    """
    Convert text to speech using ElevenLabs and play it.
    Falls back to macOS 'say' command if ElevenLabs is unavailable.
    """
    global _active_play_process
    
    if not ELEVENLABS_API_KEY:
        _fallback_speak(text)
        return

    headers = {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept":       "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",   # Fastest ElevenLabs model
        "voice_settings": {
            "stability":        0.50,
            "similarity_boost": 0.85,
            "style":            0.30,
            "use_speaker_boost": True,
        },
    }

    url = ELEVENLABS_TTS_URL.format(voice_id=ELEVENLABS_VOICE_ID)

    def _play():
        global _active_play_process
        with _tts_lock:
            try:
                response = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)
                if response.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        for chunk in response.iter_content(chunk_size=4096):
                            tmp.write(chunk)
                        tmp_path = tmp.name
                    
                    _active_play_process = subprocess.Popen(["afplay", tmp_path])
                    _active_play_process.wait()
                    os.unlink(tmp_path)
                else:
                    _fallback_speak(text)
            except Exception:
                _fallback_speak(text)

    if blocking:
        _play()
    else:
        threading.Thread(target=_play, daemon=True).start()


def _fallback_speak(text: str) -> None:
    """Use macOS built-in 'say' command as TTS fallback."""
    # Samantha is the best built-in macOS voice
    subprocess.run(["say", "-v", "Samantha", "-r", "185", text])


# ─────────────────────────────────────────────────────────────────────────────
# SPEECH-TO-TEXT  (Microphone → Google STT)
# ─────────────────────────────────────────────────────────────────────────────

_recognizer = sr.Recognizer()
_recognizer.energy_threshold = 300       # Sensitivity
_recognizer.dynamic_energy_threshold = True
_recognizer.pause_threshold = 0.8        # Seconds of silence to end phrase


def listen(timeout: int = 8, phrase_limit: int = 12) -> Optional[str]:
    """
    Listen from the microphone and return transcribed text.
    Returns None if nothing was heard or recognition failed.
    """
    with sr.Microphone() as source:
        # Brief ambient noise adjustment on first call
        _recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None

    try:
        text = _recognizer.recognize_google(audio, language="en-IN")
        return text.strip()
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        # Google STT unreachable – try offline Sphinx if available
        try:
            return _recognizer.recognize_sphinx(audio)
        except Exception:
            return None


def is_wake_word(text: str, wake_words: Optional[List[str]] = None) -> bool:
    """Check if transcribed text starts with a wake word."""
    if wake_words is None:
        wake_words = ["hey bait", "bait", "ok bait", "okay bait"]
    text_lower = text.lower().strip()
    return any(text_lower.startswith(w) for w in wake_words)


def strip_wake_word(text: str, wake_words: Optional[List[str]] = None) -> str:
    """Remove the wake word prefix from the command."""
    if wake_words is None:
        wake_words = ["hey bait", "okay bait", "ok bait", "bait"]
    text_lower = text.lower().strip()
    for w in sorted(wake_words, key=len, reverse=True):
        if text_lower.startswith(w):
            return text[len(w):].strip(" ,.")
    return text
