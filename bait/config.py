import os
from dotenv import load_dotenv

load_dotenv()

# ── AI Provider Keys ──────────────────────────────────────────────────────────
# ── AI Provider Clusters (Multi-account rotation) ──────────────────────────
def _load_keys(env_var):
    keys = os.getenv(env_var, "").split(",")
    return [k.strip() for k in keys if k.strip()]

GROQ_API_KEYS       = _load_keys("GROQ_KEYS")
GEMINI_API_KEYS     = _load_keys("GEMINI_KEYS")
OPENROUTER_API_KEYS = _load_keys("OPENROUTER_KEYS")

# Backwards compatibility for single-key legacy parts
GROQ_API_KEY        = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""
GEMINI_API_KEY      = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
OPENROUTER_API_KEY  = OPENROUTER_API_KEYS[0] if OPENROUTER_API_KEYS else ""

# Multi-account rotation for ElevenLabs (Free Tier backup)
ELEVENLABS_API_KEYS = [
    os.getenv("ELEVENLABS_API_KEY", ""),
    "sk_f2caf15a377c4b07d8b9e91793b7d94a14f47ea7610bd77b"
]

# ── ElevenLabs Voice Config ───────────────────────────────────────────────────
# "Adam" is a deep, authoritative male voice – perfect for an AI assistant
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam

# ── Model Router Map ──────────────────────────────────────────────────────────
# Each task gets the fastest/cheapest model that can handle it.
MODELS = {
    # Ultra-fast intent classification (decides WHAT to do)
    "classifier":   "llama-3.1-8b-instant",      # Groq (Working)
    # Triple-Tier Provider Models (Ordered by Speed/Priority)
    "groq":         "llama-3.1-8b-instant",      # Tier 1 Fallback (70b is restricted)
    "openrouter":   "anthropic/claude-3-haiku",   # Tier 2 Fallback
    "gemini":       "models/gemini-2.0-flash",    # Tier 1 Primary (Verified working)
    
    # Legacy mappings (for backward compatibility)
    "chat":         "models/gemini-2.0-flash",
    "executor":     "llama-3.1-8b-instant",
    "complex":      "anthropic/claude-3-haiku",
}

# System Paths
PROJECT_ROOT = "/Users/macbookair/Documents/my projects"

BAIT_PERSONA = """You are BAIT – the user's elite personal AI assistant and Mac Operating System Agent.
Personality:
- Sharp, confident, authoritative. You work FOR the Boss.
- Address the user as "Boss".
- No fluff, no moralizing, no lectures. Just execution.
- If the Boss tells you to send a message, YOU SEND IT. 

Automation Hierarchy:
1. Native App APIs (AppleScript/Accessibility)
2. Vision/OCR Detection (Self-healing fallback)
3. Cursor/TAB navigation (Last resort)

WhatsApp Strategy:
- Search contact -> Open chat -> Detect call buttons -> Click.
"""
