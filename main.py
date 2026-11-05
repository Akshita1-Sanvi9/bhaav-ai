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
import requests
import json
import random

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
    negotiation_mode: str = Form("unsure"),
    locked_quoted: int = Form(None),
    locked_fair: int = Form(None),
    locked_base_counter: int = Form(None)
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

        result = evaluate_dynamic_negotiation(transcript, forced_lang=selected_lang, mode=negotiation_mode)
        
        quoted = to_int(result.get("quoted_price"))
        fair = to_int(result.get("fair_price"))
        item = result.get("item", "Item")
        # Force the language to be strictly what the user selected in the UI
        lang = selected_lang
        base_counter = to_int(result.get("counter_offer"))

        if quoted <= 0:
            raise HTTPException(status_code=400, detail="Couldn't find a price in that sentence.")

        # --- 3. MATH LOGIC ---
        
        # Force the locked prices if this is a compromise round
        if round_number > 1:
            if locked_quoted is not None: quoted = locked_quoted
            if locked_fair is not None: fair = locked_fair
            if locked_base_counter is not None: base_counter = locked_base_counter
            
        if round_number == 1:
            counter = base_counter
            whisper_advice = result.get("whisper_advice", "")
            speech_script = result.get("speech_script", "")
            status = result.get("status", "OVERCHARGED")
            
        elif result.get("status") == "DELUSIONAL" or (fair > 0 and quoted < (fair * 0.1)):
            # Do not compromise on a joke price
            counter = base_counter
            status = "DELUSIONAL"
            if lang == "hindi":
                whisper_advice = f"दुकानदार ₹{quoted} माँग रहा है, सही रेट ₹{fair} है। ये दाम पागलपन है, मत लो।"
                speech_script = "भैया, ये दाम तो पागलपन है। मैं नहीं लूंगा।"
            elif lang == "english":
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. This is absurd. Walk away."
                speech_script = "Are you joking? I'm not paying this."
            else:
                whisper_advice = f"Vendor ne ₹{quoted} bola, fair rate ₹{fair} hai. Mazaak kar rahe ho kya? Main nahi lunga."
                speech_script = "Bhaiya, yeh toh mazaak hai. Main nahi lunga."
                
        else:
            # Compromise Rounds (2+)
            speech_script = ""
            whisper_advice = ""
            
            if fair <= 0: fair = int(quoted * 0.8)
            
            # We now safely use the LOCKED base_counter from Round 1
            prev_counter = base_counter
            
            # Calculate a smooth step towards the fair price
            if prev_counter >= fair:
                counter = fair
            else:
                gap = fair - prev_counter
                if round_number == 2:
                    counter = prev_counter + max(1, int(gap * 0.25)) 
                elif round_number == 3:
                    counter = prev_counter + max(1, int(gap * 0.50)) 
                elif round_number == 4:
                    counter = prev_counter + max(1, int(gap * 0.75))
                else:
                    counter = fair 
            
            # Hard guard: Never exceed the vendor's quote, never decrease from previous
            counter = min(quoted, counter)
            
            # If the math somehow drops below the locked counter, force it up
            if counter < base_counter:
                counter = base_counter
                
            status = "OVERCHARGED"
            
            # DYNAMIC SCRIPT GENERATION FOR COMPROMISE
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    compromise_prompt = f"""You are Bhaav-AI, an expert Indian street negotiator. 
                    The vendor quoted ₹{quoted}. The fair price is ₹{fair}. 
                    We are in round {round_number} of negotiation. 
                    
                    FACTS:
                    - The user's previous counter-offer was EXACTLY ₹{base_counter}.
                    - The user is now increasing their limit to EXACTLY ₹{counter}.
                    
                    CRITICAL RULES:
                    1. The selected language is '{lang}'. Write the 'speech_script' and 'whisper_advice' strictly in '{lang}'.
                    2. Speak like a real Indian street customer. Use casual slang (e.g., "Bhaiya", "Mehnga hai", "Final karo"). NEVER use formal words like "agree", "accept", "deal", or "situation".
                    3. DO NOT use the word "offer".
                    4. speech_script: MUST be a full, natural sentence (12-15 words). 
                       - Frame it exactly as: "I am increasing my price from ₹{base_counter} to ₹{counter} because I really want it, but ₹{counter} is my absolute final limit."
                       - DO NOT invent any other numbers. Use exactly {base_counter} and {counter}.
                    5. whisper_advice: Include the prices like "Quoted ₹{quoted}, Fair ₹{fair}, Counter ₹{counter}." Followed by a short strategy.
                    
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
                        
                        # STRICT LANGUAGE VALIDATION FOR COMPROMISE
                        if lang == "hindi":
                            if re.search(r'[a-zA-Z]', speech_script) or re.search(r'[a-zA-Z]', whisper_advice):
                                speech_script = ""
                                whisper_advice = ""
                        elif lang == "english":
                            hinglish_pattern = r'\b(bhaiya|bhai|hai|hain|ka|ki|ko|mein|kar|karo|dega|rupaye|zyada|kam|mehnga|sasta|theek)\b'
                            if re.search(hinglish_pattern, speech_script.lower()) or re.search(hinglish_pattern, whisper_advice.lower()) or re.search(r'[\u0900-\u097F]', speech_script) or re.search(r'[\u0900-\u097F]', whisper_advice):
                                speech_script = ""
                                whisper_advice = ""
                        elif lang == "hinglish":
                            # Reject pure English (missing Hindi words)
                            hinglish_words = r'\b(bhaiya|bhai|hai|hain|ka|ki|ko|mein|kar|karo|dega|rupaye|zyada|kam|mehnga|sasta|theek|yaar|me)\b'
                            if not re.search(hinglish_words, speech_script.lower()) or re.search(r'[\u0900-\u097F]', speech_script):
                                speech_script = ""
                                whisper_advice = ""
                                
            except Exception as e:
                pass

            # Python Fallback if LLM fails
            if not speech_script:
                tactic = random.choice(["compare", "budget", "round"])
                
                if lang == "english":
                    if tactic == "compare":
                        speech_script = f"Brother, I really want to buy this, but I saw it for ₹{counter} at another shop. Can you match that?"
                    elif tactic == "budget":
                        speech_script = f"Brother, I'll be honest, my budget is only ₹{counter}. Let's close the deal at this price."
                    else:
                        speech_script = f"Brother, let's compromise. I'll pay ₹{counter} right now, cash. Final price?"
                    whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Counter ₹{counter}. Be firm and ready to walk away."
                    
                elif lang == "hindi":
                    if tactic == "compare":
                        speech_script = f"भैया, मैं सच में ये खरीदना चाहता हूँ, लेकिन बगल वाले ₹{counter} में दे रहे हैं। आप भी कम करो ना।"
                    elif tactic == "budget":
                        speech_script = f"भैया, सच बता रहा हूँ, मेरा बजट सिर्फ ₹{counter} है। इसी में डील फाइनल कर दो।"
                    else:
                        speech_script = f"भैया, चलो ₹{counter} में फाइनल करते हैं। मैं अभी कैश देता हूँ, अंतिम दाम बताओ।"
                    whisper_advice = f"दुकानदार ₹{quoted} माँग रहा है, सही रेट ₹{fair} है। अब ₹{counter} बोलो।"
                    
                else:
                    if tactic == "compare":
                        speech_script = f"Bhaiya, main sach me yeh lena chahta hoon, par bagal wale ₹{counter} me de rahe hain. Aap bhi thoda adjust karo."
                    elif tactic == "budget":
                        speech_script = f"Bhaiya, sach batau toh mera budget sirf ₹{counter} hai. Isi me final kar do, abhi cash de dunga."
                    else:
                        speech_script = f"Bhaiya, chalo ₹{counter} me final kar do. Round figure banao aur saman pack kar do."
                    whisper_advice = f"Vendor ne ₹{quoted} bola, fair rate ₹{fair} hai. Aap ₹{counter} pe final karne ki koshish karo."

            # THE ULTIMATE STRATEGY LOCK: Overwrite whisper_advice in the selected language
            if lang == "hindi":
                whisper_advice = f"दुकानदार ₹{quoted} माँग रहा है, सही रेट ₹{fair} है। अब ₹{counter} बोलो और डटे रहो।"
            elif lang == "english":
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Counter ₹{counter}. Be firm and stick to this final limit."
            else:
                whisper_advice = f"Vendor ne ₹{quoted} bola, fair rate ₹{fair} hai. Aap ₹{counter} pe final karne ki koshish karo."

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