import re, time, logging
import requests
from bs4 import BeautifulSoup
from .config import HEADERS

logger = logging.getLogger(__name__)

def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def fetch(session, url, delay=1.5):
    try:
        time.sleep(delay)
        r = session.get(url, timeout=20)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "iso-8859-15"
        return BeautifulSoup(r.text, "lxml")
    except requests.RequestException as e:
        logger.warning(f"Network error {url}: {e}")
        return None

def to_float(text):
    if not text:
        return None
    t = re.sub(r"[€¤\s\xa0]", "", text).replace(",", ".").strip()
    if t in ("-", "", "N/A"):
        return None
    try:
        return float(t)
    except ValueError:
        return None

def clean(text):
    return " ".join(text.split()).strip()
