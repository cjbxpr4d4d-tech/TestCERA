"""
scrapers.py — Módulo de extracción por plataforma
Cada función devuelve lista de dicts: {platform, date, user, content}
El sentimiento se aplica en main.py tras la extracción.
"""

import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("scrapers")

KEYWORDS = os.getenv(
    "KEYWORDS",
    "Paco Salazar,PSOE Argentina CERA,voto CERA Andalucía,Pilar Cancela,Ley Memoria Democrática"
).split(",")

TIKTOK_KEYWORDS = os.getenv(
    "TIKTOK_KEYWORDS",
    "Paco Salazar,voto CERA,Pilar Cancela"
).split(",")

INSTA_ACCOUNTS = os.getenv("INSTA_ACCOUNTS", "psoe_argentina,elespanol").split(",")
FB_PAGES = os.getenv("FB_PAGES", "PSOE,elespanolcom,rtve").split(",")

SINCE_DATE = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")


# ── X / Twitter (vía ntscraper — sin API key) ────────────────────────────────
def fetch_x(limit: int = 20) -> list:
    """
    Usa ntscraper (Nitter scraper) — no requiere API key de X.
    Instalar: pip install ntscraper
    """
    posts = []
    try:
        from ntscraper import Nitter
        scraper = Nitter(log_level=0, skip_instance_check=False)
        for kw in KEYWORDS[:3]:
            try:
                results = scraper.get_tweets(kw, mode="term", number=limit // 3, since=SINCE_DATE)
                for tweet in results.get("tweets", []):
                    posts.append({
                        "platform": "X",
                        "date": tweet.get("date", ""),
                        "user": tweet.get("user", {}).get("username", "unknown"),
                        "content": tweet.get("text", "")[:300],
                    })
            except Exception as e:
                logger.warning(f"X keyword '{kw}' error: {e}")
    except ImportError:
        logger.error("ntscraper no instalado. Ejecuta: pip install ntscraper")
    except Exception as e:
        logger.error(f"fetch_x error general: {e}")
    return posts


# ── Instagram (vía instaloader) ──────────────────────────────────────────────
def fetch_instagram(limit: int = 10) -> list:
    """
    Instaloader — acceso a perfiles públicos sin login (con rate limiting).
    Para perfiles privados se necesita: INSTA_USER + INSTA_PASS en env vars.
    Instalar: pip install instaloader
    """
    posts = []
    try:
        import instaloader
        L = instaloader.Instaloader(
            quiet=True,
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
        )
        # Login opcional (evita bloqueos)
        ig_user = os.getenv("INSTA_USER")
        ig_pass = os.getenv("INSTA_PASS")
        if ig_user and ig_pass:
            try:
                L.login(ig_user, ig_pass)
            except Exception as e:
                logger.warning(f"Instagram login failed: {e}")

        for acc in INSTA_ACCOUNTS:
            try:
                profile = instaloader.Profile.from_username(L.context, acc.strip())
                for post in list(profile.get_posts())[:limit // len(INSTA_ACCOUNTS)]:
                    caption = post.caption or ""
                    posts.append({
                        "platform": "Instagram",
                        "date": post.date.strftime("%Y-%m-%d"),
                        "user": acc.strip(),
                        "content": caption[:300],
                    })
            except Exception as e:
                logger.warning(f"Instagram account '{acc}' error: {e}")
    except ImportError:
        logger.error("instaloader no instalado. Ejecuta: pip install instaloader")
    except Exception as e:
        logger.error(f"fetch_instagram error general: {e}")
    return posts


# ── Facebook (vía facebook-scraper) ─────────────────────────────────────────
def fetch_facebook(limit: int = 15) -> list:
    """
    facebook-scraper — acceso a páginas públicas de Facebook.
    Instalar: pip install facebook-scraper
    """
    posts = []
    try:
        from facebook_scraper import get_posts
        for page in FB_PAGES:
            try:
                count = 0
                for post in get_posts(page.strip(), pages=2, timeout=15, extra_info=False):
                    text = post.get("text", "") or post.get("post_text", "") or ""
                    if not text:
                        continue
                    posts.append({
                        "platform": "Facebook",
                        "date": str(post.get("time", ""))[:10],
                        "user": page.strip(),
                        "content": text[:300],
                    })
                    count += 1
                    if count >= limit // len(FB_PAGES):
                        break
            except Exception as e:
                logger.warning(f"Facebook page '{page}' error: {e}")
    except ImportError:
        logger.error("facebook-scraper no instalado. Ejecuta: pip install facebook-scraper")
    except Exception as e:
        logger.error(f"fetch_facebook error general: {e}")
    return posts


# ── TikTok (vía TikTokApi) ──────────────────────────────────────────────────
def fetch_tiktok(limit: int = 10) -> list:
    """
    TikTokApi — requiere Playwright instalado para simular navegador.
    Instalar: pip install TikTokApi && python -m playwright install
    """
    posts = []
    try:
        import asyncio
        from TikTokApi import TikTokApi as TApi

        async def _scrape():
            results = []
            async with TApi() as api:
                await api.create_sessions(
                    ms_tokens=[os.getenv("TIKTOK_MS_TOKEN", "")],
                    num_sessions=1,
                    sleep_after=3,
                    headless=True,
                )
                for kw in TIKTOK_KEYWORDS[:2]:
                    try:
                        async for video in api.hashtag(name=kw).videos(count=limit // 2):
                            d = video.as_dict
                            text = d.get("desc", "")
                            results.append({
                                "platform": "TikTok",
                                "date": datetime.fromtimestamp(d.get("createTime", 0)).strftime("%Y-%m-%d"),
                                "user": d.get("author", {}).get("uniqueId", "unknown"),
                                "content": text[:300],
                            })
                    except Exception as e:
                        logger.warning(f"TikTok keyword '{kw}' error: {e}")
            return results

        loop = asyncio.new_event_loop()
        posts = loop.run_until_complete(_scrape())
        loop.close()

    except ImportError:
        logger.error("TikTokApi no instalado. Ejecuta: pip install TikTokApi && python -m playwright install")
    except Exception as e:
        logger.error(f"fetch_tiktok error general: {e}")
    return posts
