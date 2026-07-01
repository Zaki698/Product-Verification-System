import json
import re
from typing import Any, Dict

import google.generativeai as genai

from backend.validation_service.prompts import ocr_prompt
from config import *



def extract_dates_from_image(
    image_b64: str,
    mime_type: str = "image/jpeg",
) -> Dict[str, Any]:
    """Use Gemini Vision to extract manufacturing date and expiry date from a
    product label image.

    Args:
        image_b64: base64-encoded image bytes.
        mime_type: MIME type of the image (e.g. 'image/jpeg', 'image/png').

    Returns:
        dict with mfg_date (YYYY-MM-DD or None), expiry_date (YYYY-MM-DD or None),
        confidence (0.0-1.0), raw_text (raw model output for debugging).
    """

    api_key = GEMINI_API_KEY
    if not api_key:
        return {
            "success": False,
            "mfg_date": None,
            "expiry_date": None,
            "confidence": None,
            "raw_text": None,
            "error": "GOOGLE_API_KEY not set in environment.",
        }

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = ocr_prompt

    image_part = {"mime_type": mime_type, "data": image_b64}

    try:
        response = model.generate_content([image_part, prompt])
        raw_text = response.text.strip()
        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip().rstrip("`").strip()
        parsed = json.loads(cleaned)
        return {
            "success": True,
            "mfg_date": parsed.get("mfg_date"),
            "expiry_date": parsed.get("expiry_date"),
            "confidence": float(parsed.get("confidence", 0.0)),
            "raw_text": raw_text,
            "error": None,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "mfg_date": None,
            "expiry_date": None,
            "confidence": None,
            "raw_text": raw_text if "raw_text" in dir() else None,
            "error": f"Could not parse model JSON response: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "mfg_date": None,
            "expiry_date": None,
            "confidence": None,
            "raw_text": None,
            "error": str(e),
        }
