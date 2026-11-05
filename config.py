import os
from dotenv import load_dotenv

load_dotenv()

# API Settings
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
PRISMA_STT_URL = "https://api.vachana.ai/stt/v3"
TIMBRE_TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"

# Evon LLM is not on the hosted API. Leave this empty.
# The negotiator will instantly use the rules engine if this is empty.
EVON_LLM_URL = os.getenv("EVON_LLM_URL", "") 

# Audio Recording Specs
SAMPLE_RATE = 16000
CHANNELS = 1

# --- Voice Configuration ---
FEMALE_VOICE = "Nalini"
MALE_VOICE = "Vikrant"      # Male Hindi voice

# Default Parameters
DEFAULT_VOICE = FEMALE_VOICE
DEFAULT_LANG = "hi-IN"
DEFAULT_SPEED = 1.0