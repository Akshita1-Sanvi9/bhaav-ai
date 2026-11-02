import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def synthesize_speech(
    text: str, 
    output_path: str = "counter_response.wav", 
    voice: str = None,
    lang_code: str = None  # <-- Added this parameter
) -> str:
    """
    Sends synthesized negotiation dialogue to Gnani's Timbre v2.5 TTS API 
    and saves the output audio to a WAV file.
    """
    # Safe fallbacks if config values are missing
    api_key = getattr(config, "GNANI_API_KEY", "")
    tts_url = getattr(config, "TIMBRE_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")
    sample_rate = getattr(config, "SAMPLE_RATE", 48000)
    channels = getattr(config, "CHANNELS", 1)
    default_voice = getattr(config, "DEFAULT_VOICE", "Nalini")
    default_lang = getattr(config, "DEFAULT_LANG", "hi-IN")
    default_speed = getattr(config, "DEFAULT_SPEED", 1.0)

    selected_voice = voice if voice else default_voice
    # Use the passed language, or fall back to default
    selected_lang = lang_code if lang_code else default_lang

    headers = {
        "Content-Type": "application/json",
        "X-API-Key-ID": api_key
    }

    payload = {
        "text": text,
        "voice": selected_voice,
        "model": "timbre-v2.5",
        "language": selected_lang,  # <-- Using the dynamic language
        "speed": default_speed,
        "audio_config": {
            "sample_rate": sample_rate,
            "num_channels": channels,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav"
        }
    }

    try:
        response = requests.post(
            tts_url, 
            headers=headers, 
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return output_path
        else:
            print(f"[Timbre TTS Error {response.status_code}]: {response.text}")
            return ""

    except Exception as e:
        print(f"[Timbre TTS Exception]: {e}")
        return ""