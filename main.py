import os
import sys
import re
import io
import traceback
import uuid
import subprocess
import tempfile
import shutil
import time

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# --- Base Directories ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# --- FFmpeg Setup ---
if os.name == "nt":
    FFMPEG_WIN_PATH = r"C:\Users\Akshita\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
    if os.path.exists(FFMPEG_WIN_PATH):
        FFMPEG_BIN = FFMPEG_WIN_PATH
    else:
        FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"
else:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

load_dotenv()

from gnani_sdk.prisma_stt import transcribe_audio
from core.negotiator import evaluate_dynamic_negotiation
from gnani_sdk.timbre_tts import synthesize_speech
import config

app = FastAPI(title="Bhaav-AI")

STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

AUDIO_DIR = os.path.join(BASE_DIR, "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)

def to_int(val):
    try: return int(float(val))
    except (TypeError, ValueError): return 0

def to_wav_16k(audio_bytes: bytes) -> str:
    out_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.wav")
    try:
        proc = subprocess.run(
            [FFMPEG_BIN, "-y", "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0", "-ar", "16000", "-ac", "1", out_path],
            input=audio_bytes, capture_output=True, timeout=30,
        )
        if proc.returncode != 0:
            raise ValueError(proc.stderr.decode(errors="ignore")[:300])
        return out_path
    except Exception as e:
        if os.path.exists(out_path): os.remove(out_path)
        raise ValueError(f"FFmpeg conversion failed: {e}")

def cleanup_old_audio():
    now = time.time()
    for f in os.listdir(AUDIO_DIR):
        fp = os.path.join(AUDIO_DIR, f)
        if os.path.isfile(fp) and os.path.getmtime(fp) < now - 600:
            try: os.remove(fp)
            except OSError: pass

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/audio/{req_id}/{kind}")
def get_audio(req_id: str, kind: str):
    if not re.fullmatch(r"[0-9a-f]{32}", req_id) or kind not in ("counter", "whisper"):
        raise HTTPException(status_code=404)
    path = os.path.join(AUDIO_DIR, f"{req_id}_{kind}.wav")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio not ready")
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "no-store"})

