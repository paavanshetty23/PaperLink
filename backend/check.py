import os
import sys
import httpx
from dotenv import load_dotenv


MODELS_URL = "https://api.groq.com/openai/v1/models"
CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def pick_supported_model(api_key: str) -> str | None:
    preferred = [
        # Prefer current Llama 3.1 variants
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        # Other common options
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=20) as client:
            r = client.get(MODELS_URL, headers=headers)
            r.raise_for_status()
            data = r.json()
        ids = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
        # Choose first preferred that exists
        for p in preferred:
            if p in ids:
                return p
        # Fallback to first available
        return ids[0] if ids else None
    except Exception:
        return None


def call_chat(api_key: str, model: str) -> tuple[int, str]:
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
    with httpx.Client(timeout=20) as client:
        resp = client.post(CHAT_URL, headers=headers, json=payload)
    return resp.status_code, resp.text


def main():
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL")
    if not api_key:
        print("❌ GROQ_API_KEY is not set. Add it to backend/.env or your environment.")
        sys.exit(1)

    # If no model provided, or provided model fails with decommissioned error, pick from /models.
    tried_models = []
    if not model:
        model = pick_supported_model(api_key)
        if not model:
            print("❌ Could not fetch supported models from Groq; check your key and network.")
            sys.exit(2)

    status, text = call_chat(api_key, model)
    if status == 200:
        try:
            data = httpx.Response(status_code=200, text=text).json()
        except Exception:
            print(f"Model: {model}\nRaw: {text}")
            sys.exit(0)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        print(f"Model: {model}")
        print(f"Reply: {content}")
        print("✅ Groq API check: OK")
        sys.exit(0)

    # If 400 with decommissioned code, try auto-pick
    tried_models.append(model)
    if status == 400 and "model_decommissioned" in text:
        alt = pick_supported_model(api_key)
        if alt and alt not in tried_models:
            status, text = call_chat(api_key, alt)
            if status == 200:
                data = httpx.Response(status_code=200, text=text).json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                print(f"Model: {alt}")
                print(f"Reply: {content}")
                print("✅ Groq API check: OK (auto-switched model)")
                sys.exit(0)

    print(f"HTTP {status}: {text}")
    sys.exit(3)


if __name__ == "__main__":
    main()
