import re
import os
import requests
import json
import random

def extract_digits_only(text: str) -> int:
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

def evaluate_dynamic_negotiation(transcript: str, forced_lang: str = "hinglish", mode: str = "unsure") -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    item_en = "Item"
    item_hi = "सामान"
    quoted = 0
    fair = 0
    counter = 0
    status = "OVERCHARGED"
    speech_script = ""
    whisper_advice = ""

    print(f"\n[DEBUG] INPUT: '{transcript}', MODE: {mode}, LANG: {forced_lang}")
    
    if api_key:
        try:
            cache_buster = random.randint(1000, 9999)
            tactic_roll = random.randint(1, 4) 
            
            mode_instruction = ""
            if mode == "fair":
                mode_instruction = "The user thinks the price is FAIR. Do minimal bargaining (5% drop)."
            elif mode == "unsure_branded":
                mode_instruction = "The user is in a BRANDED store. Margins are fixed. Do very minimal bargaining (2-5% drop)."
            elif mode == "unsure_local":
                mode_instruction = "The user is in a LOCAL market. High markups exist. Bargain moderately (15-20% drop)."
            elif mode == "unfair":
                mode_instruction = "The user thinks the price is UNFAIR/TOO HIGH. Bargain aggressively (25-30% drop)."
            else:
                mode_instruction = "The user is unsure. Bargain moderately."

            system_prompt = f"""You are Bhaav-AI, an expert Indian street negotiator. Session: {cache_buster}.
            The vendor quoted a price. User's situation: {mode_instruction}
            
            CRITICAL RULES:
            1. The user's selected language is '{forced_lang}'. Write BOTH 'speech_script' and 'whisper_advice' strictly in this language.
            2. NEVER use the word "Unknown" or "अज्ञात" for the item name. If you don't know it, use "Saaman" (Hindi/Hinglish) or "Item" (English).
            3. SCRIPT TONE: Speak like a real Indian street customer. Use casual slang (e.g., "Bhaiya", "Mehnga hai", "Final karo", "Aage dekhta hoon"). NEVER use formal words like "deal", "accept", "situation", or "budget" (unless using the specific budget tactic).
            4. DO NOT use the word "offer" in the speech_script.
            5. FOR HINGLISH: Keep English nouns (like shirt, laptop, phone) in English letters. Do NOT transliterate them into Hindi spelling (e.g., DO NOT write "shaar" for "shirt"). It should read like: "Bhaiya, yeh shirt 500 ka hai, 300 me final karo."

            Analyze the transcript and determine:
            1. item_en: English name.
            2. item_hi: Hindi name.
            3. quoted_price: Integer.
            4. fair_price: Realistic market value.
            5. status: "FAIR", "OVERCHARGED", or "DELUSIONAL". 
            6. counter_offer: MUST be lower than fair_price.
            
            7. speech_script: What the user should say to the vendor. 
               - The script MUST be a full, natural sentence (at least 12-15 words). 
               - You MUST use Tactic #{tactic_roll} for this round:
                 Tactic 1: Compare to another shop (e.g., "Bagal wale X me de rahe hain")
                 Tactic 2: Mention last week's price (e.g., "Pichhle hafte X me mila tha")
                 Tactic 3: Play the budget card (e.g., "Mera budget sirf X hai")
                 Tactic 4: Ask for a round figure (e.g., "X me final kar do")
               - Replace X with the exact counter_offer number.
               
            8. whisper_advice: A full sentence of private strategy. MUST include the prices. 
               - Example: "Quoted 500, Fair 400. Counter 350. Mention the shop next door."

            Return ONLY a JSON object."""
            
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript}
                    ],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"}
                },
                timeout=6
            )
            
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                parsed = json.loads(data)
                
                item_en = re.sub(r'[^\w\s]', '', str(parsed.get("item_en", "Item"))).strip().capitalize()
                item_hi = re.sub(r'[^\w\s\u0900-\u097F]', '', str(parsed.get("item_hi", "सामान"))).strip()
                
                # HARD FIX: Catch every variation of "Unknown"
                if "unknown" in item_en.lower() or "item" in item_en.lower():
                    words = [w for w in transcript.lower().split() if len(w) > 2 and not w.isdigit()]
                    if words:
                        item_en = words[0].capitalize()
                        item_hi = item_en
                    else:
                        item_en = "Item"
                        item_hi = "सामान"

                quoted = int(parsed.get("quoted_price", 0))
                fair = int(parsed.get("fair_price", 0))
                counter = int(parsed.get("counter_offer", 0))
                status = parsed.get("status", "OVERCHARGED").upper()
                speech_script = parsed.get("speech_script", "")
                whisper_advice = parsed.get("whisper_advice", "")
                print(f"[LLM SUCCESS] -> {parsed}")
            else:
                print(f"[LLM FAILED] Status: {res.status_code}")
        except Exception as e:
            print(f"[LLM FAILED] Exception: {e}")

    # --- PYTHON SAFETY NET ---
    if quoted <= 0:
        quoted = extract_digits_only(transcript)
        if quoted <= 0:
             return {
                 "transcript": transcript, "item": "Item", "quoted_price": 0, "fair_price": 0,
                 "counter_offer": 0, "overcharge_pct": 0, "status": "UNCERTAIN",
                 "whisper_advice": "Could not detect price.", "speech_script": "Bhaiya, kitna daam hai?",
                 "detected_language": forced_lang
             }

    raw_number = extract_digits_only(transcript)
    if raw_number > 0 and abs(quoted - raw_number) > (raw_number * 0.5):
        quoted = raw_number

    if status == "DELUSIONAL" and quoted < fair:
        fair = quoted * 100 
        counter = fair
    elif status == "DELUSIONAL" and quoted > fair:
        fair = quoted * 0.1  
        counter = fair
    else:
        if fair <= 0 or fair >= quoted:
            fair = int(quoted * 0.75) 

        if counter <= 0 or counter >= fair:
            if mode == "unfair": counter = int(fair * 0.75)
            elif mode == "fair": counter = int(fair * 0.90)
            elif mode == "unsure_branded": counter = int(fair * 0.95)
            else: counter = int(fair * 0.85)

        if counter >= fair:
            counter = int(fair * 0.90)

    if status not in ["FAIR", "OVERCHARGED", "DELUSIONAL"]:
        if quoted > (fair * 4) or quoted < (fair * 0.2):
            status = "DELUSIONAL"
        else:
            status = "OVERCHARGED" if quoted > fair else "FAIR"

    overcharge_pct = int(((quoted - fair) / fair) * 100) if fair > 0 and quoted > fair else 0
    item_display = f"{item_en} ({item_hi})" if forced_lang == "hindi" and item_en.lower() != item_hi.lower() else item_en

    # Fallback if LLM fails or uses "offer" or formal words
    bad_words = ["offer", "accept", "deal", "situation"]
    if not speech_script or any(word in speech_script.lower() for word in bad_words) or not whisper_advice:
        if status == "DELUSIONAL":
            if forced_lang == "hindi":
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. ये दाम पागलपन है, मत लो।"
                speech_script = f"भैया, ₹{quoted} में तो कोई नहीं देगा। इसका सही रेट ₹{fair} है। मैं थोड़ा और देख लेता हूँ।"
            elif forced_lang == "english":
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. This is absurd, walk away."
                speech_script = f"Brother, ₹{quoted} is a joke. The actual price is around ₹{fair}. I'll look elsewhere."
            else:
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Yeh price toh mazaak hai, mat lo."
                speech_script = f"Bhaiya, ₹{quoted} toh bahut hi zyada hai. Iska sahi rate ₹{fair} hai. Main aage se dekhta hoon."
        else:
            # Smart Fallback Tactics (Longer Scripts)
            tactic = random.choice(["compare", "budget", "round"])
            
            if forced_lang == "hindi":
                if tactic == "compare":
                    speech_script = f"भैया, ये तो बहुत ज़्यादा है। मैंने बगल वाली दुकान पर ₹{counter} में देखा है। थोड़ा कम करो।"
                elif tactic == "budget":
                    speech_script = f"भैया, आपका सामान अच्छा है, लेकिन मेरा बजट सिर्फ ₹{counter} है। इसी में दे दो।"
                else:
                    speech_script = f"भैया, ₹{quoted} में तो बहुत मंहगा पड़ रहा है। चलो ₹{counter} में राउंड फिगर कर दो।"
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Counter ₹{counter}. Compare to another shop politely."
                
            elif forced_lang == "english":
                if tactic == "compare":
                    speech_script = f"Brother, this is too expensive. The shop next door is selling the same item for ₹{counter}. Can you match that?"
                elif tactic == "budget":
                    speech_script = f"Brother, I really like this item, but my budget is only ₹{counter}. Can we make it work?"
                else:
                    speech_script = f"Brother, ₹{quoted} is a bit high for me. Let's make it a round figure at ₹{counter} and close the deal."
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Counter ₹{counter}. Be firm but polite."
                
            else:
                if tactic == "compare":
                    speech_script = f"Bhaiya, yeh toh zyada lag raha hai. Maine bagal wali dukaan pe ₹{counter} me dekha hai. Thoda kam karo."
                elif tactic == "budget":
                    speech_script = f"Bhaiya, saman achha hai, par mera budget sirf ₹{counter} hai. Isi me de do, aage bhi lenge."
                else:
                    speech_script = f"Bhaiya, ₹{quoted} thoda zyada lag raha hai. Chalo ₹{counter} me round figure kar do, abhi le jaata hoon."
                whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. Counter ₹{counter}. Use comparison and be willing to walk away."

    if str(quoted) not in whisper_advice:
        whisper_advice = f"Quoted ₹{quoted}, Fair ₹{fair}. " + whisper_advice

    return {
        "transcript": transcript, "item": item_display, "quoted_price": quoted, "fair_price": fair,
        "counter_offer": counter, "overcharge_pct": overcharge_pct, "status": status,
        "whisper_advice": whisper_advice, "speech_script": speech_script, "detected_language": forced_lang
    }