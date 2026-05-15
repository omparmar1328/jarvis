"""
actions.py – All Mac automation lives here.
Each function is a tool BAIT can call to interact with macOS.
"""

import subprocess
import webbrowser
import urllib.parse
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Any
from bait.config import PROJECT_ROOT

try:
    from AppKit import NSPasteboard, NSURL
except ImportError:
    NSPasteboard = None
    NSURL = None


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
    """Relentless Wi-Fi sensor: tries multiple system commands to find the SSID."""
    # Try 1: networksetup (Official)
    try:
        # Get active interface
        iface_out = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
        wifi_device = "en0"
        for line in iface_out.split("\n"):
            if "Wi-Fi" in line: continue
            if "Device:" in line:
                wifi_device = line.split(":")[1].strip()
                break
        
        ssid_out = subprocess.check_output(["networksetup", "-getairportnetwork", wifi_device], text=True)
        if "Current Wi-Fi Network:" in ssid_out:
            return f"📶 Connected to: {ssid_out.split(':')[1].strip()}"
    except Exception: pass

    # Try 2: ipconfig (Low-level)
    try:
        ip_out = subprocess.check_output(["ipconfig", "getsummary", "en0"], text=True)
        for line in ip_out.split("\n"):
            if " SSID :" in line:
                return f"📶 Connected to: {line.split(':')[1].strip()}"
    except Exception: pass

    # Try 3: wdutil (Modern Apple Silicon)
    try:
        wd_out = subprocess.check_output(["wdutil", "info"], text=True)
        for line in wd_out.split("\n"):
            if "SSID" in line and ":" in line:
                return f"📶 Connected to: {line.split(':')[1].strip()}"
    except Exception: pass

    # Try 4: scutil (Deep System Config)
    try:
        sc_out = subprocess.check_output(["scutil", "--nwi"], text=True)
        for line in sc_out.split("\n"):
            if "network interface: en0" in line or "network interface: en1" in line:
                pass
    except Exception: pass

    return "WiFi is active, but SSID is hidden or unreachable."


def reveal_in_finder(path: str) -> str:
    """Open Finder and highlight the specified file/folder."""
    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path):
        return f"❌ Error: Cannot reveal '{path}' because it doesn't exist."
    subprocess.run(["open", "-R", abs_path])
    return f"📂 Revealed '{os.path.basename(abs_path)}' in Finder, Boss."


def find_by_tag(tag: str) -> str:
    """Search for files matching a macOS Tag (Red, Orange, Blue, etc.)"""
    try:
        cmd = ["mdfind", f"kMDItemUserTags == '{tag.capitalize()}'"]
        result = subprocess.check_output(cmd, text=True).strip()
        if not result:
            return f"No files found with the tag '{tag}', Boss."
        
        paths = result.split("\n")
        if len(paths) == 1:
            return f"Found 1 file with tag '{tag}': {paths[0]}"
        
        return f"Found {len(paths)} files with tag '{tag}':\n- " + "\n- ".join(paths[:5])
    except Exception as e:
        return f"❌ Tag search error: {str(e)}"


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
    now = datetime.now()
    return f"🕐 It's {now.strftime('%I:%M %p on %A, %B %d, %Y')}."


def get_system_info() -> str:
    """Return basic system info."""
    result = subprocess.run(["sw_vers"], capture_output=True, text=True)
    return f"💻 System Info:\n{result.stdout.strip()}"


