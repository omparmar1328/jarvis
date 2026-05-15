import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def list_gemini_models():
    gemini_keys = os.getenv("GEMINI_KEYS", "").split(",")
    for k in gemini_keys:
        k = k.strip()
        if not k: continue
        print(f"\n--- LISTING MODELS FOR KEY {k[:8]}... ---")
        try:
            genai.configure(api_key=k)
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"   - {m.name}")
            
            # Try a simple generation with a very safe model name
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("hi")
            print(f"✅ Success with 'gemini-1.5-flash': {response.text[:20]}")
        except Exception as e:
            print(f"❌ Error for key {k[:8]}: {str(e)}")

if __name__ == "__main__":
    list_gemini_models()
