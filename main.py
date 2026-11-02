import os
import sys

# --- FFmpeg Setup ---
if os.name == "nt":
    FFMPEG_WIN_PATH = r"C:\Users\Akshita\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
    if os.path.exists(FFMPEG_WIN_PATH):
        os.environ["PATH"] += os.pathsep + FFMPEG_WIN_PATH
else:
    import imageio_ffmpeg
    os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import io
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

        result = evaluate_dynamic_negotiation(transcript)
        quoted = result.get("quoted_price", 0)
        fair = result.get("estimated_fair_price", 0)
        item = result.get("detected_item", "Item")
        lang = result.get("detected_language", "hinglish")

        if quoted <= 0:
            raise HTTPException(status_code=400, detail="Couldn't find a price.")

        if round_number == 1:
            counter = int(fair * 0.90) 
        elif round_number == 2:
            counter = int(fair * 0.95)
        else:
            counter = fair
        
        counter = min(quoted, counter)
        is_fair = quoted <= fair 
        overcharge_pct = int(((quoted - fair) / fair) * 100) if fair > 0 else 0

        # --- GENERATE SCRIPTS (Language Aware) ---
        if is_fair:
            status = "FAIR PRICE"
            whisper_advice = f"Quoted Rs.{quoted}. Fair estimate Rs.{fair}. This is a good price, accept it."
            if lang == "english":
                speech_script = f"Okay, I will take it for Rs.{quoted}."
            elif lang == "hindi":
                speech_script = f"ठीक है भैया, {quoted} रुपये में दे दो।"
            else:
                speech_script = f"Theek hai bhaiya, {quoted} rupaye me de do."
        else:
            status = "OVERCHARGED"
            whisper_advice = f"Vendor is asking Rs.{quoted}. Fair estimate is Rs.{fair}. Push them to Rs.{counter}."
            
            if round_number == 1:
                if lang == "english":
                    script_pool = [
                        f"That is too high. I can give you Rs.{counter}.",
                        f"I bought this last week for Rs.{counter}. Same price?",
                        f"Check the market rate, I will pay Rs.{counter}."
                    ]
                elif lang == "hindi":
                    script_pool = [
                        f"भैया, {quoted} रुपये बहुत ज़्यादा है। {counter} रुपये में देना है तो बोलो।",
                        f"पिछले हफ्ते {counter} में मिला था। आज भी वही रेट दो।",
                        f"मार्केट रेट चेक करो भैया, {counter} रुपये में फाइनल करो।"
                    ]
                else: # hinglish
                    script_pool = [
                        f"Bhaiya, {quoted} rupaye toh bahut zyada hai. {counter} me dena hai toh bolo.",
                        f"Arre bhaiya, market rate check karo. {counter} rupaye me final karo.",
                        f"Pichhle hafte {counter} me mila tha. Aaj bhi wahi rate do."
                    ]
                speech_script = random.choice(script_pool)
                
            elif round_number == 2:
                if lang == "english":
                    speech_script = f"Let's compromise. I can go up to Rs.{counter}, final."
                elif lang == "hindi":
                    speech_script = f"चलो भैया, मैं थोड़ा बढ़ा के बोलता हूँ। {counter} रुपये में फाइनल कर दो।"
                else:
                    speech_script = f"Chalo bhaiya, main thoda badha ke bolta hoon. {counter} me final kar do."
            else:
                if lang == "english":
                    speech_script = f"This is my final offer: Rs.{counter}. Take it or leave it."
                elif lang == "hindi":
                    speech_script = f"देखो भैया, मेरा लास्ट ऑफर है। {counter} रुपये में दे दो।"
                else:
                    speech_script = f"Dekho bhaiya, mera last offer hai. {counter} me de do."

        response_payload = {
            "transcript": transcript, "item": item, "quoted_price": quoted,
            "fair_price": fair, "counter_offer": counter, "overcharge_pct": overcharge_pct,
            "status": status, "whisper_advice": whisper_advice, "speech_script": speech_script,
        }

        for path in [COUNTER_AUDIO_PATH, WHISPER_AUDIO_PATH]:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass

        # Tell Gnani TTS which language to use for the voice
        tts_lang = "en-IN" if lang == "english" else "hi-IN"
        
        tts_counter = synthesize_speech(text=speech_script, output_path="counter_response.wav", voice=config.DEFAULT_VOICE, lang_code=tts_lang)
        tts_whisper = synthesize_speech(text=whisper_advice, output_path="whisper_response.wav", voice=config.DEFAULT_VOICE, lang_code=tts_lang)

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