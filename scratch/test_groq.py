import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def test_groq_keys():
    groq_keys = os.getenv("GROQ_KEYS", "").split(",")
    models = ["llama-3.1-70b-versatile", "llama3-70b-8192", "llama-3.1-8b-instant"]

    for k in groq_keys:
        k = k.strip()
        if not k: continue
        print(f"\n--- TESTING GROQ KEY {k[:8]}... ---")
        client = Groq(api_key=k)
        for m in models:
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=[{"role": "user", "content": "hi"}],
                )
                print(f"   ✅ Model {m} SUCCESS: {response.choices[0].message.content[:20]}")
            except Exception as e:
                print(f"   ❌ Model {m} FAILED: {str(e)[:50]}...")

if __name__ == "__main__":
    test_groq_keys()
