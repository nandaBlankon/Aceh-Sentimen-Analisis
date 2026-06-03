import logging
import os
from typing import Tuple
import httpx
from .config import settings

logger = logging.getLogger("app.ai_engine")

# Hugging Face Inference API URL for the indobert-base-p2 model
API_URL = "https://api-inference.huggingface.co/models/indobenchmark/indobert-base-p2"

async def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Asynchronously analyze the sentiment of a given text using the Hugging Face Inference API
    with the 'indobenchmark/indobert-base-p2' model.

    Args:
        text (str): The input text to analyze.

    Returns:
        Tuple[str, float]: A tuple containing the sentiment label ('positif', 'negatif', or 'netral')
                           and the confidence score (float).

    Raises:
        ValueError: If configuration is invalid or the model output is malformed.
        RuntimeError: If the API request fails or the model is loading.
    """
    # Retrieve HF_TOKEN securely from settings (or directly from environment if settings is not set/overridden)
    hf_token = settings.hf_token or os.environ.get("HF_TOKEN")
    
    # Secure validation: Check if HF_TOKEN is configured.
    # Do NOT fall back to default or hardcoded credential values.
    if not hf_token:
        # TODO(security): Raise configuration error if secret is missing to prevent silent fallback or insecure defaults
        logger.error("Hugging Face API token (HF_TOKEN) is not set in environment or config.")
        raise ValueError("HF_TOKEN environment variable is not configured.")

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": text
    }

    try:
        # Use httpx.AsyncClient to perform the asynchronous POST request
        # Explicit timeout configured to prevent request hanging indefinitely
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, json=payload, headers=headers)
            
            # Secure error handling: raise for HTTP status errors but log details privately, returning a generic error
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Hugging Face API error (Status: %s): %s", e.response.status_code, e.response.text)
        raise RuntimeError("Failed to analyze sentiment due to Hugging Face API error.") from e
    except httpx.RequestError as e:
        logger.warning("Network connection error while contacting Hugging Face API: %s. Using lexical fallback.", e)
        return _fallback_lexical_analysis(text)
    except Exception as e:
        logger.error("Unexpected error during API call or response parsing: %s", e)
        raise RuntimeError("An unexpected error occurred during sentiment analysis.") from e

def _fallback_lexical_analysis(text: str) -> Tuple[str, float]:
    """
    A simple lexical fallback used when the Hugging Face API is unreachable (e.g. DNS issues).
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

    # Hugging Face Inference API may return an error dictionary, for example when the model is still loading
    if isinstance(result, dict) and "error" in result:
        error_msg = result.get("error", "Unknown API error")
        estimated_time = result.get("estimated_time", "unknown")
        logger.error("Hugging Face API returned error: %s (estimated loading time: %s)", error_msg, estimated_time)
        raise RuntimeError(f"Hugging Face model is not ready: {error_msg}")

    # Typical Hugging Face sequence classification response structure is:
    # [[{"label": "LABEL_0", "score": 0.8}, {"label": "LABEL_1", "score": 0.15}, ...]]
    # or sometimes just:
    # [{"label": "LABEL_0", "score": 0.8}, ...]
    predictions = None
    if isinstance(result, list):
        if len(result) > 0 and isinstance(result[0], list):
            predictions = result[0]
        else:
            predictions = result

    if not predictions or not isinstance(predictions, list):
        logger.error("Invalid or unexpected response structure from Hugging Face API: %s", result)
        raise ValueError("Received invalid response structure from sentiment analysis service.")

    # Find the prediction with the highest confidence score
    best_prediction = None
    for pred in predictions:
        if not isinstance(pred, dict) or "label" not in pred or "score" not in pred:
            continue
        if best_prediction is None or pred["score"] > best_prediction["score"]:
            best_prediction = pred

    if not best_prediction:
        logger.error("No valid predictions with label and score found in HF response: %s", predictions)
        raise ValueError("Sentiment analysis model did not return any valid predictions.")

    raw_label = best_prediction["label"]
    confidence_score = float(best_prediction["score"])

    # Map the model's raw label to the required: 'positif', 'negatif', 'netral'
    # We support typical fine-tuning label patterns:
    # - LABEL_0, LABEL_1, LABEL_2 for standard IndoNLU / IndoBERT classification datasets
    # - English classification words (positive, negative, neutral)
    # - Common variations (pos, neg, neu, net)
    label_map = {
        "LABEL_0": "negatif",
        "LABEL_1": "netral",
        "LABEL_2": "positif",
        "POSITIVE": "positif",
        "NEGATIVE": "negatif",
        "NEUTRAL": "netral",
        "POS": "positif",
        "NEG": "negatif",
        "NEU": "netral",
        "NET": "netral",
        "POSITIF": "positif",
        "NEGATIF": "negatif",
        "NETRAL": "netral"
    }

    # Match normalized label (uppercase, stripped)
    normalized_label = str(raw_label).strip().upper()
    sentiment_label = label_map.get(normalized_label)

    if not sentiment_label:
        # Secure warning for developer debugging while maintaining graceful fallback to netral
        logger.warning("Unrecognized raw sentiment label from model: '%s'. Defaulting to 'netral'.", raw_label)
        sentiment_label = "netral"

    return sentiment_label, confidence_score