def capture_screen_state() -> str:
    """
    Takes a screenshot of the current screen state for 'Vision' analysis.
    This allows BAIT to 'see' what is happening in apps.
    """
    path = os.path.expanduser("~/.bait/screen_context.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["screencapture", "-x", path])
    return path


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


def get_contact_phone(name: str) -> Optional[str]:
    """
    Search macOS Contacts for a phone number matching the name.
    """
    script = f'''
    tell application "Contacts"
        try
            set thePerson to first person whose name contains "{name}"
            set thePhone to value of first phone of thePerson
            return thePhone
        on error
            return "NOT_FOUND"
        end try
    end tell
    '''
    result = _run_applescript(script).strip()
    if result == "NOT_FOUND" or not result:
        return None
    # Clean phone number (remove spaces, dashes, etc.)
    return "".join(filter(str.isdigit, result))


def send_whatsapp_message(contact: str, message: str) -> str:
    """
    Send a WhatsApp message with Ultra-Accurate Sequence.
    """
    safe_contact = contact.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    
    script = f'''
    -- Step 1: Clean Slate (Robust Restart)
    if application "WhatsApp" is running then
        tell application "WhatsApp" to quit
        repeat while application "WhatsApp" is running
            delay 0.5
        end repeat
    end if
    delay 1.0
    
    tell application "WhatsApp" to activate
    delay 7.0 -- Increased wait for full sync and UI readiness

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            
            -- Step 2: New Chat Section
            keystroke "n" using command down
            delay 2.0
            
            -- Step 3: Navigate Buffer (3x Tab)
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.5
            
            -- Step 4: Search Contact
            keystroke "{safe_contact}"
            delay 2.5
            
            -- Step 5: Select Contact (Enter, Tab, Enter)
            key code 36 -- Enter
            delay 0.8
            key code 48 -- Tab
            delay 0.8
            key code 36 -- Enter
            delay 2.0
            
            -- Step 6: Send Message
            keystroke "{safe_message}"
            delay 0.5
            key code 36 -- Enter
            
            return "SUCCESS"
        end tell
    end tell
    '''
    result = _run_applescript(script)
    if "SUCCESS" in result:
        return f"✅ WhatsApp message successfully sent to {contact}, Boss."
    return f"❌ Failed to send message."


def send_whatsapp_file(contact: str, file_path: str) -> str:
    """
    Send a file via WhatsApp using Optimized Blueprint + Clipboard Paste.
    """
    if not os.path.exists(file_path):
        return f"❌ Error: The file '{file_path}' does not exist, Boss."
        
    safe_contact = contact.replace('"', '\\"')
    abs_path = os.path.abspath(file_path)
    
    # native macOS Clipboard Injection
    try:
        from AppKit import NSPasteboard, NSURL
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        url = NSURL.fileURLWithPath_(abs_path)
        pb.writeObjects_([url])
        time.sleep(0.5)
    except Exception as e:
        return f"❌ Native Clipboard Error: {str(e)}"

    script = f'''
    -- Step 1: Clean Slate (Robust Restart)
    if application "WhatsApp" is running then
        tell application "WhatsApp" to quit
        repeat while application "WhatsApp" is running
            delay 0.5
        end repeat
    end if
    delay 1.0
    
    tell application "WhatsApp" to activate
    delay 7.0 -- Increased wait for full sync and UI readiness

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            
            -- Step 2: New Chat Section
            keystroke "n" using command down
            delay 2.0
            
            -- Step 3: Navigate Buffer (3x Tab)
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.5
            
            -- Step 4: Search Contact
            keystroke "{safe_contact}"
            delay 2.5 -- More time for search results to populate
            
            -- Step 5: Select Contact (Enter, Tab, Enter)
            key code 36 -- Enter
            delay 0.8
            key code 48 -- Tab
            delay 0.8
            key code 36 -- Enter
            delay 2.0 -- Wait for chat window to fully open
            
            -- Step 6: Paste and Send
            keystroke "v" using command down -- Paste file
            delay 4.0 -- More time for file preview to load
            key code 36 -- Enter (Confirm preview)
            delay 1.5
            key code 36 -- Enter (Final Send)
            
            return "SUCCESS"
        end tell
    end tell
    '''
    result = _run_applescript(script)
    if "SUCCESS" in result:
        return f"🚀 File '{os.path.basename(file_path)}' has been blasted over to {contact}, Boss!"
    return f"❌ Delivery Error: {result}"


def save_contact(name: str, phone: str) -> str:
    """
    Save a new contact (name and phone) to the macOS Contacts app.
    """
    # Clean phone number
    clean_phone = "".join(filter(str.isdigit, phone))
    
    script = f'''
    tell application "Contacts"
        set newPerson to make new person with properties {{first name:"{name}"}}
        make new phone at end of phones of newPerson with properties {{label:"mobile", value:"{clean_phone}"}}
        save
    end tell
    '''
    _run_applescript(script)
    
    # Force a WhatsApp open to sync
    subprocess.run(['open', '-a', 'WhatsApp'])
    time.sleep(1.0)
    
    return f"✅ Saved '{name}' with number {clean_phone} to your Contacts. You can now message them!"


def whatsapp_call(contact: str, call_type: str = "video") -> str:
    """
    WhatsApp Calling with Ultra-Accurate Sequence.
    """
    safe_contact = contact.replace('"', '\\"')
    
    script = f'''
    -- Step 1: Clean Slate (Robust Restart)
    if application "WhatsApp" is running then
        tell application "WhatsApp" to quit
        repeat while application "WhatsApp" is running
            delay 0.5
        end repeat
    end if
    delay 1.0
    
    tell application "WhatsApp" to activate
    delay 7.0 -- Increased wait for full sync and UI readiness

    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            
            -- Step 2: New Chat Section
            keystroke "n" using command down
            delay 2.0
            
            -- Step 3: Navigate Buffer (3x Tab)
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.2
            key code 48 -- Tab
            delay 0.5
            
            -- Step 4: Search Contact
            keystroke "{safe_contact}"
            delay 2.5
            
            -- Step 5: Select Contact (Enter, Tab, Enter)
            key code 36 -- Enter
            delay 0.8
            key code 48 -- Tab
            delay 0.8
            key code 36 -- Enter
            delay 2.0
            
            -- Step 6: Navigation for Call (10x Control+Tab)
            repeat 10 times
                keystroke tab using control down
                delay 0.1
            end repeat
            
            -- Step 7: Final Execution (Space click)
            key code 49 -- Space
            
            return "SUCCESS"
        end tell
    end tell
    '''
    result = _run_applescript(script)
    if "SUCCESS" in result:
        return f"📞 Initiating {call_type} call to {contact}..."
    return f"❌ Tool Error: Could not trigger the call."


def get_contact_email(name: str) -> Optional[str]:
    """Search macOS Contacts for an email matching the name."""
    script = f'''
    tell application "Contacts"
        try
            set thePerson to first person whose name contains "{name}"
            set theEmail to value of first email of thePerson
            return theEmail
        on error
            return "NOT_FOUND"
        end try
    end tell
    '''
    result = _run_applescript(script).strip()
    if result == "NOT_FOUND" or not result:
        return None
    return result


def send_email(recipient: str, subject: str, body: str, attachment_path: str = "") -> str:
    """Send an email using the macOS Mail app, with optional attachment."""
    # Check if recipient is an email address
    if "@" not in recipient:
        email = get_contact_email(recipient)
        if email:
            recipient = email
        else:
            return f"❌ Could not find an email for '{recipient}' in Contacts."

    # Escape quotes for AppleScript
    subject = subject.replace('"', '\\"')
    body = body.replace('"', '\\"')
    
    attachment_script = ""
    if attachment_path and os.path.exists(attachment_path):
        abs_path = os.path.abspath(os.path.expanduser(attachment_path))
        # Use alias for the most robust attachment method in macOS Mail
        attachment_script = f'''
        set theAttachment to (POSIX file "{abs_path}") as alias
        tell content
            make new attachment with properties {{file name:theAttachment}} at after the last paragraph
        end tell
        '''

    script = f'''
    tell application "Mail"
        activate
        set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
        tell newMessage
            make new to recipient with properties {{address:"{recipient}"}}
            {attachment_script}
            delay 2.0 -- Give the system time to anchor the file
            send
        end tell
    end tell
    '''
    _run_applescript(script)
    return f"✅ Email sent to {recipient}." + (f" with attachment: {os.path.basename(attachment_path)}" if attachment_path else "")


def stop_all_actions() -> str:
    """
    Immediately stop all ongoing automations and audio.
    """
    # Kill AppleScript runner
    subprocess.run(["pkill", "-x", "osascript"], capture_output=True)
    # Kill speech (redundant but safe)
    subprocess.run(["pkill", "-x", "afplay"], capture_output=True)
    subprocess.run(["pkill", "-x", "say"], capture_output=True)
    return "🛑 All actions stopped, Boss."


def play_youtube_video(query: str) -> str:
    """
    Search for a video on YouTube and automatically play the first result.
    """
    # Append video filter to search query
    search_youtube(query + " song")
    
    # AppleScript that uses JS to poll for the video element and click it
    script = '''
    tell application "Google Chrome"
        activate
        set found to false
        set startTime to (current date)
        
        repeat while (found is false) and ((current date) - startTime < 12)
            try
                -- Exhaustive selector for YouTube titles/thumbnails
                execute active tab of window 1 javascript "
                    var selectors = [
                        'ytd-video-renderer a#video-title', 
                        'ytd-grid-video-renderer a#video-title', 
                        'a#video-title-link', 
                        '#video-title',
                        'ytd-thumbnail a'
                    ];
                    var clicked = false;
                    for (var sel of selectors) {
                        var el = document.querySelector(sel);
                        if (el && el.offsetHeight > 0) {
                            el.click();
                            clicked = true;
                            break;
                        }
                    }
                    clicked;
                "
                if result is "true" then
                    set found to true
                end if
            end try
            if found is false then delay 0.8
        end repeat
    end tell
    '''
    _run_applescript(script)
    return f"🚀 Finding and playing '{query}' on YouTube for you, Boss!"


def click_ui_element(app_name: str, element_name: str, role: str = "button") -> str:
    """
    Combines UI Scripting and Coordinate clicking. 
    Finds an element in an app (like a button or menu) and clicks its exact center.
    """
    process_map = {
        "chrome": "Google Chrome",
        "vscode": "Code",
        "whatsapp": "WhatsApp",
        "spotify": "Spotify",
        "mail": "Mail",
    }
    process_name = process_map.get(app_name.lower().strip(), app_name)

    script = f'''
    activate application "{process_name}"
    tell application "System Events"
        tell process "{process_name}"
            try
                set theElement to (first {role} whose name contains "{element_name}")
                set {{x, y}} to position of theElement
                set {{w, h}} to size of theElement
                set clickX to x + (w / 2)
                set clickY to y + (h / 2)
                click at {{clickX, clickY}}
                return "SUCCESS"
            on error err
                return "Could not find " & "{element_name}" & " as a " & "{role}" & ". Error: " & err
            end try
        end tell
    end tell
    '''
    result = _run_applescript(script)
    if "SUCCESS" in result:
        return f"✅ Smart-clicked '{element_name}' in {process_name}."
    else:
        return f"❌ {result}"


def list_files(directory: str = "PROJECT_ROOT") -> str:
    """
    List files in a directory. Defaults to the user's 'my projects' folder.
    """
    # Smart path resolution
    if directory == "PROJECT_ROOT":
        path = PROJECT_ROOT
    else:
        path = os.path.expanduser(directory)
        # If path doesn't exist, try looking inside PROJECT_ROOT
        if not os.path.exists(path):
            path = os.path.join(PROJECT_ROOT, directory.replace("~/", ""))

    if not os.path.exists(path):
        return f"❌ Folder '{directory}' not found, Boss. I checked the Desktop and My Projects."
    
    try:
        files = os.listdir(path)
        visible_files = [f for f in files if not f.startswith(".")]
        if not visible_files:
            return f"Empty folder: '{directory}' is clean, Boss."
        
        return f"📁 Files in {os.path.basename(path)}:\n- " + "\n- ".join(visible_files[:20])
    except Exception as e:
        return f"❌ Error reading folder: {str(e)}"


def get_latest_file(directory: str = "PROJECT_ROOT") -> str:
    """
    Find the most recently created/modified file in a folder.
    Perfect for 'Send the latest screenshot'.
    """
    path = PROJECT_ROOT if directory == "PROJECT_ROOT" else os.path.expanduser(directory)
    
    if not os.path.exists(path):
        return f"❌ Folder '{directory}' not found."
    
    try:
        files = [os.path.join(path, f) for f in os.listdir(path) if not f.startswith(".")]
        if not files:
            return f"No files found in {directory}, Boss."
        
        latest_file = max(files, key=os.path.getmtime)
        return f"Found latest file: {latest_file}"
    except Exception as e:
        return f"❌ Error tracking latest file: {str(e)}"


def find_file(query: str, directory: str = "PROJECT_ROOT") -> str:
    """
    Search for a file by name (partial match) in a folder.
    """
    path = PROJECT_ROOT if directory == "PROJECT_ROOT" else os.path.expanduser(directory)
    
    if not os.path.exists(path):
        return f"❌ Folder '{directory}' not found."
    
    try:
        query = query.lower()
        matches = []
        for f in os.listdir(path):
            if query in f.lower() and not f.startswith("."):
                matches.append(os.path.join(path, f))
        
        if not matches:
            return f"No file matching '{query}' found in {directory}, Boss."
        
        if len(matches) == 1:
            return f"Found file: {matches[0]}"
        
        return f"Multiple matches found:\n- " + "\n- ".join([os.path.basename(m) for m in matches[:5]])
    except Exception as e:
        return f"❌ Error searching for file: {str(e)}"


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
    "whatsapp_send_file": send_whatsapp_file,
    "whatsapp_call":     whatsapp_call,
    "save_contact":      save_contact,
    "send_email":        send_email,
    "click_ui":          click_ui_element,
    "see_screen":        capture_screen_state,
    "list_files":        list_files,
    "get_latest_file":   get_latest_file,
    "find_file":         find_file,
    "find_by_tag":       find_by_tag,
    "reveal_in_finder":  reveal_in_finder,
    "play_youtube":      play_youtube_video,
    "stop_actions":      stop_all_actions,
}

