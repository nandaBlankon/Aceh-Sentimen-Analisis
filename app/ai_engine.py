import asyncio
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
    directly, or via 9Router (OpenAI-compatible gateway) if configured.

    Args:
        text (str): The input text to analyze.

    Returns:
        Tuple[str, float]: A tuple containing the sentiment label ('positif', 'negatif', or 'netral')
                           and the confidence score (float).
    """
    ninerouter_base = settings.ninerouter_api_base
    ninerouter_key = settings.ninerouter_api_key
    gemini_api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    
    # 1. Fallback immediately if no provider credentials exist
    if not ninerouter_base and not gemini_api_key:
        logger.error("Neither 9Router nor Gemini API key is configured. Using lexical fallback.")
        return _fallback_lexical_analysis(text)

    prompt = (
        "Anda adalah analis sentimen ahli dalam bahasa Indonesia dan dialek daerah (seperti bahasa Aceh/Gayo). "
        "Tentukan sentimen dari teks berikut apakah positif (pos), negatif (neg), atau netral. "
        "Perhatikan konteks sarkasme, sindiran, dialek lokal, dan singkatan khas media sosial.\n\n"
        f"Teks: {text}"
    )

    headers = {
        "Content-Type": "application/json"
    }

    # 2. Setup URL and payload based on config
    if ninerouter_base:
        url = f"{ninerouter_base.rstrip('/')}/chat/completions"
        if ninerouter_key:
            headers["Authorization"] = f"Bearer {ninerouter_key}"
            
        payload = {
            "model": settings.ninerouter_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {
                "type": "json_object"
            }
        }
    else:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
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

    max_retries = 3
    retry_delay = 2.0  # base delay in seconds

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Check for rate limit status (429)
                if response.status_code == 429:
                    if attempt < max_retries:
                        sleep_time = retry_delay * (2 ** attempt)
                        logger.warning("AI provider returned 429. Attempt %d/%d. Retrying in %s seconds...", attempt + 1, max_retries, sleep_time)
                        await asyncio.sleep(sleep_time)
                        continue
                
                response.raise_for_status()
                result = response.json()
                
                # 3. Parse output structure based on route
                if ninerouter_base:
                    choices = result.get("choices", [])
                    if not choices:
                        raise ValueError("No choices found in 9Router response.")
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content.startswith("```"):
                        content = content.strip("`").replace("json", "", 1).strip()
                    data = json.loads(content)
                else:
                    candidates = result.get("candidates", [])
                    if not candidates:
                        raise ValueError("No candidates found in Gemini response.")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise ValueError("No parts found in Gemini candidate.")
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
            if e.response.status_code == 429 and attempt < max_retries:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning("AI provider returned 429 (HTTPStatusError). Attempt %d/%d. Retrying in %s seconds...", attempt + 1, max_retries, sleep_time)
                await asyncio.sleep(sleep_time)
                continue
            logger.error("AI provider returned status code %s: %s", e.response.status_code, e.response.text)
            return _fallback_lexical_analysis(text)
        except httpx.RequestError as e:
            if attempt < max_retries:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning("Network connection error: %s. Attempt %d/%d. Retrying in %s seconds...", e, attempt + 1, max_retries, sleep_time)
                await asyncio.sleep(sleep_time)
                continue
            logger.warning("Network connection error while contacting AI provider: %s. Using lexical fallback.", e)
            return _fallback_lexical_analysis(text)
        except Exception as e:
            logger.error("Unexpected error parsing AI response: %s. Using lexical fallback.", e)
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
