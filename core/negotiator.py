import re
import os
import requests

def _compute_prices(quoted: int) -> tuple:
    if quoted <= 0: return 0, 0
    if quoted <= 50:
        return max(quoted - 2, 5), max(quoted - 3, 4)
    elif quoted <= 1000:
        return int(quoted * 0.75), int(quoted * 0.80)
    else:
        return int(quoted * 0.70), int(quoted * 0.75)

def extract_price_from_text(text: str) -> int:
    text = text.lower().replace(',', '').replace('.', '')
    text = re.sub(r'\b(hazaar|hazar|thousand|k)\b', '000', text)
    text = re.sub(r'\b(hundred)\b', '00', text)
    text = re.sub(r'\b(lakh|lac)\b', '00000', text)
    text = re.sub(r'\b(million)\b', '000000', text)
    text = text.replace('हज़ार', '000').replace('हजार', '000').replace('लाख', '00000')
    text = re.sub(r'(\d)\s+(000)', r'\1\2', text)
    text = re.sub(r'(\d+)\s+(00000)', r'\1\2', text)
    text = re.sub(r'(\d+)\s+(000000)', r'\1\2', text)
    numbers = [int(n) for n in re.findall(r'\d+', text)]
    return max(numbers) if numbers else 0

def evaluate_dynamic_negotiation(transcript: str) -> dict:
    quoted = extract_price_from_text(transcript)
    if quoted <= 0:
        return {"detected_item": "Item", "quoted_price": 0, "estimated_fair_price": 0, "detected_language": "english"}
        
    counter, fair = _compute_prices(quoted)
    item_name = "Item"
    detected_language = "hinglish" # Default fallback
    
    # 1. Base Keyword Rules
    text_lower = transcript.lower()
    if "शिमला" in text_lower or "shimla" in text_lower: item_name = "Shimla Mirch"
    elif "लौकी" in text_lower or "lauki" in text_lower: item_name = "Lauki"
    elif "परवल" in text_lower or "parwal" in text_lower: item_name = "Parwal"
    elif "tv" in text_lower or "television" in text_lower or "टीवी" in text_lower: item_name = "TV"
    elif "laptop" in text_lower or "लैपटॉप" in text_lower: item_name = "Laptop"
    elif "phone" in text_lower or "mobile" in text_lower or "फोन" in text_lower: item_name = "Phone"

    # 2. Ask LLM for Item AND Language
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-20b",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "Analyze the transcript. Return ONLY a JSON object with two keys: 'item' (the item name) and 'language' (choose exactly one: 'english', 'hindi', or 'hinglish'). Example: {\"item\": \"laptop\", \"language\": \"english\"}"
                        },
                        {"role": "user", "content": transcript}
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                },
                timeout=3
            )
            if res.status_code == 200:
                data = res.json()["choices"][0]["message"]["content"]
                import json
                parsed = json.loads(data)
                
                # Update item if LLM found something and our keywords didn't catch it
                if item_name == "Item" and parsed.get("item"):
                     item_name = parsed["item"].capitalize()
                     
                # Update language
                if parsed.get("language"):
                    detected_language = parsed["language"].lower()
        except Exception as e:
            print(f"[!] LLM extraction skipped: {e}")

    # 3. Python Fallback for Item name if LLM failed
    if item_name == "Item" and transcript:
        words = transcript.split()
        if len(words) >= 2:
            item_name = f"{words[0]} {words[1]}".capitalize()
        elif len(words) == 1:
            item_name = words[0].capitalize()

    return {
        "detected_item": item_name,
        "quoted_price": quoted,
        "estimated_fair_price": fair,
        "detected_language": detected_language
    }