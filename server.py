import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import threading
from pathlib import Path
import datetime
import uuid
from typing import Optional

# Import the existing BAIT brain and actions
from bait.brain import BAITBrain
from bait.actions import stop_all_actions
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

@app.get("/voice/stream")
async def voice_stream(request: Request, conversation_id: Optional[str] = None):
    global is_listening_active
    is_listening_active = True

    async def event_generator():
        global is_listening_active
        curr_id = conversation_id
        print("🎙  Local Always-on Voice Mode: ACTIVE")
        while is_listening_active:
            if await request.is_disconnected():
                break
            
            text = listen(timeout=5, phrase_limit=10)
            if text:
                print(f"👂 Heard: {text}")
                reply = brain.think(text)
                curr_id = save_local_chat(text, reply, curr_id)
                yield f"data: {json.dumps({'user_text': text, 'reply': reply, 'conversation_id': curr_id})}\n\n"
                speak(reply)
            await asyncio.sleep(0.1)

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

@app.get("/status")
async def status():
    return {"status": "online", "version": "2.0.2-robust-chats"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
