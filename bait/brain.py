"""
brain.py – The AI model router for BAIT.

Model strategy:
  - CLASSIFIER  : Groq llama3-8b  → Ultra-fast intent detection
  - EXECUTOR    : Groq llama3-70b → Tool call reasoning & command execution
  - CHAT        : Gemini Flash     → General conversation (huge free quota)
  - COMPLEX     : OpenRouter Claude Haiku → Fallback for hard tasks
"""

import json
import re
from typing import Optional, List
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
import time
from bait.config import (
    GROQ_API_KEYS, GEMINI_API_KEYS, OPENROUTER_API_KEYS,
    MODELS, BAIT_PERSONA
)
from bait.actions import TOOL_REGISTRY, TOOL_DESCRIPTIONS, capture_screen_state

# ── Key Rotation & Cooldown Management ──────────────────────────────────────
class KeyManager:
    def __init__(self, provider: str, keys: list):
        self.provider = provider
        self.keys = keys
        self.current_idx = 0
        self.cooldowns = {k: 0 for k in keys}  # timestamp when key is usable again
        self.exhausted_until = 0

    def get_active_key(self):
        """Find the next available key that isn't in cooldown."""
        now = time.time()
        for _ in range(len(self.keys)):
            key = self.keys[self.current_idx]
            if now >= self.cooldowns[key]:
                return key
            self.current_idx = (self.current_idx + 1) % len(self.keys)
        return None

    def mark_failed(self, key: str, reason: str = "Unknown", retry_after_mins: int = 10):
        """Mark a key as exhausted/quota-limited (Default 10 mins)."""
        print(f"🛑 [Rotation] Key {key[:8]}... sidelined. Reason: {reason}. Cooldown: {retry_after_mins}m")
        self.cooldowns[key] = time.time() + (retry_after_mins * 60)
        # Check if entire cluster is now exhausted
        if not self.get_active_key():
            self.exhausted_until = min(self.cooldowns.values())

    def get_earliest_refill_time(self):
        """Returns minutes until the first key in this cluster refills."""
        now = time.time()
        wait_times = [max(0, (ts - now) / 60) for ts in self.cooldowns.values()]
        return int(min(wait_times)) if wait_times else 0

# Initialize Cluster Managers
GEMINI_CLUSTER = KeyManager("gemini", GEMINI_API_KEYS)
GROQ_CLUSTER   = KeyManager("groq", GROQ_API_KEYS)
OR_CLUSTER     = KeyManager("openrouter", OPENROUTER_API_KEYS)

# ── Client initialization ──────────────────────────────────────────────────
_groq_client = None
_openrouter_client = None

def _get_groq():
    key = GROQ_CLUSTER.get_active_key()
    if not key: return None
    return Groq(api_key=key)

def _get_openrouter():
    key = OR_CLUSTER.get_active_key()
    if not key: return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key,
    )

def _init_gemini(key: str):
    """Re-configure Gemini with a specific key."""
    if not key: return False
    genai.configure(api_key=key)
    return True


# ── Token Tracking ────────────────────────────────────────────────────────
TOKEN_USAGE = {
    "groq": {"prompt": 0, "completion": 0},
    "gemini": {"prompt": 0, "completion": 0},
    "openrouter": {"prompt": 0, "completion": 0}
}

def get_token_usage():
    return TOKEN_USAGE

def _update_tokens(provider: str, prompt: int, completion: int):
    TOKEN_USAGE[provider]["prompt"] += prompt
    TOKEN_USAGE[provider]["completion"] += completion

