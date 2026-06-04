import json
import logging
import os
from typing import Tuple
import httpx
from .config import settings

logger = logging.getLogger("app.ai_engine")

async def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Asynchronously analyze the sentiment of a given text using Google Gemini 2.5 Flash API
    with direct REST HTTP request.

    Args:
        text (str): The input text to analyze.

    Returns:
        Tuple[str, float]: A tuple containing the sentiment label ('positif', 'negatif', or 'netral')
                           and the confidence score (float).
    """
    gemini_api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    
    if not gemini_api_key:
        logger.error("Gemini API key (GEMINI_API_KEY) is not set in environment or config. Using lexical fallback.")
        return _fallback_lexical_analysis(text)

    # Gemini REST API URL (using gemini-2.5-flash)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
    
    prompt = (
        "Anda adalah analis sentimen ahli dalam bahasa Indonesia dan dialek daerah (seperti bahasa Aceh/Gayo). "
        "Tentukan sentimen dari teks berikut apakah positif (pos), negatif (neg), atau netral. "
        "Perhatikan konteks sarkasme, sindiran, dialek lokal, dan singkatan khas media sosial.\n\n"
        f"Teks: {text}"
    )

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "sentimen": {
                        "type": "STRING",
                        "enum": ["pos", "neg", "netral"]
                    },
                    "confidence": {
                        "type": "NUMBER"
                    }
                },
                "required": ["sentimen", "confidence"]
            }
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Parse the structured JSON output from Gemini response
            candidates = result.get("candidates", [])
            if not candidates:
                logger.warning("No candidates found in Gemini API response. Using lexical fallback.")
                return _fallback_lexical_analysis(text)
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                logger.warning("No parts found in Gemini API candidate. Using lexical fallback.")
                return _fallback_lexical_analysis(text)
                
            text_response = parts[0].get("text", "").strip()
            data = json.loads(text_response)
            
            sentimen = data.get("sentimen", "netral")
            confidence = float(data.get("confidence", 0.8))
            
            # Map labels to the output values ('positif', 'negatif', 'netral') expected by the caller
            label_map = {
                "pos": "positif",
                "neg": "negatif",
                "netral": "netral"
            }
            sentiment_label = label_map.get(sentimen, "netral")
            
            return sentiment_label, confidence

    except httpx.HTTPStatusError as e:
        logger.error("Gemini API returned status code %s: %s", e.response.status_code, e.response.text)
        return _fallback_lexical_analysis(text)
    except httpx.RequestError as e:
        logger.warning("Network connection error while contacting Gemini API: %s. Using lexical fallback.", e)
        return _fallback_lexical_analysis(text)
    except Exception as e:
        logger.error("Unexpected error parsing Gemini response: %s. Using lexical fallback.", e)
        return _fallback_lexical_analysis(text)

def _fallback_lexical_analysis(text: str) -> Tuple[str, float]:
    """
    A simple lexical fallback used when the Gemini API is unreachable or fails.
    """
    text_lower = text.lower()
    pos_words = ["bantu", "dukung", "baik", "positif", "sukses", "meningkat", "cepat", "aman", "solusi", "apresiasi", "setuju", "maju"]
    neg_words = ["buruk", "rusak", "tolak", "gagal", "turun", "lambat", "bahaya", "masalah", "kecewa", "korupsi", "bencana", "protes"]
    
    pos_count = sum(1 for w in pos_words if w in text_lower)
    neg_count = sum(1 for w in neg_words if w in text_lower)
    
    if pos_count > neg_count:
        return "positif", 0.6 + (0.05 * pos_count)
    elif neg_count > pos_count:
        return "negatif", 0.6 + (0.05 * neg_count)
    else:
        return "netral", 0.5
