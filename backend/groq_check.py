import os
import sys
import httpx
from dotenv import load_dotenv


def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    if not api_key:
        print("❌ GROQ_API_KEY is not set. Add it to backend/.env or your environment.")
        sys.exit(1)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Reply with the single word: pong"},
        ],
        "temperature": 0,
        "max_tokens": 8,
    }

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}: {resp.text}")
            sys.exit(2)
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        print(f"Model: {model}")
        print(f"Reply: {content}")
        if "pong" in content.lower():
            print("✅ Groq API check: OK")
            sys.exit(0)
        else:
            print("Groq API responded but unexpected content.")
            sys.exit(3)
    except Exception as e:
        print(f"Error calling Groq: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()
