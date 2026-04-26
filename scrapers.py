import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(“scrapers”)

KEYWORDS = os.getenv(
“KEYWORDS”,
“Paco Salazar,PSOE Argentina CERA,voto CERA Andalucia,Pilar Cancela,Ley Memoria Democratica”
).split(”,”)

INSTA_ACCOUNTS = os.getenv(“INSTA_ACCOUNTS”, “psoe_argentina,elespanol”).split(”,”)
FB_PAGES = os.getenv(“FB_PAGES”, “PSOE,elespanolcom,rtve”).split(”,”)
SINCE_DATE = (datetime.now() - timedelta(days=7)).strftime(”%Y-%m-%d”)

def fetch_x(limit=20):
posts = []
try:
from ntscraper import Nitter
scraper = Nitter(log_level=0, skip_instance_check=False)
for kw in KEYWORDS[:3]:
try:
results = scraper.get_tweets(kw, mode=“term”, number=limit // 3, since=SINCE_DATE)
for tweet in results.get(“tweets”, []):
posts.append({
“platform”: “X”,
“date”: tweet.get(“date”, “”),
“user”: tweet.get(“user”, {}).get(“username”, “unknown”),
“content”: tweet.get(“text”, “”)[:300],
})
except Exception as e:
logger.warning(“X keyword %s: %s”, kw, e)
except Exception as e:
logger.error(“fetch_x error: %s”, e)
return posts

def fetch_instagram(limit=10):
posts = []
try:
import instaloader
L = instaloader.Instaloader(
quiet=True, download_pictures=False, download_videos=False,
download_video_thumbnails=False, download_geotags=False,
download_comments=False, save_metadata=False,
)
ig_user = os.getenv(“INSTA_USER”)
ig_pass = os.getenv(“INSTA_PASS”)
if ig_user and ig_pass:
try:
L.login(ig_user, ig_pass)
except Exception as e:
logger.warning(“Instagram login failed: %s”, e)
for acc in INSTA_ACCOUNTS:
try:
profile = instaloader.Profile.from_username(L.context, acc.strip())
n = max(limit // max(len(INSTA_ACCOUNTS), 1), 1)
for post in list(profile.get_posts())[:n]:
posts.append({
“platform”: “Instagram”,
“date”: post.date.strftime(”%Y-%m-%d”),
“user”: acc.strip(),
“content”: (post.caption or “”)[:300],
})
except Exception as e:
logger.warning(“Instagram %s: %s”, acc, e)
except Exception as e:
logger.error(“fetch_instagram error: %s”, e)
return posts

def fetch_facebook(limit=15):
posts = []
try:
from facebook_scraper import get_posts
for page in FB_PAGES:
try:
count = 0
per_page = max(limit // max(len(FB_PAGES), 1), 1)
for post in get_posts(page.strip(), pages=2, timeout=15, extra_info=False):
text = post.get(“text”, “”) or post.get(“post_text”, “”) or “”
if not text:
continue
posts.append({
“platform”: “Facebook”,
“date”: str(post.get(“time”, “”))[:10],
“user”: page.strip(),
“content”: text[:300],
})
count += 1
if count >= per_page:
break
except Exception as e:
logger.warning(“Facebook %s: %s”, page, e)
except Exception as e:
logger.error(“fetch_facebook error: %s”, e)
return posts

def fetch_tiktok(limit=10):
logger.info(“TikTok scraper desactivado (requiere Playwright).”)
return []
