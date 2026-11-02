# 🎙️ Bhaav-AI (भाव-AI) — Real-Time Voice Micro-Negotiator

**Submitted for the Great Indian AI Internship Challenge by Gnani.ai**

## 📖 Overview
Bhaav-AI is a real-time, voice-first micro-negotiation assistant designed for Indian street commerce. Getting overcharged in local markets is a daily reality for millions of students, migrants, and tourists who lack local price knowledge or the confidence to bargain. 

Bhaav-AI acts as an in-ear co-pilot. You speak the vendor's quote in Hindi, English, or Hinglish. Bhaav-AI transcribes it, calculates a fair market price, generates a strategic Hinglish counter-offer, and speaks it back to you through the speakers. It even simulates multiple rounds of bargaining.

**Live Demo:** *[Add your Render link here once deployed!]*

## 🚀 Key Features
* **Multilingual Voice Input:** Seamlessly understands Hindi, English, and Hinglish code-mixed speech using **Gnani Prisma v2.5**.
* **Live Audio Conversion:** Browser WebM audio is instantly converted to 16kHz WAV on the backend using FFmpeg and Pydub.
* **Intelligent Item Extraction:** Uses an LLM (Groq / Llama-3) as a semantic parser to identify items (e.g., "टिंडे", "laptop", "auto") and avoid rigid keyword lists.
* **Bulletproof Pricing Math:** A deterministic Python engine calculates the overcharge percentage and fair price, ensuring no AI hallucinations in the final financial math.
* **Native Voice Output:** Speaks the counter-offer back to you in Hindi using **Gnani Timbre v2.5**.
* **Multi-Round Bargaining:** Click the "Compromise" button to simulate the back-and-forth of a real street negotiation.
* **In-Ear Whisper:** Discreetly generates the exact numbers and strategy so you can read or hear them privately.

## 🛠️ Technology Stack
* **Speech-to-Text (STT):** Gnani.ai Prisma v2.5 (Code-mixed Indian dialects)
* **Text-to-Speech (TTS):** Gnani.ai Timbre v2.5 (Natural Hindi voice synthesis)
* **Reasoning / NLP:** Groq API (Llama-3) for semantic entity extraction
* **Backend:** FastAPI, Uvicorn
* **Audio Processing:** Pydub, FFmpeg, NumPy
* **Frontend:** HTML5, Tailwind CSS, JavaScript (MediaRecorder API)

## ⚙️ Architecture Flow
1. **Audio Capture:** User records the vendor's quote via the browser (`MediaRecorder` API).
2. **Audio Conversion:** FastAPI converts the WebM stream to a 16kHz mono WAV file using FFmpeg.
3. **Transcription:** The WAV file is sent to **Gnani Prisma** to get the Hinglish transcript.
4. **Entity Extraction:** The transcript is sent to **Groq LLM** to identify the item name.
5. **Negotiation Engine:** A deterministic Python script calculates the fair price and counter-offer based on tiered margins.
6. **Voice Synthesis:** The Hinglish counter-script is sent to **Gnani Timbre**, generating a WAV file.
7. **Playback:** The user clicks "Speak" to hear the counter-offer.

## 💻 How to Run Locally

### 1. Prerequisites
* Python 3.11 or higher
* FFmpeg installed and added to your system PATH.

### 2. Installation
```bash
git clone https://github.com/Akshita1-Sanvi9/bhaav-ai.git
cd bhaav-ai
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt