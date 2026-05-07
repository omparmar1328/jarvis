import os
import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import threading

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

brain = BAITBrain()
is_listening_active = False

class ChatRequest(BaseModel):
    message: str
    user_id: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        reply = brain.think(request.message)
        threading.Thread(target=speak, args=(reply,), daemon=True).start()
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voice/stream")
async def voice_stream(request: Request):
    """
    Server-Sent Events endpoint that keeps listening and pushes recognized 
    text/replies to the GUI in real-time.
    """
    global is_listening_active
    is_listening_active = True

    async def event_generator():
        global is_listening_active
        print("🎙  Always-on Voice Mode: ACTIVE")
        
        while is_listening_active:
            # Check if client disconnected
            if await request.is_disconnected():
                print("🎙  Always-on Voice Mode: DISCONNECTED")
                break
            
            # Listen for a command
            # Using a slightly shorter timeout for responsiveness in loop
            text = listen(timeout=5, phrase_limit=10)
            
            if text:
                print(f"👂 Heard: {text}")
                reply = brain.think(text)
                
                # Push the data to the GUI
                yield f"data: {json.dumps({'user_text': text, 'reply': reply})}\n\n"
                
                # Speak the reply
                speak(reply) # Blocking here prevents it from hearing itself
            
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
    return {"status": "online", "version": "1.1.0-always-on"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
