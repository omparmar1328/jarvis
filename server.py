import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import threading
from pathlib import Path
import datetime
import uuid
from typing import Optional

import bait.brain as brain_module
import bait.actions as actions_module
print(f"📍 Brain Module Path: {brain_module.__file__}")
print(f"📍 Actions Module Path: {actions_module.__file__}")

# Import the existing BAIT brain and actions
from bait.brain import BAITBrain, get_token_usage
from bait.actions import stop_all_actions, get_battery_status
from bait.voice import speak, stop_speech, listen

app = FastAPI(title="BAIT API Server")

# Allow Electron to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Local Storage Configuration
STORAGE_DIR = Path.home() / ".bait"
STORAGE_DIR.mkdir(exist_ok=True)
CHATS_FILE = STORAGE_DIR / "chats.json"

def load_local_chats():
    if not CHATS_FILE.exists():
        return []
    try:
        with open(CHATS_FILE, "r") as f:
            data = json.load(f)
            # Migration: Ensure all items are in the new format
            if isinstance(data, list) and len(data) > 0 and "messages" not in data[0]:
                return [] # Clear old flat format to prevent UI crashes
            return data
    except:
        return []

def save_local_chat(user_text, reply, conversation_id=None):
    all_chats = load_local_chats()
    
    # If no ID provided, this is a new conversation
    if not conversation_id or conversation_id == "null":
        conversation_id = str(uuid.uuid4())
        new_conv = {
            "id": conversation_id,
            "title": user_text[:30] + ("..." if len(user_text) > 30 else ""),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        all_chats.append(new_conv)
    
    # Find the conversation
    conv = next((c for c in all_chats if str(c.get("id")) == str(conversation_id)), None)
    
    if not conv:
        conversation_id = str(uuid.uuid4())
        conv = {
            "id": conversation_id,
            "title": user_text[:30] + ("..." if len(user_text) > 30 else ""),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        all_chats.append(conv)

    # Append the new message pair
    conv["messages"].append({
        "role": "user",
        "content": user_text,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })
    conv["messages"].append({
        "role": "bait",
        "content": reply,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })
    
    # Update timestamp
    conv["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(CHATS_FILE, "w") as f:
        json.dump(all_chats, f, indent=4)
    
    return conversation_id

brain = BAITBrain()
is_listening_active = False

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        reply = brain.think(request.message)
        # Save locally with grouping
        conv_id = save_local_chat(request.message, reply, request.conversation_id)
        # Speak
        threading.Thread(target=speak, args=(reply,), daemon=True).start()
        return {"reply": reply, "conversation_id": conv_id}
    except Exception as e:
        print(f"Chat Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chats")
async def get_chats():
    return load_local_chats()

@app.delete("/chats/{conversation_id}")
async def delete_chat(conversation_id: str):
    all_chats = load_local_chats()
    filtered_chats = [c for c in all_chats if str(c.get("id")) != str(conversation_id)]
    
    if len(all_chats) == len(filtered_chats):
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    with open(CHATS_FILE, "w") as f:
        json.dump(filtered_chats, f, indent=4)
    
    return {"status": "deleted", "id": conversation_id}

@app.get("/system/battery")
async def battery():
    try:
        status = get_battery_status()
        # Parse percentage from string like "100%; discharging; ..."
        percentage = "100"
        if "%" in status:
            percentage = status.split("%")[0].split("\t")[-1].split(" ")[-1]
        return {"percentage": percentage, "raw": status}
    except Exception as e:
        return {"percentage": "0", "error": str(e)}

@app.get("/tokens")
async def tokens():
    return get_token_usage()

# ── Always-on Voice Mode ───────────────────────────────────────────────────

from bait.voice import init_mic, listen

# Global state for voice loop
is_listening_active = False
voice_loop_thread = None
voice_results_queue = asyncio.Queue()

def run_voice_loop():
    """Background thread to handle continuous listening and brain routing."""
    global is_listening_active
    print("🎙  Neural sentinel: ACTIVE (Background Mode)")
    
    # One-time calibration
    init_mic()
    
    while is_listening_active:
        try:
            # Listen for 5s blocks with 15s phrase limit
            text = listen(timeout=5, phrase_limit=15)
            if text:
                print(f"👂 Heard: {text}")
                # Use a separate instance or the main brain? (Main brain for history)
                reply = brain.think(text)
                
                # Save to history (Note: This might need an ID, using 'voice-active')
                save_local_chat(text, reply, "voice-active")
                
                # Push to queue for any active SSE monitors
                asyncio.run_coroutine_threadsafe(
                    voice_results_queue.put({'user_text': text, 'reply': reply}),
                    asyncio.get_event_loop()
                )
                
                # Immediate voice feedback
                speak(reply)
        except Exception as e:
            print(f"🎙  Sentinel Warning: {e}")
        
        # Micro-sleep to prevent CPU pinning
        import time
        time.sleep(0.1)

@app.post("/voice/start")
async def voice_start():
    global is_listening_active, voice_loop_thread
    if not is_listening_active:
        is_listening_active = True
        voice_loop_thread = threading.Thread(target=run_voice_loop, daemon=True)
        voice_loop_thread.start()
    return {"status": "voice mode activated"}

@app.get("/voice/stream")
async def voice_stream(request: Request, conversation_id: Optional[str] = None):
    """Monitor the background voice loop results."""
    global is_listening_active
    
    # Ensure loop is running
    if not is_listening_active:
        await voice_start()

    async def event_generator():
        print("🎙  Voice Monitor: Connected")
        while True:
            if await request.is_disconnected():
                print("🎙  Voice Monitor: Client Disconnected (Background sentinel remains active)")
                break
            
            # Send heartbeat
            yield ": keep-alive\n\n"
            
            try:
                # Wait for data from the background thread
                data = await asyncio.wait_for(voice_results_queue.get(), timeout=2.0)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                pass
            
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/voice/stop")
async def voice_stop():
    global is_listening_active
    is_listening_active = False
    return {"status": "voice mode stopped"}

@app.post("/stop")
async def stop():
    stop_speech()
    result = stop_all_actions()
    return {"status": "stopped", "message": result}

@app.get("/debug/screen")
async def get_debug_screen():
    """Retrieve the latest self-healing screenshot."""
    path = os.path.expanduser("~/.bait/screen_context.png")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="No screenshot found")

@app.get("/status")
async def status():
    return {"status": "online", "version": "2.1.1-fixed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
