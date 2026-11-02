import os

FFMPEG_WIN_PATH = r"C:\Users\Akshita\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
if os.name == "nt" and os.path.exists(FFMPEG_WIN_PATH):
    os.environ["PATH"] += os.pathsep + FFMPEG_WIN_PATH

import io
import sys
import traceback
import random

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gnani_sdk.prisma_stt import transcribe_audio
from core.negotiator import evaluate_dynamic_negotiation
from gnani_sdk.timbre_tts import synthesize_speech
import config

app = FastAPI(title="Bhaav-AI")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

COUNTER_AUDIO_PATH = os.path.join(os.getcwd(), "counter_response.wav")
WHISPER_AUDIO_PATH = os.path.join(os.getcwd(), "whisper_response.wav")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/audio/counter")
def get_counter_audio():
    if os.path.exists(COUNTER_AUDIO_PATH):
        return FileResponse(COUNTER_AUDIO_PATH, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="Audio not ready")

@app.get("/audio/whisper")
def get_whisper_audio():
    if os.path.exists(WHISPER_AUDIO_PATH):
        return FileResponse(WHISPER_AUDIO_PATH, media_type="audio/wav")
    raise HTTPException(status_code=404, detail="Audio not ready")


@app.post("/api/negotiate")
async def process_negotiation(
    file: UploadFile = File(None),
    text_input: str = Form(None),
    round_number: int = Form(1),
):
    try:
        transcript = ""
        if text_input and text_input.strip():
            transcript = text_input.strip()
        elif file:
            audio_bytes = await file.read()
            temp_wav_path = "temp_input.wav"
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                audio_segment.set_frame_rate(16000).set_channels(1).export(temp_wav_path, format="wav")
                transcript = transcribe_audio(temp_wav_path, lang_code="hi-IN")
            finally:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)

        if not transcript or not transcript.strip():
            raise HTTPException(status_code=400, detail="No speech detected.")

        # The negotiator ALWAYS calculates based on the original quote
        result = evaluate_dynamic_negotiation(transcript)
        quoted = result.get("quoted_price", 0)
        fair = result.get("estimated_fair_price", 0)
        item = result.get("detected_item", "Item")

        if quoted <= 0:
            raise HTTPException(status_code=400, detail="Couldn't find a price.")

        # --- COMPROMISE MATH LOGIC ---
        # We keep the vendor's 'quoted' price exactly the same.
        # Your 'counter' offer goes up every round until it hits the Fair Price.
        if round_number == 1:
            # Round 1: Your opening lowball offer (10% below fair)
            counter = int(fair * 0.90) 
        elif round_number == 2:
            # Round 2: You raise your offer (5% below fair)
            counter = int(fair * 0.95)
        else:
            # Round 3+: You meet exactly at the fair price
            counter = fair
        
        # Ensure you never offer more than the vendor is asking
        counter = min(quoted, counter)

        # The vendor is only fair if their quote is equal to or lower than the fair price
        is_fair = quoted <= fair 
        overcharge_pct = int(((quoted - fair) / fair) * 100) if fair > 0 else 0

        # --- GENERATE SCRIPTS ---
        if is_fair:
            status = "FAIR PRICE"
            whisper_advice = f"Quoted Rs.{quoted}. Fair estimate Rs.{fair}. This is a good price, accept it."
            speech_script = f"Theek hai bhaiya, {quoted} rupaye me de do."
        else:
            status = "OVERCHARGED"
            whisper_advice = f"Vendor is asking Rs.{quoted}. Fair estimate is Rs.{fair}. Push them to Rs.{counter}."
            
            if round_number == 1:
                # Expanded pool of varied Hinglish scripts for Round 1
                script_pool = [
                    f"Bhaiya, {quoted} rupaye toh bahut zyada hai. {counter} me dena hai toh bolo, warna main aage chala jaunga.",
                    f"Arre bhaiya, market rate check karo. {counter} rupaye me final karo.",
                    f"Pichhle hafte {counter} me mila tha. Aaj bhi wahi rate do.",
                    f"Theek hai bhaiya, {quoted} se kam nahi karoge? Chalo {counter} me de do.",
                    f"Main regular customer hoon bhaiya, {counter} me de do toh aaj le jata hoon."
                ]
                speech_script = random.choice(script_pool)
            elif round_number == 2:
                speech_script = f"Chalo bhaiya, main thoda badha ke bolta hoon. {counter} me final kar do."
            else:
                speech_script = f"Dekho bhaiya, mera last offer hai. {counter} me de do, warna main chala jaunga."

        response_payload = {
            "transcript": transcript, "item": item, "quoted_price": quoted,
            "fair_price": fair, "counter_offer": counter, "overcharge_pct": overcharge_pct,
            "status": status, "whisper_advice": whisper_advice, "speech_script": speech_script,
        }

        # Generate BOTH Counter Audio and Whisper Audio
        for path in [COUNTER_AUDIO_PATH, WHISPER_AUDIO_PATH]:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass

        tts_counter = synthesize_speech(text=speech_script, output_path="counter_response.wav", voice=config.DEFAULT_VOICE)
        tts_whisper = synthesize_speech(text=whisper_advice, output_path="whisper_response.wav", voice=config.DEFAULT_VOICE)

        response_payload["tts_available"] = bool(tts_counter)
        response_payload["whisper_tts_available"] = bool(tts_whisper)

        return JSONResponse(content=response_payload)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)