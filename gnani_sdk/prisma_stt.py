import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def transcribe_audio(audio_file_path: str, lang_code: str = "hi-IN") -> str:
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found at: {audio_file_path}")

    headers = {
        "X-API-Key-ID": config.GNANI_API_KEY
    }

    # v3 API payload. We use hi-IN because Prisma is trained on Hinglish code-switching.
    payload = {
        "language_code": lang_code,
        "format": "transcribe"
    }

    try:
        with open(audio_file_path, "rb") as audio_file:
            files = {
                "audio_file": (os.path.basename(audio_file_path), audio_file, "audio/wav")
            }
            
            response = requests.post(
                config.PRISMA_STT_URL,
                headers=headers,
                data=payload,
                files=files,
                timeout=30
            )

        if response.status_code == 200:
            result = response.json()
            transcript = result.get("transcript", "").strip()
            return transcript
        else:
            print(f"[Prisma STT Error {response.status_code}]: {response.text}")
            return ""

    except Exception as e:
        print(f"[Prisma STT Exception]: {e}")
        return ""