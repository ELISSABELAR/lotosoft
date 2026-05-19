"""
Listing page parser.

FIX CLÉ : l'URL de répartition est extraite directement depuis la colonne 2
du tableau HTML (le bouton icône), au lieu d'être construite depuis la config.
Cela évite les erreurs 404 si pronosoft utilise un path différent de celui attendu.

Structure du tableau stat_hist :
  col 0 : numéro d'ordre (1, 2, 3...)
  col 1 : lien historique  → /fr/lotosports/historiques/{grid}/{season}/{grille_id}/
  col 2 : lien répartition → /fr/lotofoot/repartition/{path}/{grille_id}/   ← EXTRAIT ICI
  col 3 : date
  col 4 : type/compétition
  col 5 : pactole
  col 6 : enjeux
  col 7 : rapport rang 2
  col 8 : rapport rang 1
"""

import logging, re
from dataclasses import dataclass
from bs4 import BeautifulSoup
from .config import BASE_URL, GRID_TYPES, GRID_SLUG, URL_LISTING, DELAY_LISTING
from .utils import fetch, to_float, clean

logger = logging.getLogger(__name__)


@dataclass
class RecordRef:
    grid_type:   str
    record_id:   str    # ex: "2026-grille-44"
    season:      str    # ex: "2025-2026"
    date_str:    str
    competition: str
    pactole:     float | None
    enjeux:      float | None
    rang1:       float | None
    rang2:       float | None
    url_results: str    # URL page historique/résultats
    url_stats:   str    # URL page répartition/stats (extraite du HTML)


def _parse_ids(href):
    """Extrait (record_id, season) depuis l'URL historique."""
    m = re.search(r"/(\d{4}-\d{4})/([\w-]+)/?$", href)
    if m:
        return m.group(2), m.group(1)
    # Fallback pour URLs sans saison explicite
    m = re.search(r"/(\d{4}-grille-\d+)/?$", href)
    if m:
        return m.group(1), "unknown"
    return "", ""


def detect_total_pages(soup):
    pg = soup.select_one("#dev_pagination")
    if not pg:
        return 1
    last = pg.select_one("a.last")
    if last:
        m = re.search(r"page-(\d+)", last.get("href", ""))
        if m:
            return int(m.group(1))
    nums = [int(m.group(1)) for a in pg.find_all("a")
            if (m := re.search(r"page-(\d+)", a.get("href", "")))]
    return max(nums) if nums else 1


def parse_listing_page(soup, grid_type):
    cfg = GRID_TYPES[grid_type]
    results = []

    tbody = soup.select_one("table.stat_hist tbody")
    if not tbody:
        logger.warning(f"[{grid_type}] table stat_hist introuvable")
        return results

    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        # ── col 1 : lien historique → record_id + season ─────────────────────
        hist_link = cells[1].find("a")
        if not hist_link:
            continue
        hist_href = hist_link.get("href", "")
        record_id, season = _parse_ids(hist_href)
        if not record_id:
            continue

        # ── col 2 : lien répartition extrait DIRECTEMENT du HTML ─────────────
        # C'est le bouton icône dans la colonne "link"
        rep_link = cells[2].find("a")
        if rep_link and rep_link.get("href"):
            rep_href = rep_link.get("href", "")
            url_stats = BASE_URL + rep_href if rep_href.startswith("/") else rep_href
        else:
            # Fallback : construction depuis la config (moins fiable)
            url_stats = f"{BASE_URL}/fr/lotofoot/repartition/{cfg['path']}/{record_id}/"
            logger.debug(f"  {record_id}: URL répartition construite (fallback)")

        url_results = BASE_URL + hist_href if hist_href.startswith("/") else hist_href

        results.append(RecordRef(
            grid_type   = grid_type,
            record_id   = record_id,
            season      = season,
            date_str    = clean(cells[3].get_text()),
            competition = clean(cells[4].get_text()),
            pactole     = to_float(cells[5].get_text()),
            enjeux      = to_float(cells[6].get_text()),
            rang2       = to_float(cells[7].get_text()) if len(cells) > 7 else None,
            rang1       = to_float(cells[8].get_text()) if len(cells) > 8 else None,
            url_results = url_results,
            url_stats   = url_stats,
        ))

    return results


def fetch_listing_page(session, grid_type, page):
    slug = GRID_SLUG[grid_type]
    url  = URL_LISTING.format(base=BASE_URL, slug=slug, page=page)
    logger.info(f"[{grid_type}] listing page {page} ({url})")
    soup, status = fetch(session, url, delay=DELAY_LISTING)
    if soup is None:
        logger.warning(f"[{grid_type}] listing page {page}: HTTP {status}")
        return None, []
    return soup, parse_listing_page(soup, grid_type)