@app.post("/api/negotiate")
def process_negotiation(
    file: UploadFile = File(None),
    text_input: str = Form(None),
    round_number: int = Form(1),
    selected_lang: str = Form("hinglish"),
    negotiation_mode: str = Form("unsure")
):
    try:
        cleanup_old_audio()
        transcript = ""
        
        # BULLETPROOF STT MAPPING
        stt_lang = "hi-IN" 
        if selected_lang == "english":
            stt_lang = "en-IN"
            
        if text_input and text_input.strip():
            transcript = text_input.strip()
        elif file:
            audio_bytes = file.file.read()
            if len(audio_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Audio file too large.")
            try:
                wav_path = to_wav_16k(audio_bytes)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            try:
                transcript = transcribe_audio(wav_path, lang_code=stt_lang)
                print(f"[DEBUG] STT Output ({stt_lang}): '{transcript}'")
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Speech-to-text failed: {e}")
            finally:
                if os.path.exists(wav_path): os.remove(wav_path)

        if not transcript or not transcript.strip():
            raise HTTPException(status_code=400, detail="No speech detected.")

        # The negotiator returns the base counter, script, and whisper for Round 1
        result = evaluate_dynamic_negotiation(transcript, forced_lang=selected_lang, mode=negotiation_mode)
        
        quoted = to_int(result.get("quoted_price"))
        fair = to_int(result.get("fair_price"))
        item = result.get("item", "Item")
        lang = result.get("detected_language", "hinglish")
        base_counter = to_int(result.get("counter_offer"))

        if quoted <= 0:
            raise HTTPException(status_code=400, detail="Couldn't find a price in that sentence.")

        # --- 3. MATH LOGIC ---
        if round_number == 1:
            counter = base_counter
            whisper_advice = result.get("whisper_advice", "")
            speech_script = result.get("speech_script", "")
            status = result.get("status", "OVERCHARGED")
            
        elif result.get("status") == "DELUSIONAL":
            # Do not compromise on a joke price
            counter = base_counter
            status = "DELUSIONAL"
            if lang == "hindi":
                whisper_advice = f"Quoted: ₹{quoted}, Fair: ₹{fair}. मज़ाक कर रहे हो क्या? मैं नहीं लूंगा।"
                speech_script = "भैया, ये दाम तो पागलपन है। मैं नहीं लूंगा।"
            elif lang == "english":
                whisper_advice = f"Quoted: ₹{quoted}, Fair: ₹{fair}. This is absurd. Walk away."
                speech_script = "Are you joking? I'm not paying this."
            else:
                whisper_advice = f"Quoted: ₹{quoted}, Fair: ₹{fair}. Mazaak kar rahe ho kya? Main nahi lunga."
                speech_script = "Bhaiya, yeh toh mazaak hai. Main nahi lunga."
                
        else:
            # Compromise Rounds (2+)
            if fair <= 0: fair = int(quoted * 0.8)
            
            # SMOOTH MATH: Move towards the fair price
            gap = fair - base_counter
            if round_number == 2:
                counter = base_counter + int(gap * 0.33) 
            elif round_number == 3:
                counter = base_counter + int(gap * 0.66) 
            else:
                counter = fair 
            
            counter = min(quoted, counter)
            status = "OVERCHARGED"
            
            # DYNAMIC SCRIPT GENERATION FOR COMPROMISE
            try:
                import requests
                import json
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    compromise_prompt = f"""You are Bhaav-AI, an expert Indian street negotiator. 
                    The vendor quoted ₹{quoted}. The fair price is ₹{fair}. 
                    We are in round {round_number} of negotiation. The user is now willing to pay ₹{counter}.
                    
                    CRITICAL RULES:
                    1. The selected language is '{lang}'. Write the 'speech_script' and 'whisper_advice' strictly in '{lang}'.
                    2. Speak like a real Indian street customer. Use casual slang (e.g., "Bhaiya", "Mehnga hai", "Final karo"). NEVER use formal words like "agree", "accept", "deal", or "situation".
                    3. DO NOT use the word "offer".
                    4. speech_script: MUST be a full, natural sentence (12-15 words). It should sound like you are compromising but still pushing for a good deal.
                    5. whisper_advice: Include the prices like "Quoted ₹X, Fair ₹Y, Counter ₹{counter}." Followed by a short strategy.
                    
                    Return ONLY a JSON object: {{"speech_script": "...", "whisper_advice": "..."}}"""
                    
                    res_c = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "model": "openai/gpt-oss-20b",
                            "messages": [{"role": "user", "content": compromise_prompt}],
                            "temperature": 0.7,
                            "response_format": {"type": "json_object"}
                        },
                        timeout=4
                    )
                    if res_c.status_code == 200:
                        c_data = json.loads(res_c.json()["choices"][0]["message"]["content"])
                        speech_script = c_data.get("speech_script", "")
                        whisper_advice = c_data.get("whisper_advice", "")
                        print(f"[COMPROMISE LLM] -> {c_data}")
            except Exception as e:
                print(f"[COMPROMISE LLM FAILED]: {e}")

            # Python Fallback if LLM fails
            if not speech_script or "offer" in speech_script.lower():
                if lang == "english":
                    whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Compromise to ₹{counter}."
                    speech_script = f"Let's compromise. I can go up to ₹{counter}, final."
                elif lang == "hindi":
                    whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. थोड़ा बढ़ा कर ₹{counter} बोलो।"
                    speech_script = f"चलो भैया, मैं थोड़ा बढ़ा के बोलती हूँ। ₹{counter} रुपये में फाइनल कर दो।"
                else:
                    whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Thoda badha ke ₹{counter} bolo."
                    speech_script = f"Chalo bhaiya, main thoda badha ke bolti hoon. ₹{counter} me final kar do."

        counter = min(quoted, counter)
        overcharge_pct = int(((quoted - fair) / fair) * 100) if fair > 0 and quoted > fair else 0

        req_id = uuid.uuid4().hex
        counter_path = os.path.join(AUDIO_DIR, f"{req_id}_counter.wav")
        whisper_path = os.path.join(AUDIO_DIR, f"{req_id}_whisper.wav")

        tts_lang = "en-IN" if lang == "english" else "hi-IN"
        tts_available = False
        whisper_tts_available = False

        try:
            if synthesize_speech(text=speech_script, output_path=counter_path, voice=config.DEFAULT_VOICE, lang_code=tts_lang):
                tts_available = True
        except Exception as e: print(f"[TTS Error]: {e}")

        try:
            if synthesize_speech(text=whisper_advice, output_path=whisper_path, voice=config.DEFAULT_VOICE, lang_code=tts_lang):
                whisper_tts_available = True
        except Exception as e: print(f"[TTS Error]: {e}")

        response_payload = {
            "transcript": transcript, "item": item, "quoted_price": quoted,
            "fair_price": fair, "counter_offer": counter, "overcharge_pct": overcharge_pct,
            "status": status, "whisper_advice": whisper_advice, "speech_script": speech_script,
            "tts_available": tts_available, "whisper_tts_available": whisper_tts_available,
            "counter_audio_url": f"/audio/{req_id}/counter" if tts_available else "",
            "whisper_audio_url": f"/audio/{req_id}/whisper" if whisper_tts_available else "",
        }

        return JSONResponse(content=response_payload)

    except HTTPException: raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)