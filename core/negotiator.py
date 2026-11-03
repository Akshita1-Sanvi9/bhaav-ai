import re
import os
import requests
import json
import random

def _compute_prices(quoted: int, category: str) -> tuple:
    if quoted <= 0: return 0, 0
    if category == "electronics": margin = 0.10
    elif category == "clothing": margin = 0.25
    elif category == "grocery": margin = 0.35
    else: margin = 0.25
    fair = int(quoted * (1 - margin))
    counter = int(fair * 0.90)
    return counter, fair

def extract_digits_only(text: str) -> int:
    """Python fallback to find numbers if the LLM fails."""
    text = text.lower().replace(',', '').replace('.', '')
    text = re.sub(r'\b(hazaar|hazar|thousand|k)\b', '000', text)
    text = re.sub(r'\b(lakh|lac)\b', '00000', text)
    text = re.sub(r'\b(crore|cr)\b', '0000000', text) 
    text = text.replace('हज़ार', '000').replace('हजार', '000')
    text = text.replace('लाख', '00000').replace('करोड़', '0000000') 
    text = re.sub(r'(\d)\s+(000)', r'\1\2', text)
    text = re.sub(r'(\d+)\s+(00000)', r'\1\2', text)
    text = re.sub(r'(\d+)\s+(0000000)', r'\1\2', text) 
    numbers = [int(n) for n in re.findall(r'\d+', text)]
    return max(numbers) if numbers else 0

def evaluate_dynamic_negotiation(transcript: str, forced_lang: str = "hinglish") -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    item_en = "Item"
    item_hi = "सामान"
    quoted = 0
    category = "general"

    print(f"\n[DEBUG] INPUT: '{transcript}'")
    
    # 1. Try the LLM
    if api_key:
        try:
            cache_buster = random.randint(1000, 9999)
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {
                            "role": "system", 
                            "content": f"""You are Bhaav-AI. Session ID: {cache_buster}.
                            Analyze the transcript. Extract:
                            1. item_en: English name.
                            2. item_hi: Hindi name.
                            3. price: The TOTAL price in INR.
                            4. category: 'electronics', 'clothing', 'grocery', or 'general'.
                            If no price is mentioned, return price: 0.
                            Return ONLY a JSON object."""
                        },
                        {"role": "user", "content": transcript}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                },
                timeout=5  # Increased timeout slightly
            )
            
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(data)
                item_en = str(parsed.get("item_en", "Item")).capitalize()
                item_hi = str(parsed.get("item_hi", "सामान")).strip()
                quoted = int(parsed.get("price", 0))
                category = parsed.get("category", "general").lower()
                print(f"[LLM SUCCESS] -> {parsed}")
            else:
                print(f"[LLM FAILED] Status: {res.status_code}")
        except Exception as e:
            print(f"[LLM FAILED] Exception: {e}")

    # 2. Python Fallback if LLM timed out or returned 0
    if quoted <= 0 or item_en == "Item":
        quoted = extract_digits_only(transcript)
        if quoted <= 0:
             return {
                 "transcript": transcript, "item": "Item", "quoted_price": 0, "fair_price": 0,
                 "counter_offer": 0, "overcharge_pct": 0, "status": "UNCERTAIN",
                 "whisper_advice": "Could not detect price.", "speech_script": "Bhaiya, kitna daam hai?",
                 "detected_language": forced_lang
             }
        
        # Smart fallback to extract the item name without LLM
        t_lower = transcript.lower()
        clean_text = re.sub(r'\d+', '', t_lower)
        stop_words = ["this", "that", "is", "the", "of", "a", "an", "for", "costs", "cost", "my", "it", "rupees", "rupaye", "ka", "ki", "hai", "ke", "in", "price", "का", "की", "है", "रुपये"]
        for word in stop_words:
            clean_text = re.sub(rf'\b{word}\b', '', clean_text)
        
        words = [w for w in clean_text.split() if len(w) > 1]
        if words:
            item_en = words[0].capitalize()
            item_hi = item_en
            # Fix common Hindi words
            if item_hi == "बैंगन": item_en, item_hi = "Brinjal", "बैंगन"
            if item_hi == "आलू": item_en, item_hi = "Potato", "आलू"
            if item_hi == "टमाटर": item_en, item_hi = "Tomato", "टमाटर"

    counter, fair = _compute_prices(quoted, category)
    overcharge_pct = int(((quoted - fair) / fair) * 100) if quoted > fair else 0

    if forced_lang == "hindi":
        item_display = f"{item_en} ({item_hi})" if item_en.lower() != item_hi.lower() else item_hi
        whisper = f"विक्रेता ने ₹{quoted} मांगे हैं। उचित दर ₹{fair} है। ₹{counter} की पेशकश करें।"
        script = f"भैया, {item_display} का ₹{quoted} बहुत ज़्यादा है। ₹{counter} में देना है तो बताओ।"
    elif forced_lang == "english":
        item_display = item_en
        whisper = f"Quoted ₹{quoted}. Estimated fair value is ₹{fair}. Offer ₹{counter} firmly."
        script = f"Brother, ₹{quoted} is too high for this {item_en.lower()}. I'll pay ₹{counter}."
    else:
        item_display = item_en
        whisper = f"Quoted ₹{quoted}. Fair price around ₹{fair}. Counter-offer ₹{counter} try karo."
        script = f"Bhaiya, {quoted} rupaye zyada lag raha hai. {counter} me dena hai toh bolo."

    return {
        "transcript": transcript, "item": item_display, "quoted_price": quoted, "fair_price": fair,
        "counter_offer": counter, "overcharge_pct": overcharge_pct, "status": "OVERCHARGED" if overcharge_pct > 0 else "FAIR",
        "whisper_advice": whisper, "speech_script": script, "detected_language": forced_lang
    }