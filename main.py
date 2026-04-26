"""
PSOE CERA Monitor — Backend FastAPI
Scrapers: X (via ntscraper), Instagram (instaloader), Facebook (facebook-scraper), TikTok (TikTokApi)
Sentimiento: TextBlob (ES via translate) + VADER
Despliegue: Railway
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json, os, logging
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler

from scrapers import fetch_x, fetch_instagram, fetch_facebook, fetch_tiktok
from sentiment import analyze_sentiment
from storage import load_data, save_data, append_entry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("psoe-monitor")

app = FastAPI(title="PSOE CERA Monitor API", version="2.0.0")

# ── CORS (permite peticiones desde Netlify) ──────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Scheduler diario ─────────────────────────────────────────────────────────
scheduler = BackgroundScheduler()

def daily_scrape_job():
    logger.info("▶ Iniciando scrape diario automático...")
    run_full_scrape()

scheduler.add_job(daily_scrape_job, "cron", hour=8, minute=0)
scheduler.start()


# ── Core scrape logic ────────────────────────────────────────────────────────
def run_full_scrape() -> dict:
    logger.info("Iniciando scrape completo de todas las plataformas...")

    all_posts = []
    errors = []

    for platform, fetcher in [
        ("X", fetch_x),
        ("Instagram", fetch_instagram),
        ("Facebook", fetch_facebook),
        ("TikTok", fetch_tiktok),
    ]:
        try:
            posts = fetcher()
            # Añadir sentimiento a cada post
            for p in posts:
                p["sentiment"] = analyze_sentiment(p.get("content", ""))
            all_posts.extend(posts)
            logger.info(f"✓ {platform}: {len(posts)} posts recogidos")
        except Exception as e:
            logger.error(f"✗ {platform} error: {e}")
            errors.append({"platform": platform, "error": str(e)})

    sentiments = [p["sentiment"] for p in all_posts if isinstance(p["sentiment"], float)]
    avg_sentiment = round(sum(sentiments) / max(len(sentiments), 1), 4)

    platform_count = {}
    for p in all_posts:
        platform_count[p["platform"]] = platform_count.get(p["platform"], 0) + 1

    # Frecuencia de palabras clave
    from collections import Counter
    import re
    all_text = " ".join(p.get("content", "") for p in all_posts).lower()
    words = re.findall(r"\b\w{4,}\b", all_text)
    stopwords = {"para","este","esta","como","pero","más","que","los","las","una","uno","con","por","del","sus","sin","sobre"}
    word_freq = Counter(w for w in words if w not in stopwords).most_common(20)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "combined_sentiment": avg_sentiment,
        "total_posts": len(all_posts),
        "platform_count": platform_count,
        "word_freq": [{"word": w, "freq": f} for w, f in word_freq],
        "sample": all_posts[:30],
        "errors": errors,
    }

    append_entry(entry)
    logger.info(f"✓ Scrape completado. Total posts: {len(all_posts)}, sentimiento: {avg_sentiment}")
    return entry


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "online", "service": "PSOE CERA Monitor API v2.0"}


@app.get("/api/status")
def status():
    data = load_data()
    return {
        "last_update": data.get("last_update"),
        "total_entries": len(data.get("history", [])),
        "current_sentiment": data.get("history", [{}])[-1].get("combined_sentiment", 0) if data.get("history") else 0,
        "platforms_active": 4,
    }


@app.get("/api/history")
def get_history(days: int = 30):
    data = load_data()
    history = data.get("history", [])[-days:]
    return {"history": history, "count": len(history)}


@app.get("/api/feed")
def get_feed(platform: str = None, limit: int = 30):
    data = load_data()
    if not data.get("history"):
        return {"posts": [], "count": 0}
    latest = data["history"][-1]
    posts = latest.get("sample", [])
    if platform and platform != "Todos":
        posts = [p for p in posts if p.get("platform") == platform]
    return {"posts": posts[:limit], "count": len(posts)}


@app.get("/api/wordfreq")
def get_wordfreq(days: int = 7):
    data = load_data()
    history = data.get("history", [])[-days:]
    from collections import Counter
    combined = Counter()
    for entry in history:
        for item in entry.get("word_freq", []):
            combined[item["word"]] += item["freq"]
    return {"word_freq": [{"word": w, "freq": f} for w, f in combined.most_common(20)]}


@app.get("/api/sentiment-series")
def get_sentiment_series(days: int = 30):
    data = load_data()
    history = data.get("history", [])[-days:]
    series = [
        {
            "date": e["timestamp"][:10],
            "sentiment": e.get("combined_sentiment", 0),
            **e.get("platform_count", {}),
            "total": e.get("total_posts", 0),
        }
        for e in history
    ]
    return {"series": series}


@app.post("/api/update")
async def trigger_update(background_tasks: BackgroundTasks):
    """Trigger manual scrape (runs async en background)"""
    background_tasks.add_task(run_full_scrape)
    return {"status": "started", "message": "Scrape iniciado en background. Refresca /api/status en ~60s."}


@app.get("/api/scenarios")
def get_scenarios():
    """Escenarios electorales Andalucía 2026 — actualizados manualmente"""
    return {
        "scenarios": [
            {"escenario": "Base (status quo)", "pp": 55, "psoe": 28, "vox": 17, "necesita_vox": False, "prob": 30},
            {"escenario": "CERA favorable PP", "pp": 57, "psoe": 26, "vox": 17, "necesita_vox": False, "prob": 20},
            {"escenario": "CERA + LMD favorable PSOE", "pp": 52, "psoe": 33, "vox": 15, "necesita_vox": True, "prob": 35},
            {"escenario": "CERA muy favorable PSOE", "pp": 49, "psoe": 37, "vox": 14, "necesita_vox": True, "prob": 15},
        ]
    }