TOOL_DESCRIPTIONS = """
Available tools (JSON only):
- open_application(app_name)       → Open a Mac app (Chrome, Spotify, VS Code, etc.)
- search_google(query)             → Search Google in Chrome
- search_youtube(query)            → Search YouTube in Chrome
- play_youtube(query)             → Search AND automatically play the first video on YouTube
- stop_actions()                   → Immediately stop all ongoing automations or speech (use for "Stop!", "Interrupt", "Shut up")
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
- whatsapp_send_file(contact, file_path) → Send a file from your Mac to a WhatsApp contact.
- whatsapp_call(contact, call_type) → Start a WhatsApp call.
- send_email(recipient, subject, body, attachment_path) → Send an email with an optional file attachment.
- click_ui(app_name, element_name, role) → Smart Click: Finds a UI element and clicks its coordinates.
- see_screen() → Vision: Captures the current screen so BAIT can analyze what is happening.
- list_files(directory) → Lists files in a folder so you can see what to send.
- get_latest_file(directory) → Finds the most recent file.
- find_file(query, directory) → Searches for a file by name.
- find_by_tag(tag) → Finds files by macOS Tag (Red, Orange, Blue, etc.).
- reveal_in_finder(path) → Opens Finder and highlights the file.
- save_contact(name, phone) → Save a new contact with their mobile number to the Mac Contacts app.

Note: Always prioritize 'play_youtube' if the user asks to play a song or video.
Note: Always prioritize 'open_application' for native Mac apps (like Crunchyroll, Spotify, VS Code).

If a task needs tools, respond with valid JSON objects. You may output MULTIPLE JSON objects in a sequence if the task requires multiple steps (e.g., open Chrome, then search YouTube).
Format: {"tool": "tool_name", "args": {"param1": "value1"}}

If no tool is needed (conversation/question), respond normally as BAIT.
"""
