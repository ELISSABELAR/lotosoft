"""Utilitaires partagés."""
import re, time, logging
import requests
from bs4 import BeautifulSoup
from .config import HEADERS

logger = logging.getLogger(__name__)

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

def fetch(session: requests.Session, url: str, delay: float = 1.5) -> BeautifulSoup | None:
    try:
        time.sleep(delay)
        r = session.get(url, timeout=20)
        if r.status_code == 404:
            logger.debug(f"404: {url}")
            return None
        r.raise_for_status()
        r.encoding = r.apparent_encoding or "iso-8859-15"
        return BeautifulSoup(r.text, "lxml")
    except requests.RequestException as e:
        logger.warning(f"Erreur réseau {url}: {e}")
        return None

def to_float(text: str) -> float | None:
    if not text:
        return None
    # Supprime €, ¤ (variante ISO de €), espaces, nbsp, puis virgule → point
    t = re.sub(r"[€¤\s\xa0]", "", text).replace(",", ".").strip()
    if t in ("-", "", "N/A"):
        return None
    try:
        return float(t)
    except ValueError:
        return None

def clean(text: str) -> str:
    return " ".join(text.split()).strip()
