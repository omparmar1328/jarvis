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
import google.generativeai as genai
from groq import Groq
from openai import OpenAI  # OpenRouter is OpenAI-compatible

from bait.config import (
    GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
    MODELS, BAIT_PERSONA
)
from bait.actions import TOOL_REGISTRY, TOOL_DESCRIPTIONS


# ── Client initialization ──────────────────────────────────────────────────
_groq_client = None
_openrouter_client = None

def _get_groq():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

def _get_openrouter():
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return _openrouter_client

def _init_gemini():
    genai.configure(api_key=GEMINI_API_KEY)


# ── Model Callers ──────────────────────────────────────────────────────────

def _call_groq(model: str, messages: list, temperature: float = 0.4) -> str:
    """Call a Groq model and return text response."""
    response = _get_groq().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def _call_gemini(prompt: str, temperature: float = 0.5) -> str:
    """Call Gemini Flash for general conversation."""
    _init_gemini()
    model = genai.GenerativeModel(
        model_name=MODELS["chat"],
        generation_config={"temperature": temperature, "max_output_tokens": 400},
        system_instruction=BAIT_PERSONA,
    )
    response = model.generate_content(prompt)
    return response.text.strip()


def _call_openrouter(messages: list, temperature: float = 0.4) -> str:
    """Call OpenRouter (Claude Haiku) as a fallback for complex tasks."""
    response = _get_openrouter().chat.completions.create(
        model=MODELS["complex"],
        messages=messages,
        temperature=temperature,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


# ── Intent Classifier ──────────────────────────────────────────────────────

INTENT_PROMPT = """You are a command intent classifier. Given a user message, classify it as ONE of:
- "action"     → The user wants to DO something on the Mac (open app, search, control system)
- "chat"       → General conversation, question, or chitchat

Respond with ONLY one word: action OR chat"""

def classify_intent(user_message: str) -> str:
    """Use Groq's fastest model to classify intent instantly."""
    messages = [
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user",   "content": user_message},
    ]
    result = _call_groq(MODELS["classifier"], messages, temperature=0.0)
    return "action" if "action" in result.lower() else "chat"


# ── Tool Parser ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Extract the first JSON object from a response string."""
    try:
        # Direct parse
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find embedded JSON
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


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
        self.history: list[dict] = []
        self.system_prompt = BAIT_PERSONA + "\n\n" + TOOL_DESCRIPTIONS

    def _build_executor_messages(self, user_message: str) -> list[dict]:
        """Build message list for the executor model."""
        messages = [{"role": "system", "content": self.system_prompt}]
        # Include last 6 turns for context (keep it lean for speed)
        messages.extend(self.history[-6:])
        messages.append({"role": "user", "content": user_message})
        return messages

    def think(self, user_message: str) -> str:
        """
        Main entry point. Routes the message, calls the right model,
        executes tools, and returns BAIT's final reply.
        """
        # Step 1: Classify intent with the fastest model
        intent = classify_intent(user_message)

        if intent == "action":
            # Step 2: Use Groq llama3-70b to decide which tool to call
            messages = self._build_executor_messages(user_message)
            raw_response = _call_groq(MODELS["executor"], messages, temperature=0.2)

            # Step 3: Check if the response is a tool call (JSON)
            tool_call = _extract_json(raw_response)

            if tool_call and "tool" in tool_call:
                tool_name = tool_call.get("tool", "")
                args = tool_call.get("args", {})

                # Step 4: Execute the tool
                tool_result = _execute_tool_call(tool_name, args)

                # Step 5: Generate a natural spoken reply from Groq about the result
                confirm_messages = [
                    {"role": "system", "content": BAIT_PERSONA},
                    {
                        "role": "user",
                        "content": (
                            f"I asked you to: '{user_message}'\n"
                            f"You executed: {tool_name}({args})\n"
                            f"Result: {tool_result}\n\n"
                            f"Give a short, natural spoken confirmation. No JSON. Keep it 1–2 sentences."
                        )
                    }
                ]
                spoken_reply = _call_groq(MODELS["executor"], confirm_messages, temperature=0.6)
                bait_reply = spoken_reply

            else:
                # The executor gave a direct text response (no tool needed)
                bait_reply = raw_response

        else:
            # Conversation → Gemini Flash (free, big quota)
            try:
                # Build a prompt with recent history
                history_text = ""
                for turn in self.history[-4:]:
                    role = "You" if turn["role"] == "assistant" else "User"
                    history_text += f"{role}: {turn['content']}\n"
                history_text += f"User: {user_message}"
                bait_reply = _call_gemini(history_text)
            except Exception:
                # Fallback to Groq if Gemini fails
                messages = self._build_executor_messages(user_message)
                bait_reply = _call_groq(MODELS["executor"], messages, temperature=0.7)

        # Update history
        self.history.append({"role": "user",      "content": user_message})
        self.history.append({"role": "assistant",  "content": bait_reply})

        return bait_reply

    def reset_memory(self):
        """Clear conversation history."""
        self.history = []
        return "Memory cleared. Fresh start, Boss."
