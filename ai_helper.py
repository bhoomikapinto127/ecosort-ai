"""
ai_helper.py
Uses the Groq API (Llama vision model) to classify an uploaded waste
image into one of: Plastic, Organic, Hazardous, E-Waste, Others.

"Others" covers anything that doesn't belong in one of the 4 physical
smart bins (e.g. glass, mixed/general waste) - it still gets logged for
the Waste Distribution pie chart on the dashboard.

Setup:
    pip install groq python-dotenv
    Put GROQ_API_KEY=your-key-here in a .env file in the project root
    (or export it as an environment variable directly)

Get a free key at https://console.groq.com/keys
"""

import os
import base64
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # reads GROQ_API_KEY from a .env file in the project root, if present

# Any current Groq vision-capable model works here, e.g.:
#   "llama-3.2-90b-vision-preview" or "llama-3.2-11b-vision-preview"
# Check https://console.groq.com/docs/vision for the latest model name.
MODEL_NAME = "qwen/qwen3.6-27b"


VALID_CATEGORIES = ["Plastic", "Organic", "Hazardous", "E-Waste", "Others"]

_api_key = os.environ.get("GROQ_API_KEY")
if not _api_key:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Add GROQ_API_KEY=your-key-here to a .env "
        "file in the project root, or run: $env:GROQ_API_KEY=\"your-key-here\" "
        "(PowerShell) before starting the app."
    )

client = Groq(api_key=_api_key)


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
        "You are a waste-sorting AI for a smart bin system. Carefully examine "
        "the entire image before answering - don't guess based on a quick "
        "glance. If the image shows a single item, identify that item. If it "
        "shows a bin or pile with multiple items, identify the waste material "
        "that visually makes up the largest share of what's in the image (by "
        "volume, not just what's brightest or most colorful), and name that "
        "material specifically rather than a single object within it. "
        "Classify it into exactly one of these categories: "
        "Plastic, Organic, Hazardous, E-Waste, Others. "
        "Use 'Others' only if the item genuinely doesn't fit the first four "
        "(e.g. glass, textiles, mixed/general waste). "
        "Set confidence lower (below 0.7) if the image is cluttered, mixed, "
        "or the item is ambiguous - don't report high confidence unless "
        "you're actually looking at one clear, unobstructed item. "
        "Respond with ONLY valid JSON, no markdown, no extra text, in this exact shape: "
        '{"item": "<short item or material name>", "category": "<one of the 5 categories>", '
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
        max_tokens=800,
        reasoning_effort="none",
    )

    raw = response.choices[0].message.content.strip()
    print("\n========== MODEL RESPONSE ==========")
    print(raw)
    print("====================================\n")

    # Strip accidental markdown fences
    raw = response.choices[0].message.content.strip()

    print("RAW RESPONSE:")
    print(raw)

# Remove markdown
    raw = raw.replace("```json", "").replace("```", "").strip()

# Remove thinking section if present
    if "</think>" in raw:
      raw = raw.split("</think>")[-1].strip()

# Keep only the JSON
    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end != -1:
     raw = raw[start:end+1]

     print("FINAL JSON:")
     print(raw)

    try:
        result = json.loads(raw)
        category = result.get("category", "Others")
        if category not in VALID_CATEGORIES:
            category = "Others"
        return {
            "item": result.get("item", "Unknown item"),
            "category": category,
            "confidence": float(result.get("confidence", 0.85)),
            "tip": result.get("tip", "Please dispose of this responsibly."),
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print("PARSE ERROR:", repr(e), flush=True)
        print("RAW THAT FAILED TO PARSE:", repr(raw), flush=True)
        return {
            "item": "Unrecognized item",
            "category": "Others",
            "confidence": 0.5,
            "tip": "Could not confidently classify — please check manually.",
        }
    print("\n========== MODEL RESPONSE ==========", flush=True)
    print(raw, flush=True)
    print("====================================\n", flush=True)
  