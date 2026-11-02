import re
from typing import Dict, Any

def extract_price_and_item(transcript: str) -> Dict[str, Any]:
    """
    Production-grade extractor that distinguishes item quantities from monetary price quotes
    in noisy, code-mixed street dialogue.
    """
    if not transcript or not transcript.strip():
        return {
            "raw_transcript": "",
            "quoted_price": None,
            "detected_item": "unknown"
        }

    transcript_clean = transcript.lower().strip()
    
    # 1. Prioritize explicit currency markers (High Confidence)
    explicit_patterns = [
        r'(?:rs\.?|rupees?|rupaye|inr|₹)\s*[:\=]?\s*(\d+)',
        r'(\d+)\s*(?:rs\.?|rupees?|rupaye|inr|\/\-|/-)',
    ]
    
    extracted_price = None
    for pattern in explicit_patterns:
        match = re.search(pattern, transcript_clean)
        if match:
            val = int(match.group(1))
            if val > 0:
                extracted_price = val
                break

    # 2. Heuristic Fallback: If no explicit currency tag, analyze all numbers in the sentence
    if not extracted_price:
        all_numbers = [int(n) for n in re.findall(r'\d+', transcript_clean)]
        if all_numbers:
            # Street commerce heuristic: Quantities are usually small (1-5 kg/pcs), 
            # while prices are larger. Filter out tiny numbers if larger ones exist.
            valid_prices = [n for n in all_numbers if n > 5]
            if valid_prices:
                extracted_price = max(valid_prices) # Pick the highest logical price value
            else:
                extracted_price = max(all_numbers)

    # 3. Comprehensive Commodity & Service Keyword Dictionary
    item_keywords = {
        "auto": ["auto", "rickshaw", "cab", "ride", "drop", "station", "fare", "meter"],
        "potato": ["aloo", "potatoes", "potato", "aaloo"],
        "onion": ["pyaz", "pyaaz", "onions", "onion"],
        "tomato": ["tamatar", "tomatoes", "tomato"],
        "apple": ["seb", "apples", "apple"],
        "laundry": ["dhobi", "clothes", "ironing", "press", "kapde"],
        "repairs": ["plumber", "electrician", "repair", "service", "fix"],
        "electronics": ["charger", "cable", "phone", "adapter", "battery"]
    }

    detected_item = "general_item"
    for item, keywords in item_keywords.items():
        if any(kw in transcript_clean for kw in keywords):
            detected_item = item
            break

    return {
        "raw_transcript": transcript,
        "quoted_price": extracted_price,
        "detected_item": detected_item
    }