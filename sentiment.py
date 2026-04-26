"""
sentiment.py — Análisis de sentimiento multilingüe
Estrategia: VADER (rápido) como base + TextBlob como fallback
Para textos en español usa langdetect + traducción automática si disponible.
"""

import logging

logger = logging.getLogger("sentiment")

# Cache del analizador VADER para no reinstanciar en cada llamada
_vader = None

def _get_vader():
    global _vader
    if _vader is None:
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader = SentimentIntensityAnalyzer()
        except ImportError:
            logger.warning("vaderSentiment no disponible")
    return _vader


def analyze_sentiment(text: str) -> float:
    """
    Devuelve un float entre -1.0 (muy negativo) y +1.0 (muy positivo).
    Estrategia en cascada:
    1. VADER sobre el texto original (funciona razonablemente en ES)
    2. Si falla, TextBlob
    3. Si falla, 0.0
    """
    if not text or not text.strip():
        return 0.0

    text = text[:500]  # Limitar longitud para performance

    # Intentar VADER primero (más preciso en redes sociales)
    vader = _get_vader()
    if vader:
        try:
            scores = vader.polarity_scores(text)
            return round(scores["compound"], 4)
        except Exception as e:
            logger.debug(f"VADER error: {e}")

    # Fallback: TextBlob
    try:
        from textblob import TextBlob
        blob = TextBlob(text)
        return round(blob.sentiment.polarity, 4)
    except Exception as e:
        logger.debug(f"TextBlob error: {e}")

    return 0.0