def _call_groq(model: str, messages: list, temperature: float = 0.4) -> str:
    """Call Groq with cluster rotation."""
    while True:
        key = GROQ_CLUSTER.get_active_key()
        if not key: raise Exception("GROQ_EXHAUSTED")
        
        try:
            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=512,
            )
            if hasattr(response, 'usage'):
                _update_tokens("groq", response.usage.prompt_tokens, response.usage.completion_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️ Groq Key {key[:8]}... exhausted. Rotating...")
                GROQ_CLUSTER.mark_failed(key, reason=str(e))
                continue
            raise e

def _call_gemini(prompt: str, temperature: float = 0.5) -> str:
    """Call Gemini with cluster rotation."""
    while True:
        key = GEMINI_CLUSTER.get_active_key()
        if not key: raise Exception("GEMINI_EXHAUSTED")
        
        try:
            _init_gemini(key)
            # Try multiple model identifiers per key (Verified IDs from scan)
            models_to_try = [
                MODELS["gemini"], 
                "models/gemini-2.0-flash", 
                "models/gemini-pro-latest", 
                "models/gemini-flash-latest"
            ]
            
            for m_name in models_to_try:
                try:
                    model = genai.GenerativeModel(
                        model_name=m_name,
                        generation_config={"temperature": temperature, "max_output_tokens": 1000},
                        system_instruction=BAIT_PERSONA,
                    )
                    response = model.generate_content(prompt)
                    try:
                        usage = response.usage_metadata
                        _update_tokens("gemini", usage.prompt_token_count, usage.candidates_token_count)
                    except: pass
                    return response.text.strip()
                except Exception as e:
                    if "quota" in str(e).lower() or "429" in str(e):
                        raise e # Trigger key rotation
                    print(f"⚠️ Gemini {m_name} failed on key {key[:8]}... Trying next model identifier.")
                    continue
            raise Exception("MODEL_ID_FAILURE")
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️ Gemini Key {key[:8]}... exhausted. Rotating...")
                GEMINI_CLUSTER.mark_failed(key, reason=str(e))
                continue
            raise e

def _call_openrouter(messages: list, temperature: float = 0.4) -> str:
    """Call OpenRouter with cluster rotation."""
    while True:
        key = OR_CLUSTER.get_active_key()
        if not key: raise Exception("OR_EXHAUSTED")
        
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
            response = client.chat.completions.create(
                model=MODELS["complex"],
                messages=messages,
                temperature=temperature,
                max_tokens=600,
            )
            if hasattr(response, 'usage'):
                _update_tokens("openrouter", response.usage.prompt_tokens, response.usage.completion_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                print(f"⚠️ OR Key {key[:8]}... exhausted. Rotating...")
                OR_CLUSTER.mark_failed(key, reason=str(e))
                continue
            raise e

def _call_vision(prompt: str, image_path: str) -> str:
    """Analyze a screenshot using Gemini Flash Vision."""
    _init_gemini()
    from PIL import Image
    model = genai.GenerativeModel(model_name=MODELS["chat"])
    img = Image.open(image_path)
    response = model.generate_content([prompt, img])
    
    # Track tokens
    try:
        usage = response.usage_metadata
        _update_tokens("gemini", usage.prompt_token_count, usage.candidates_token_count)
    except:
        pass

    return response.text.strip()


# ── Intent Classifier ──────────────────────────────────────────────────────

INTENT_PROMPT = """You are a highly accurate command intent classifier for a Mac AI assistant named BAIT.
Classify the user message as ONE of these two categories:

1. "action" → The user wants to PERFORM A TASK or CONTROL the system. 
   Examples: 
   - "open chrome"
   - "search for cats on youtube"
   - "set volume to 50"
   - "tell me the time"
   - "take a screenshot"
   - "type 'hello world'"
   - "quit slack"
   - "what is my battery level?"
   - "send a whatsapp message to Mom"
   - "play some music"

2. "chat" → The user is just talking, asking a general question, or greeting you.
   Examples:
   - "hello"
   - "who are you?"
   - "who is the prime minister of india?"
   - "tell me a joke"
   - "what is the capital of france?"
   - "how is the weather?" (if no weather tool is listed)
   - "thank you"

Respond with ONLY one word: action OR chat"""

def classify_intent(user_message: str) -> str:
    """Classify intent using cluster priority (Gemini -> Groq)."""
    messages = [
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    
    # Try Gemini Cluster first (for intent classification too, to squeeze limits)
    try:
        result = _call_gemini(f"{INTENT_PROMPT}\n\nUser: {user_message}", temperature=0.0)
    except:
        # Fallback to Groq Cluster
        try:
            result = _call_groq(MODELS["classifier"], messages, temperature=0.0)
        except:
            return "chat" # Default to chat if everything fails
            
    return "action" if "action" in result.lower() else "chat"


# ── Tool Parser ────────────────────────────────────────────────────────────

def _extract_all_json(text: str) -> List[dict]:
    """Extract all JSON objects from a response string, even if they are concatenated."""
    text = text.strip()
    
    # Remove markdown code blocks if present
    if "```" in text:
        # Match content inside ```json ... ``` or just ``` ... ```
        blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if blocks:
            text = " ".join(blocks)
    
    results = []
    decoder = json.JSONDecoder()
    pos = 0
    while pos < len(text):
        # Skip leading whitespace or characters until we find a {
        match = re.search(r'\{', text[pos:])
        if not match:
            break
        
        start_index = pos + match.start()
        try:
            obj, end_index = decoder.raw_decode(text[start_index:])
            results.append(obj)
            pos = start_index + end_index
        except json.JSONDecodeError:
            # If decode fails at this {, move past it and try again
            pos = start_index + 1
    
    return results


def _execute_tool_call(tool_name: str, args: dict) -> str:
    """Look up and execute a tool from the registry."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return f"⚠️ Unknown tool: {tool_name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"⚠️ Tool '{tool_name}' failed: {e}"


# ── Main Brain ─────────────────────────────────────────────────────────────

class BAITBrain:
    """
    Routes each user message to the right model and executes tools if needed.
    Conversation history is kept in-memory for context.
    """

    def __init__(self):
        self.history: List[dict] = []
        self.system_prompt = BAIT_PERSONA + "\n\n" + TOOL_DESCRIPTIONS

    def _build_executor_messages(self, user_message: str) -> List[dict]:
        """Build message list for the executor model."""
        messages = [{"role": "system", "content": self.system_prompt}]
        # Include last 6 turns for context (keep it lean for speed)
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": user_message})
        return messages

    def think(self, user_message: str) -> str:
        """
        Multi-Cluster Priority Routing (Gemini Squeeze -> Groq -> OR Fallback).
        """
        try:
            intent = classify_intent(user_message)
            is_action = (intent == "action")

            # ── BUILD PROMPTS ──
            action_prompt = f"{self.system_prompt}\n\nUser: {user_message}\n\nRespond only in JSON."
            history_text = ""
            for turn in self.history[-4:]:
                role = "Assistant" if turn["role"] == "assistant" else "User"
                history_text += f"{role}: {turn['content']}\n"
            chat_prompt = f"Previous Context:\n{history_text}\n\nUser Message: {user_message}"

            # ── CLUSTER ROTATION EXECUTION ──
            raw_response = ""
            providers_to_try = ["gemini", "groq", "openrouter"]
            
            for provider in providers_to_try:
                try:
                    if provider == "gemini":
                        print(f"🧠 [Cluster 1] Squeezing Gemini Keys...")
                        raw_response = _call_gemini(action_prompt if is_action else chat_prompt)
                    elif provider == "groq":
                        print(f"⚙️ [Cluster 2] Fallback to Groq Cluster...")
                        # Build messages list for executor if needed
                        messages = self._build_executor_messages(user_message)
                        msgs = messages if is_action else [{"role": "user", "content": chat_prompt}]
                        raw_response = _call_groq(MODELS["groq"], msgs)
                    elif provider == "openrouter":
                        print(f"💎 [Cluster 3] Fallback to OpenRouter Cluster...")
                        messages = self._build_executor_messages(user_message)
                        msgs = messages if is_action else [{"role": "user", "content": chat_prompt}]
                        raw_response = _call_openrouter(msgs)
                    
                    if raw_response:
                        print(f"✅ {provider.title()} Success.")
                        break
                except Exception as e:
                    print(f"⚠️ {provider.title()} Cluster exhausted or failed: {str(e)[:50]}")
                    continue

            if not raw_response:
                # ── ALL CLUSTERS EXHAUSTED ──
                g_refill = GEMINI_CLUSTER.get_earliest_refill_time()
                gr_refill = GROQ_CLUSTER.get_earliest_refill_time()
                or_refill = OR_CLUSTER.get_earliest_refill_time()
                
                soonest = min([t for t in [g_refill, gr_refill, or_refill] if t > 0] or [60])
                
                return (
                    f"Boss, I've squeezed every last token from all your accounts. "
                    f"All sectors are currently in cooldown. The earliest refill will be in approximately {soonest} minutes. "
                    "I'm standing by until the systems are back online."
                )

            # Step 3: Handle execution
            tool_calls = _extract_all_json(raw_response)
            bait_reply = ""

            if tool_calls:
                execution_results = []
                for call in tool_calls:
                    if isinstance(call, dict) and "tool" in call:
                        tool_name = call.get("tool", "")
                        args = call.get("args", {})
                        
                        # Execute tool
                        tool_result = _execute_tool_call(tool_name, args)
                        
                        # SELF-HEALING: Check for failures
                        if any(err in tool_result for err in ["Could not find", "UI Error", "System Error", "FAIL"]):
                            # Analyze screen
                            try:
                                screen_path = capture_screen_state()
                                vision_prompt = f"The user wanted to '{user_message}' but the tool '{tool_name}' failed with result: '{tool_result}'. Look at this screenshot and tell me exactly what happened and what I should do next. Keep it brief."
                                correction = _call_vision(vision_prompt, screen_path)
                                tool_result = f"FAILURE: {tool_result}\nVISION ANALYSIS: {correction}"
                            except: pass
                        
                        execution_results.append(f"Command: {tool_name}\nResult: {tool_result}")

                if execution_results:
                    # Generate natural confirmation using cluster priority
                    confirm_messages = [
                        {"role": "system", "content": BAIT_PERSONA},
                        {
                            "role": "user",
                            "content": (
                                f"Context: The user asked: '{user_message}'\n"
                                f"I executed the following actions:\n\n"
                                + "\n\n".join(execution_results) + 
                                "\n\nNow, give a short, natural confirmation to the Boss. "
                                "If there was a failure, explain it naturally based on the Vision analysis. "
                                "Do not mention JSON. Keep it sharp and under 2 sentences."
                            )
                        }
                    ]
                    
                    # Try clusters for confirmation too
                    for provider in ["gemini", "groq", "openrouter"]:
                        try:
                            if provider == "gemini":
                                bait_reply = _call_gemini(confirm_messages[1]["content"])
                            elif provider == "groq":
                                bait_reply = _call_groq(MODELS["executor"], confirm_messages)
                            elif provider == "openrouter":
                                bait_reply = _call_openrouter(confirm_messages)
                            if bait_reply: break
                        except: continue

                    if not bait_reply:
                        bait_reply = "I've completed the tasks you requested, Boss."
                else:
                    bait_reply = raw_response
            else:
                bait_reply = raw_response

            if not bait_reply:
                bait_reply = "I've processed your request, Boss. Is there anything else?"

            # Update history
            self.history.append({"role": "user",      "content": user_message})
            self.history.append({"role": "assistant",  "content": bait_reply})

            print(f"🤖 BAIT Reply: {bait_reply}")
            return bait_reply
            
        except Exception as e:
            error_msg = f"Boss, I ran into a system error: {str(e)}"
            print(f"❌ Brain Error: {error_msg}")
            return error_msg

    def reset_memory(self):
        """Clear conversation history."""
        self.history = []
        return "Memory cleared. Fresh start, Boss."
