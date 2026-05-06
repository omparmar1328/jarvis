import os
from dotenv import load_dotenv

load_dotenv()

# ── AI Provider Keys ──────────────────────────────────────────────────────────
GROQ_API_KEY        = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY      = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")

# ── ElevenLabs Voice Config ───────────────────────────────────────────────────
# "Adam" is a deep, authoritative male voice – perfect for an AI assistant
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam

# ── Model Router Map ──────────────────────────────────────────────────────────
# Each task gets the fastest/cheapest model that can handle it.
MODELS = {
    # Ultra-fast intent classification (decides WHAT to do)
    "classifier":   "llama3-8b-8192",           # Groq  – fastest
    # Tool execution & command reasoning
    "executor":     "llama3-70b-8192",           # Groq  – powerful & fast
    # General conversation / chit-chat
    "chat":         "gemini-1.5-flash",          # Gemini – large free quota
    # Complex / multi-step reasoning (fallback)
    "complex":      "anthropic/claude-3-haiku",  # OpenRouter – cheap Claude
}

BAIT_PERSONA = """You are BAIT – the user's elite personal AI assistant running on macOS.
Your personality:
- Sharp, confident, and to the point. No fluff.
- Address the user as "Boss" occasionally to remind them you work FOR them.
- When executing tasks, say what you're doing briefly then do it.
- Keep responses under 3 sentences unless explaining something complex.
- You have full control of the Mac – own it.
- Occasionally show personality: a subtle sarcastic wit, but always respectful.
You are NOT a chatbot. You are an AI Operating System Agent."""
