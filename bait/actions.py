"""
actions.py – All Mac automation lives here.
Each function is a tool BAIT can call to interact with macOS.
"""

import subprocess
import webbrowser
import urllib.parse
import os
import time


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _run_applescript(script: str) -> str:
    """Run an AppleScript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def _open_url_in_chrome(url: str) -> str:
    """Open a URL specifically in Google Chrome."""
    script = f'''
    tell application "Google Chrome"
        activate
        if (count of windows) = 0 then
            make new window
        end if
        set URL of active tab of front window to "{url}"
    end tell
    '''
    _run_applescript(script)
    return f"Opened in Chrome: {url}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def open_application(app_name: str) -> str:
    """Open a macOS application by name with intelligent fallbacks."""
    app_lower = app_name.lower().strip()
    
    # 1. App Aliases
    aliases = {
        "chrome":        "Google Chrome",
        "google chrome": "Google Chrome",
        "safari":        "Safari",
        "firefox":       "Firefox",
        "vscode":        "Visual Studio Code",
        "vs code":       "Visual Studio Code",
        "terminal":      "Terminal",
        "finder":        "Finder",
        "music":         "Music",
        "spotify":       "Spotify",
        "slack":         "Slack",
        "zoom":          "Zoom",
        "notes":         "Notes",
        "calendar":      "Calendar",
        "mail":          "Mail",
        "messages":      "Messages",
        "facetime":      "FaceTime",
        "photos":        "Photos",
        "whatsapp":      "WhatsApp",
        "telegram":      "Telegram",
        "discord":       "Discord",
        "xcode":         "Xcode",
        "word":          "Microsoft Word",
        "excel":         "Microsoft Excel",
        "powerpoint":    "Microsoft PowerPoint",
        "crunchyroll":   "Crunchyroll",
        "netflix":       "Netflix",
    }
    
    # 2. Web Redirects (Avoid Spotlight for known web services if app fails)
    web_services = {
        "youtube": "https://www.youtube.com",
        "netflix": "https://www.netflix.com",
        "crunchyroll": "https://www.crunchyroll.com",
        "chatgpt": "https://chatgpt.com",
        "gemini": "https://gemini.google.com",
    }

    resolved = aliases.get(app_lower, app_name)
    
    # Step 1: Try direct 'open' command
    result = subprocess.run(["open", "-a", resolved], capture_output=True, text=True)
    if result.returncode == 0:
        return f"✅ Opened {resolved}."
    
    # Step 2: If direct open fails, check if it's a known web service
    if app_lower in web_services:
        return open_website(web_services[app_lower])

    # Step 3: Final fallback: Spotlight search + 'Return' key
    _run_applescript('tell application "System Events" to keystroke space using command down')
    time.sleep(0.4)
    _run_applescript(f'tell application "System Events" to keystroke "{resolved}"')
    time.sleep(0.6)
    _run_applescript('tell application "System Events" to key code 36') # 36 is Return
    return f"⚠️ Tried to open '{resolved}' via Spotlight. (Direct launch failed.)"


def search_google(query: str) -> str:
    """Search Google in Chrome."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}"
    return _open_url_in_chrome(url)


