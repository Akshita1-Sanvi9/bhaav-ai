import streamlit as st
import os

from gnani_sdk.prisma_stt import transcribe_audio
from gnani_sdk.timbre_tts import synthesize_speech
from core.price_extractor import extract_price_and_item
from core.negotiator import fallback_rule_evaluation
import config

# --- 1. PAGE CONFIG & MODERN THEMING ---
st.set_page_config(
    page_title="Bhaav-AI | Real-Time Voice Micro-Negotiator",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Tailwind-inspired Modern CSS Injection
st.markdown("""
    <style>
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .hero-container {
        padding: 2rem 1rem;
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA, #A78BFA);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #94A3B8;
        font-weight: 400;
    }
    .card {
        background-color: #1E293B;
        border: 1px solid #334155;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .pill-overcharged {
        background-color: rgba(239, 68, 68, 0.15);
        border: 1px solid #EF4444;
        color: #FCA5A5;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 600;
    }
    .pill-fair {
        background-color: rgba(16, 185, 129, 0.15);
        border: 1px solid #10B981;
        color: #6EE7B7;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 600;
    }
    .pill-uncertain {
        background-color: rgba(245, 158, 11, 0.15);
        border: 1px solid #F59E0B;
        color: #FCD34D;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 600;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(96, 165, 250, 0.25);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.markdown("### 🏆 Challenger Credentials")
    st.markdown("**Name:** Akshita Sanvi")
    st.markdown("**USN:** 1NT24CS023")
    st.markdown("---")
    st.markdown("### 🎛️ System Controls")
    voice_select = st.selectbox("🗣️ Timbre TTS Voice", ["Nalini", "Deepak"], index=0)
    language_select = st.selectbox("🌐 Speech Dialect", ["hi-IN", "hi-en", "en-IN"], index=0)
    st.markdown("---")
    st.caption("**Project:** Bhaav-AI\n**Event:** Gnani.ai Challenge 2026")

# --- 3. HERO HEADER ---
st.markdown("""
    <div class="hero-container">
        <div class="main-title">🎙️ Bhaav-AI (भाव-AI)</div>
        <div class="sub-title">Sovereign Voice Micro-Negotiation & Price Discovery Assistant powered by Gnani.ai Prisma & Timbre v2.5</div>
    </div>
""", unsafe_allow_html=True)

# --- 4. MAIN WORKSPACE ---
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### 📥 1. Audio Capture & STT")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        st.write("Upload or record a vendor audio quote (.wav / .mp3):")
        
        # Universal compatible file uploader (works on all Streamlit versions & mobile)
        audio_file = st.file_uploader("Upload Vendor Audio Quote", type=["wav", "mp3", "m4a"])
        
        if audio_file is not None:
            audio_path = "vendor_quote.wav"
            with open(audio_path, "wb") as f:
                f.write(audio_file.getbuffer())
                
            st.audio(audio_path, format="audio/wav")
            st.success("Audio loaded successfully!")
            
            with st.spinner("Decoding speech via Gnani Prisma v2.5..."):
                transcript = transcribe_audio(audio_path, lang_code=language_select)
                
            st.session_state["transcript"] = transcript

        # Editable Transcript Area
        transcript_val = st.session_state.get("transcript", "")
        transcript_input = st.text_area("Live Code-Mixed Transcription", value=transcript_val, height=120, placeholder="e.g., 'Yeh aloo 40 rupaye kilo hai, final bolo'")
        
        if st.button("🔍 Analyze Quote & Negotiate", type="primary", use_container_width=True):
            if transcript_input.strip():
                st.session_state["active_transcript"] = transcript_input
            else:
                st.warning("Please upload audio or enter a transcript first.")
                
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown("### 🧠 2. Neural Negotiation Intelligence")
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        active_transcript = st.session_state.get("active_transcript", "")
        
        if active_transcript:
            parsed_data = extract_price_and_item(active_transcript)
            strategy = fallback_rule_evaluation(active_transcript)
            
            status = strategy.get("overcharge_status", "UNCERTAIN")
            quoted = strategy.get("quoted_price")
            fair = strategy.get("estimated_fair_price")
            counter = strategy.get("recommended_counter") or (int(quoted * 0.7) if quoted else None)
            whisper = strategy.get("whisper_advice", "")
            script = strategy.get("speech_script", "")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Quoted Price", f"₹{quoted}" if quoted else "N/A")
            m2.metric("Fair Baseline", f"₹{fair}" if fair else "N/A")
            m3.metric("Counter Offer", f"₹{counter}" if counter else "N/A")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if status == "OVERCHARGED":
                st.markdown(f'<div class="pill-overcharged">⚠️ Overcharge Detected<br><span style="font-size:0.9rem; font-weight:400; color:#FCA5A5;">{whisper}</span></div>', unsafe_allow_html=True)
            elif status == "FAIR":
                st.markdown(f'<div class="pill-fair">✅ Fair Market Rate<br><span style="font-size:0.9rem; font-weight:400; color:#6EE7B7;">{whisper}</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="pill-uncertain">ℹ️ Clarification Needed<br><span style="font-size:0.9rem; font-weight:400; color:#FCD34D;">{whisper}</span></div>', unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🔊 3. Timbre v2.5 Voice Synthesis")
            st.info(f"**Synthesized Script:** *\"{script}\"*")
            
            if st.button("🔊 Synthesize Counter Offer", use_container_width=True, type="primary"):
                with st.spinner("Synthesizing voice response via Gnani Timbre v2.5..."):
                    tts_output = synthesize_speech(text=script, output_path="counter_response.wav", voice=voice_select)
                    
                if tts_output and os.path.exists(tts_output):
                    st.audio(tts_output, format="audio/wav")
                    st.success("Counter-offer audio synthesized successfully!")
                else:
                    st.error("TTS generation failed.")
        else:
            st.info("👋 Upload an audio quote or type a transcript on the left to trigger real-time AI negotiation intelligence.")
            
        st.markdown('</div>', unsafe_allow_html=True)