import os
import google.generativeai as genai
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_keys():
    gemini_keys = os.getenv("GEMINI_KEYS", "").split(",")
    groq_keys = os.getenv("GROQ_KEYS", "").split(",")
    or_keys = os.getenv("OPENROUTER_KEYS", "").split(",")

    print("--- TESTING GEMINI KEYS ---")
    for k in gemini_keys:
        k = k.strip()
        if not k: continue
        try:
            genai.configure(api_key=k)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("hi")
            print(f"✅ Gemini Key {k[:8]}... SUCCESS: {response.text[:20]}")
        except Exception as e:
            print(f"❌ Gemini Key {k[:8]}... FAILED: {str(e)}")

    print("\n--- TESTING GROQ KEYS ---")
    for k in groq_keys:
        k = k.strip()
        if not k: continue
        try:
            client = Groq(api_key=k)
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "hi"}],
            )
            print(f"✅ Groq Key {k[:8]}... SUCCESS: {response.choices[0].message.content[:20]}")
        except Exception as e:
            print(f"❌ Groq Key {k[:8]}... FAILED: {str(e)}")

    print("\n--- TESTING OPENROUTER KEYS ---")
    for k in or_keys:
        k = k.strip()
        if not k: continue
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=k)
            response = client.chat.completions.create(
                model="anthropic/claude-3-haiku",
                messages=[{"role": "user", "content": "hi"}],
            )
            print(f"✅ OR Key {k[:8]}... SUCCESS: {response.choices[0].message.content[:20]}")
        except Exception as e:
            print(f"❌ OR Key {k[:8]}... FAILED: {str(e)}")

if __name__ == "__main__":
    test_keys()
