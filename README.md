# 🎙️ Bhaav-AI (भाव-AI) — Real-Time Voice Micro-Negotiator

**Submitted for the Great Indian AI Internship Challenge by Gnani.ai**

## 📖 Overview
Bhaav-AI is a real-time, voice-first micro-negotiation assistant designed for Indian street commerce. Getting overcharged in local markets is a daily reality for millions of students, migrants, and tourists who lack local price knowledge or the confidence to bargain. 

Bhaav-AI acts as an in-ear co-pilot. You speak the vendor's quote in Hindi, English, or Hinglish. Bhaav-AI transcribes it, calculates a fair market price based on the context (Branded store vs. Local market), generates a strategic counter-offer with advanced bargaining tactics, and speaks it back to you through the speakers. It even simulates multiple rounds of bargaining.

**Live Demo:** [https://bhaav-ai.onrender.com/static/index.html](https://bhaav-ai.onrender.com/static/index.html)

## 💡 Why This Matters

In India, the "tourist tax" or "newcomer tax" is a real phenomenon. Whether you are a student moving to a new city, a tourist visiting a local bazaar, or just someone who hates the awkwardness of haggling, negotiating can be daunting.

**Real-world use-cases:**
* **Students & Migrants:** Navigating local markets (sabzi mandis, electronics hubs) without getting overcharged.
* **Tourists:** Buying souvenirs or auto-rickshaw rides without speaking the local language fluently.
* **Everyday Commuters:** Negotiating daily expenses (vegetables, cab fares, repairs) confidently and fairly.
* **Social Anxiety:** Perfect for introverts who know the fair price but lack the confidence to argue with an intimidating vendor.

Bhaav-AI bridges the gap between "knowing the price" and "having the courage to ask for it."

## 🚀 Key Features
* **Multilingual & Gender-Aware:** Seamlessly understands Hindi, English, and Hinglish code-mixed speech. You can also select your gender (Male/Female) from the UI, and the AI adjusts its grammar accordingly (e.g., "lunga" vs "lungi", "लूंगा" vs "लूंगी").
* **Context-Aware Negotiation Modes:** Before negotiating, tell the AI if the price seems "Fair", "Unfair", or if you are "Unsure". If Unsure, the AI asks if you are in a **Branded Store** (tight margins) or a **Local Market** (high markups) to adjust its strategy.
* **Advanced Bargaining Tactics:** The LLM generates full, natural sentences using real street tactics (comparing to another shop, mentioning last week's price, playing the budget card, or asking for a round figure).
* **Locked Compromise Logic:** When you click "Compromise", the frontend locks the initial Quoted Price, Fair Price, and Base Counter. The backend math strictly moves the counter up by 25%, 50%, and 75% towards the fair price across rounds—preventing the LLM from hallucinating random numbers.
* **Live Audio Conversion:** Browser WebM audio is instantly converted to 16kHz WAV on the backend using a direct FFmpeg subprocess (handling both Windows and Linux/Render environments).
* **Delusional Price Guard:** If a vendor (or user) quotes an absurd price (like ₹80 for a phone), the AI flags it as "Delusional" and refuses to negotiate a joke.
* **Native Voice Output:** Speaks the counter-offer back to you in the selected language using **Gnani Timbre v2.5**.
* **Premium UI:** Features a dynamic mesh gradient background, floating particles, glassmorphism cards, and mobile-responsive micro-interactions.

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
4. **Entity Extraction & Strategy:** The transcript is sent to **Groq LLM** to identify the item name, extract the price, determine the fair market value, and generate a bargaining script based on the selected language and gender.
5. **Negotiation Engine:** A deterministic Python safety net ensures the math is bulletproof (no counter-offer higher than the quote, no fair price of 0) and that the Speak Back script and Strategy exactly match the locked Counter.
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