# 🎙️ Bhaav-AI (भाव-AI) — Real-Time Voice Micro-Negotiator

**Submitted for the Great Indian AI Internship Challenge by Gnani.ai**

## 📖 Overview
Bhaav-AI is a real-time, voice-first micro-negotiation assistant designed for Indian street commerce. Getting overcharged in local markets is a daily reality for millions of students, migrants, and tourists who lack local price knowledge or the confidence to bargain. 

Bhaav-AI acts as an in-ear co-pilot. You speak the vendor's quote in Hindi, English, or Hinglish. Bhaav-AI transcribes it, calculates a fair market price based on the context (Branded store vs. Local market), generates a strategic Hinglish counter-offer with advanced bargaining tactics, and speaks it back to you through the speakers. It even simulates multiple rounds of bargaining.

**Live Demo:** [https://bhaav-ai.onrender.com/static/index.html](https://bhaav-ai.onrender.com/static/index.html)

## 🚀 Key Features
* **Multilingual Voice & Text Input:** Seamlessly understands Hindi, English, and Hinglish code-mixed speech using **Gnani Prisma v2.5**. Select your preferred language directly from the UI dropdown.
* **Context-Aware Negotiation Modes:** Before negotiating, tell the AI if the price seems "Fair", "Unfair", or if you are "Unsure". If Unsure, the AI asks if you are in a **Branded Store** (tight margins) or a **Local Market** (high markups) to adjust its strategy.
* **Advanced Bargaining Tactics:** The LLM generates full, natural sentences using real street tactics (e.g., comparing to another shop, mentioning last week's price, playing the budget card, or asking for a round figure).
* **Live Audio Conversion:** Browser WebM audio is instantly converted to 16kHz WAV on the backend using a direct FFmpeg subprocess (handling both Windows and Linux/Render environments).
* **Delusional Price Guard:** If a vendor (or user) quotes an absurd price (like ₹5 Lakhs for a toothbrush), the AI flags it as "Delusional" and refuses to negotiate a joke.
* **Native Voice Output:** Speaks the counter-offer back to you in the selected language (Hindi, English, or Hinglish) using **Gnani Timbre v2.5**.
* **Multi-Round Bargaining:** Click the "Compromise" button to simulate the back-and-forth of a real street negotiation. The counter-offer smoothly climbs towards the fair price, and the script dynamically changes each round.
* **Premium UI:** Features a dynamic mesh gradient background, floating particles, glassmorphism cards, and smooth micro-interactions.

## 🛠️ Technology Stack
* **Speech-to-Text (STT):** Gnani.ai Prisma v2.5 (Code-mixed Indian dialects)
* **Text-to-Speech (TTS):** Gnani.ai Timbre v2.5 (Natural Hindi voice synthesis)
* **Reasoning / NLP:** Groq API (Llama-3.3 / GPT-OSS) for semantic entity extraction and dynamic script generation
* **Backend:** FastAPI, Uvicorn
* **Audio Processing:** FFmpeg, ImageIO-FFmpeg, Subprocess
* **Frontend:** HTML5, Tailwind CSS, JavaScript (MediaRecorder API), Glassmorphism UI

## ⚙️ Architecture Flow
1. **Audio Capture:** User records the vendor's quote via the browser (`MediaRecorder` API).
2. **Audio Conversion:** FastAPI uses a subprocess to convert the WebM stream to a 16kHz mono WAV file using FFmpeg.
3. **Transcription:** The WAV file is sent to **Gnani Prisma** to get the transcript.
4. **Entity Extraction & Strategy:** The transcript is sent to **Groq LLM** to identify the item name, extract the price, determine the fair market value, and generate a bargaining script based on the selected mode.
5. **Negotiation Engine:** A deterministic Python safety net ensures the math is bulletproof (no counter-offer higher than the quote, no fair price of 0).
6. **Voice Synthesis:** The counter-script is sent to **Gnani Timbre**, generating a WAV file in the selected language.
7. **Playback:** The user clicks "Speak" to hear the counter-offer.

## 💻 How to Run Locally

### 1. Prerequisites
* Python 3.11 or higher
* FFmpeg installed and added to your system PATH (or let `imageio-ffmpeg` handle it).

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