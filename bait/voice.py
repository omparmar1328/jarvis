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

from bait.config import ELEVENLABS_API_KEYS, ELEVENLABS_VOICE_ID


# ─────────────────────────────────────────────────────────────────────────────
# TEXT-TO-SPEECH  (ElevenLabs)
# ─────────────────────────────────────────────────────────────────────────────

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
_tts_lock = threading.Lock()  # Prevent overlapping audio playback
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
    Rotates through multiple API keys if one fails (Quota Exceeded).
    Falls back to macOS 'say' command if all ElevenLabs keys are unavailable.
    """
    global _active_play_process
    print(f"🔊 BAIT Speaking: {text}")
    
    valid_keys = [k for k in ELEVENLABS_API_KEYS if k]
    if not valid_keys:
        print("⚠️ No ElevenLabs API Keys found, using system 'say'")
        _fallback_speak(text)
        return

    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.30,
            "use_speaker_boost": True,
        },
    }
    url = ELEVENLABS_TTS_URL.format(voice_id=ELEVENLABS_VOICE_ID)

    def _play():
        global _active_play_process
        with _tts_lock:
            success = False
            for key in valid_keys:
                try:
                    headers = {
                        "xi-api-key":   key,
                        "Content-Type": "application/json",
                        "Accept":       "audio/mpeg",
                    }
                    response = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)
                    
                    if response.status_code == 200:
                        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                            for chunk in response.iter_content(chunk_size=4096):
                                tmp.write(chunk)
                            tmp_path = tmp.name
                        
                        _active_play_process = subprocess.Popen(["afplay", tmp_path])
                        _active_play_process.wait()
                        os.unlink(tmp_path)
                        success = True
                        break # Success! Exit key loop
                    elif response.status_code == 401 or response.status_code == 429:
                        print(f"🔄 ElevenLabs Quota/Key Issue ({response.status_code}) - Rotating to next key...")
                        continue # Try next key
                    else:
                        print(f"❌ ElevenLabs Error: {response.status_code}")
                        continue
                except Exception as e:
                    print(f"💥 Speak Attempt Error: {e}")
                    continue
            
            if not success:
                print("⚠️ All ElevenLabs keys failed. Falling back to system voice.")
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


def listen(timeout: int = 8, phrase_limit: int = 15) -> Optional[str]:
    """
    Listen from the microphone and return transcribed text.
    Optimized for continuous background operation with zero calibration gaps.
    """
    try:
        with sr.Microphone() as source:
            # Note: adjust_for_ambient_noise is handled once at system init now
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
        
        text = _recognizer.recognize_google(audio, language="en-IN")
        return text.strip()
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        if "recognition connection failed" in str(e).lower():
            print("⚠️ STT Connection Issue. Checking network...")
        return None

# One-time initialization for the recognizer
def init_mic():
    """Perform a one-time calibration of the microphone."""
    print("🎙  Calibrating Neural Mic...")
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=1.0)
        print("✅ Mic Calibrated.")
    except Exception as e:
        print(f"⚠️ Mic Calibration Failed: {e}")


def is_wake_word(text: str, wake_words: Optional[List[str]] = None) -> bool:
    """Check if transcribed text starts with a wake word."""
    if wake_words is None:
        wake_words = ["hey bait", "bait", "wake up"]
    
    text_lower = text.lower()
    for w in wake_words:
        if text_lower.startswith(w):
            return True
    return False

def strip_wake_word(text: str, wake_words: Optional[List[str]] = None) -> str:
    """Remove the wake word from the start of the text."""
    if wake_words is None:
        wake_words = ["hey bait", "bait", "wake up"]
    
    text_lower = text.lower()
    for w in wake_words:
        if text_lower.startswith(w):
            return text[len(w):].strip(", ").strip()
    return text.strip()
