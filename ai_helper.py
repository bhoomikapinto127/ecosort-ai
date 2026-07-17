"""
ai_helper.py
Uses the Groq API (Llama vision model) to classify an uploaded waste
image into one of: Plastic, Organic, Hazardous, E-Waste.

Setup:
    pip install groq
    export GROQ_API_KEY="your-key-here"

Get a free key at https://console.groq.com/keys
"""

import os
import base64
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Any current Groq vision-capable model works here, e.g.:
#   "llama-3.2-90b-vision-preview" or "llama-3.2-11b-vision-preview"
# Check https://console.groq.com/docs/vision for the latest model name.
MODEL_NAME = "llama-3.2-90b-vision-preview"

VALID_CATEGORIES = ["Plastic", "Organic", "Hazardous", "E-Waste"]

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def _encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def classify_waste_image(image_path):
    """
    Sends the image to Groq's vision model and returns a dict:
        {
            "item": "Plastic Bottle",
            "category": "Plastic",
            "confidence": 0.97,
            "tip": "Rinse and remove the cap before recycling."
        }
    Falls back to a safe default if the model output can't be parsed.
    """
    base64_image = _encode_image(image_path)

    prompt = (
        "You are a waste-sorting AI. Look at the image and identify the item. "
        "Classify it into exactly one of these categories: "
        "Plastic, Organic, Hazardous, E-Waste. "
        "Respond with ONLY valid JSON, no markdown, no extra text, in this exact shape: "
        '{"item": "<short item name>", "category": "<one of the 4 categories>", '
        '"confidence": <number 0-1>, "tip": "<one short disposal tip>"}'
    )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        temperature=0.2,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    try:
        result = json.loads(raw)
        category = result.get("category", "Plastic")
        if category not in VALID_CATEGORIES:
            category = "Plastic"
        return {
            "item": result.get("item", "Unknown item"),
            "category": category,
            "confidence": float(result.get("confidence", 0.85)),
            "tip": result.get("tip", "Please dispose of this responsibly."),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        # Safe fallback so the demo never crashes on a bad model response
        return {
            "item": "Unrecognized item",
            "category": "Plastic",
            "confidence": 0.5,
            "tip": "Could not confidently classify — please check manually.",
        }