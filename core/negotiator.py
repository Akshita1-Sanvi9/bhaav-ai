import re
import os
import requests

def _compute_prices(quoted: int) -> tuple:
    if quoted <= 0: return 0, 0
    if quoted <= 50:
        # For very low prices, drop by 2 and 3
        return max(quoted - 2, 5), max(quoted - 3, 4)
    elif quoted <= 1000:
        return int(quoted * 0.75), int(quoted * 0.80)
    else:
        return int(quoted * 0.70), int(quoted * 0.75)

def extract_price_from_text(text: str) -> int:
    text = text.lower().replace(',', '').replace('.', '')
    text = re.sub(r'\b(hazaar|hazar|thousand|k)\b', '000', text)
    text = re.sub(r'\b(lakh|lac)\b', '00000', text)
    text = text.replace('हज़ार', '000').replace('हजार', '000').replace('लाख', '00000')
    text = re.sub(r'(\d)\s+(000)', r'\1\2', text)
    text = re.sub(r'(\d+)\s+(00000)', r'\1\2', text)
    numbers = [int(n) for n in re.findall(r'\d+', text)]
    return max(numbers) if numbers else 0

def evaluate_dynamic_negotiation(transcript: str) -> dict:
    quoted = extract_price_from_text(transcript)
    if quoted <= 0:
        return {"detected_item": "Item", "quoted_price": 0, "estimated_fair_price": 0}
        
    counter, fair = _compute_prices(quoted)
    item_name = "Item"
    
    # 1. Check for specific 2-word veggies first
    text_lower = transcript.lower()
    if "शिमला" in text_lower or "shimla" in text_lower:
        item_name = "Shimla Mirch"
    elif "लौकी" in text_lower or "lauki" in text_lower:
        item_name = "Lauki"
    elif "परवल" in text_lower or "parwal" in text_lower:
        item_name = "Parwal"
    else:
        # 2. Try the LLM with a strict few-shot prompt
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
                                "content": "You are an extraction bot. Extract only the item name. Example 1: 'टिंडे 100 किलो है' -> 'टिंडे'. Example 2: 'Ye laptop 50000 ka hai' -> 'laptop'. Reply with ONLY the word."
                            },
                            {"role": "user", "content": transcript}
                        ],
                        "temperature": 0.0, # Force deterministic output
                        "max_tokens": 10
                    },
                    timeout=3
                )
                if res.status_code == 200:
                    llm_item = res.json()["choices"][0]["message"]["content"].strip()
                    # Clean up punctuation but keep Hindi characters
                    llm_item = re.sub(r'[^\w\s\u0900-\u097F]', '', llm_item).strip()
                    if llm_item and len(llm_item) < 30 and "item" not in llm_item.lower():
                        item_name = llm_item
            except Exception as e:
                print(f"[!] LLM extraction skipped: {e}")

        # 3. If LLM failed, grab the first TWO words instead of one
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
    }