def search_youtube(query: str) -> str:
    """Search YouTube in Chrome."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    return _open_url_in_chrome(url)


def open_website(url: str) -> str:
    """Open any URL in Chrome."""
    if not url.startswith("http"):
        url = "https://" + url
    return _open_url_in_chrome(url)


def search_chrome(query: str, platform: str = "google") -> str:
    """Smart dispatcher: searches the right platform based on intent."""
    platform = platform.lower().strip()
    if platform in ("youtube", "yt"):
        return search_youtube(query)
    elif platform in ("google", "web", "search"):
        return search_google(query)
    else:
        # Try as a direct URL
        return open_website(platform)


def get_battery_status() -> str:
    """Return Mac battery percentage."""
    result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    for line in lines:
        if "%" in line:
            return f"🔋 {line.strip()}"
    return "Could not read battery status."


def get_volume() -> str:
    """Get current system volume."""
    script = "output volume of (get volume settings)"
    vol = _run_applescript(script)
    return f"🔊 Volume is at {vol}%."


def set_volume(level: int) -> str:
    """Set system volume (0–100)."""
    level = max(0, min(100, int(level)))
    _run_applescript(f"set volume output volume {level}")
    return f"🔊 Volume set to {level}%."


def take_screenshot() -> str:
    """Take a screenshot and save to Desktop."""
    path = os.path.expanduser("~/Desktop/bait_screenshot.png")
    subprocess.run(["screencapture", "-x", path])
    return f"📸 Screenshot saved to Desktop as bait_screenshot.png."


def get_wifi_name() -> str:
    """Return current Wi-Fi network name."""
    result = subprocess.run(
        ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
        capture_output=True, text=True
    )
    for line in result.stdout.split("\n"):
        if " SSID:" in line:
            return f"📶 Connected to: {line.split(':')[1].strip()}"
    return "Not connected to Wi-Fi or couldn't detect."


def type_text(text: str) -> str:
    """Type text at the current cursor position using AppleScript."""
    safe_text = text.replace('"', '\\"')
    _run_applescript(f'tell application "System Events" to keystroke "{safe_text}"')
    return f"⌨️ Typed: {text}"


def press_key(key: str) -> str:
    """Press a keyboard key (e.g. 'return', 'escape', 'tab')."""
    _run_applescript(f'tell application "System Events" to key code "{key}"')
    return f"⌨️ Pressed: {key}"


def close_application(app_name: str) -> str:
    """Quit a macOS application."""
    aliases = {
        "chrome": "Google Chrome",
        "vscode": "Visual Studio Code",
    }
    resolved = aliases.get(app_name.lower().strip(), app_name)
    _run_applescript(f'tell application "{resolved}" to quit')
    return f"✅ Closed {resolved}."


def list_running_apps() -> str:
    """List all currently running applications."""
    script = 'tell application "System Events" to get name of every application process whose background only is false'
    result = _run_applescript(script)
    apps = [a.strip() for a in result.split(",")]
    return "🖥️ Running apps: " + ", ".join(apps)


def get_current_time() -> str:
    """Return current date and time."""
    from datetime import datetime
    now = datetime.now()
    return f"🕐 It's {now.strftime('%I:%M %p on %A, %B %d, %Y')}."


def get_system_info() -> str:
    """Return basic system info."""
    result = subprocess.run(["sw_vers"], capture_output=True, text=True)
    return f"💻 System Info:\n{result.stdout.strip()}"


def manage_chrome_tab(action: str, value: str = "") -> str:
    """
    Control the active tab in Google Chrome.
    Actions: 'search_youtube', 'search_google', 'open_url', 'refresh', 'close', 'back', 'forward'
    """
    action = action.lower().strip()
    
    if action == "search_youtube":
        encoded = urllib.parse.quote(value)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        script = f'tell application "Google Chrome" to set URL of active tab of front window to "{url}"'
        _run_applescript(script)
        return f"Searching YouTube in current tab: {value}"
        
    elif action == "search_google":
        encoded = urllib.parse.quote(value)
        url = f"https://www.google.com/search?q={encoded}"
        script = f'tell application "Google Chrome" to set URL of active tab of front window to "{url}"'
        _run_applescript(script)
        return f"Searching Google in current tab: {value}"

    elif action == "open_url":
        url = value if value.startswith("http") else "https://" + value
        script = f'tell application "Google Chrome" to set URL of active tab of front window to "{url}"'
        _run_applescript(script)
        return f"Opened {url} in current tab."

    elif action == "refresh":
        _run_applescript('tell application "Google Chrome" to reload active tab of front window')
        return "Refreshed current tab."

    elif action == "close":
        _run_applescript('tell application "Google Chrome" to close active tab of front window')
        return "Closed current tab."

    elif action == "back":
        _run_applescript('tell application "Google Chrome" to go back active tab of front window')
        return "Went back."

    elif action == "forward":
        _run_applescript('tell application "Google Chrome" to go forward active tab of front window')
        return "Went forward."

    return f"Unknown action: {action}"


def send_whatsapp_message(contact: str, message: str) -> str:
    """
    Send a WhatsApp message to a contact using the native macOS app.
    Uses the main search bar (Cmd+F) for better reliability.
    """
    # Escaping quotes for AppleScript
    safe_contact = contact.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    
    script = f'''
    tell application "WhatsApp"
        activate
        reopen
    end tell
    delay 2.0
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            delay 1.0
            keystroke "n" using command down -- New chat modal
            delay 1.5
            keystroke "{safe_contact}"
            delay 2.0
            key code 36 -- Return to select contact
            delay 1.5
            keystroke "{safe_message}"
            delay 1.0
            key code 36 -- Return to send
        end tell
    end tell
    '''
    _run_applescript(script)
    return f"✅ WhatsApp message sent to {safe_contact}: '{safe_message}'"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL REGISTRY  (used by brain.py to tell the LLM what tools exist)
# ─────────────────────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "open_application":  open_application,
    "search_google":     search_google,
    "search_youtube":    search_youtube,
    "open_website":      open_website,
    "search_chrome":     search_chrome,
    "get_battery":       get_battery_status,
    "get_volume":        get_volume,
    "set_volume":        set_volume,
    "take_screenshot":   take_screenshot,
    "get_wifi":          get_wifi_name,
    "type_text":         type_text,
    "close_application": close_application,
    "list_running_apps": list_running_apps,
    "get_time":          get_current_time,
    "get_system_info":   get_system_info,
    "manage_chrome_tab": manage_chrome_tab,
    "send_whatsapp":     send_whatsapp_message,
}

TOOL_DESCRIPTIONS = """
Available tools (you can call ONE per response, JSON only):
- open_application(app_name)       → Open a Mac app (Chrome, Spotify, VS Code, etc.)
- search_google(query)             → Search Google in Chrome
- search_youtube(query)            → Search YouTube in Chrome
- open_website(url)                → Open any URL in Chrome
- search_chrome(query, platform)   → Smart search: platform = "google" | "youtube" | any URL
- get_battery()                    → Check battery level
- get_volume()                     → Check current volume
- set_volume(level)                → Set volume 0–100
- take_screenshot()                → Screenshot to Desktop
- get_wifi()                       → Current Wi-Fi name
- type_text(text)                  → Type text at cursor
- close_application(app_name)      → Quit an app
- list_running_apps()              → List all open apps
- get_time()                       → Current date & time
- get_system_info()                → macOS version info
- manage_chrome_tab(action, value) → Control CURRENT Chrome tab. Actions: 'search_youtube', 'search_google', 'open_url', 'refresh', 'close', 'back', 'forward'. Use 'value' for searches/URLs.
- send_whatsapp(contact, message)  → Send message to contact on WhatsApp app.

Note: Always prioritize 'open_application' for native Mac apps (like Crunchyroll, Spotify, VS Code) if the user implies they have the app installed.

If a task needs a tool, respond ONLY with valid JSON in this exact format:
{"tool": "tool_name", "args": {"param1": "value1"}}

If no tool is needed (conversation/question), respond normally as BAIT.
"""
