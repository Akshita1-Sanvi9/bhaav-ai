"""
core/market_index.py
Provides baseline fair market rates (in INR) and unit thresholds 
for common street micro-transactions in India.
"""

MARKET_INDEX = {
    "auto": {
        "fair_rate": 120,
        "unit": "trip",
        "margin_threshold": 0.25,
        "display_name": "Auto / Taxi Fare"
    },
    "potato": {
        "fair_rate": 25,
        "unit": "kg",
        "margin_threshold": 0.20,
        "display_name": "Potatoes (Aloo)"
    },
    "onion": {
        "fair_rate": 35,
        "unit": "kg",
        "margin_threshold": 0.20,
        "display_name": "Onions (Pyaz)"
    },
    "tomato": {
        "fair_rate": 30,
        "unit": "kg",
        "margin_threshold": 0.20,
        "display_name": "Tomatoes (Tamatar)"
    },
    "apple": {
        "fair_rate": 100,
        "unit": "kg",
        "margin_threshold": 0.15,
        "display_name": "Apples (Seb)"
    },
    "laundry": {
        "fair_rate": 10,
        "unit": "piece",
        "margin_threshold": 0.15,
        "display_name": "Ironing / Laundry"
    },
    "repairs": {
        "fair_rate": 250,
        "unit": "service",
        "margin_threshold": 0.20,
        "display_name": "Local Minor Repairs"
    },
    "electronics": {
        "fair_rate": 150,
        "unit": "item",
        "margin_threshold": 0.25,
        "display_name": "Basic Accessories / Cables"
    },
    "general_item": {
        "fair_rate": 100,
        "unit": "item",
        "margin_threshold": 0.20,
        "display_name": "General Goods"
    }
}


def get_fair_rate(item_name: str) -> dict:
    """
    Returns fair market baseline dictionary for a given item key,
    or falls back safely to 'general_item'.
    """
    item_key = item_name.lower().strip() if item_name else "general_item"
    return MARKET_INDEX.get(item_key, MARKET_INDEX["general_item"])