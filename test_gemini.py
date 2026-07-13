import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

models_to_try = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-2.0-flash"
]

for model in models_to_try:
    try:
        print(f"\nTrying: {model}")

        response = client.models.generate_content(
            model=model,
            contents="Say Hello"
        )

        print("✅ SUCCESS")
        print(response.text)
        break

    except Exception as e:
        print(f"❌ FAILED: {e}")