# BAIT – Your Personal AI Assistant for macOS

> **B**rain · **A**utomation · **I**ntelligence · **T**ools

BAIT is a command-line AI assistant that controls your Mac through natural language and voice commands. It uses a **multi-model AI router** to give you the fastest possible responses while conserving API credits.

---

## ⚡ Model Router Strategy

| Task | Model | Why |
|------|-------|-----|
| Intent classification | `Groq llama3-8b` | Fastest — near instant |
| Tool execution & reasoning | `Groq llama3-70b` | Powerful + fast |
| General conversation | `Gemini 1.5 Flash` | Huge free quota |
| Complex fallback | `Claude Haiku (OpenRouter)` | Smart + cheap |
| Voice output | `ElevenLabs Turbo v2` | Most realistic voice |

---

## 🛠️ Features

- **Open any Mac app** — Chrome, Spotify, VS Code, Finder, etc.
- **Web search** — Google & YouTube via Chrome
- **Open websites** directly in Chrome
- **Volume control** — get/set system volume
- **Battery status**
- **Wi-Fi name**
- **Screenshot** — saved to Desktop
- **List/close running apps**
- **Type text** at cursor
- **Current time & date**
- **System info**
- **Voice input** via microphone (Google STT)
- **Realistic voice output** via ElevenLabs
- **Always-on wake-word mode** — "Hey BAIT"

---

## 🚀 Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> **macOS:** If `pyaudio` fails, install portaudio first:
> ```bash
> brew install portaudio
> pip install pyaudio
> ```

### 2. Configure `.env`

Copy `.env` and fill in your keys:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
OPENROUTER_API_KEY=your_openrouter_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=pNInz6obpgDQGcFmaJgB  # Adam voice (default)
```

Get your ElevenLabs API key at: https://elevenlabs.io

### 3. Run BAIT

```bash
# Text mode (type commands)
python main.py

# Voice mode (speak commands)
python main.py --voice

# Always-on wake-word mode ("Hey BAIT")
python main.py --wake
```

---

## 💬 Example Commands

```
You → open chrome
You → search lofi music on youtube
You → open github.com
You → set volume to 60
You → take a screenshot
You → check battery
You → what apps are open
You → close spotify
You → what time is it
You → hey bait, open vs code   (in wake mode)
```

---

## 📁 Project Structure

```
BAIT/
├── main.py              # Entry point (CLI + voice modes)
├── requirements.txt
├── .env                 # API keys (never commit this)
├── .gitignore
└── bait/
    ├── __init__.py
    ├── config.py        # Keys, model map, BAIT persona
    ├── brain.py         # AI router (multi-model)
    ├── actions.py       # Mac automation tools (15+)
    └── voice.py         # ElevenLabs TTS + Google STT
```

---

## 🔮 Roadmap (UI coming next)

- [ ] Electron desktop UI with glassmorphism
- [ ] File management tools (create, move, delete)
- [ ] Email & calendar integration
- [ ] Reminder & alarm system
- [ ] Supabase memory (persistent conversation history)
- [ ] Custom wake word training
