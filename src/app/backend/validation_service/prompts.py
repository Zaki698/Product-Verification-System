ocr_prompt = """Carefully examine this product label image.
Find the manufacturing date (may appear as MFG, Mfg Date, Manufactured On,Production Date, DOM, etc.) and the expiry date (may appear as Expiry,Best Before, Use By, BBD, EXP, Expires On, etc.).
Return ONLY a valid JSON object with no markdown, no explanation, no extra text.

Use this exact format:\n
    '{"mfg_date": "YYYY-MM-DD", "expiry_date": "YYYY-MM-DD", "confidence": 0.95}\n'

If a date is partially visible or unclear, try to parse it and lower the confidence.
If a date is completely missing or unreadable, use null for that field.
Always convert dates to YYYY-MM-DD format regardless of how they appear on the label.
"""