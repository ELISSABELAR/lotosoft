import logging, re
from dataclasses import dataclass
from bs4 import BeautifulSoup
from .config import BASE_URL, GRID_TYPES, GRID_URL_MAP, URL_LISTING, URL_LISTING_WITH_NB, DELAY_LISTING
from .utils import fetch, to_float, clean

logger = logging.getLogger(__name__)

@dataclass
class RecordRef:
    grid_type:   str
    record_id:   str
    season:      str
    date_str:    str
    competition: str
    pactole:     float | None
    enjeux:      float | None
    rang1:       float | None
    rang2:       float | None
    url_results: str
    url_stats:   str

def _parse_ids(href):
    m = re.search(r"/(\d{4}-\d{4})/([\w-]+)/?$", href)
    if m: return m.group(2), m.group(1)
    m = re.search(r"/(\d{4}-grille-\d+)/?$", href)
    if m: return m.group(1), "unknown"
    return "", ""

def detect_total_pages(soup):
    pg = soup.select_one("#dev_pagination")
    if not pg: return 1
    last = pg.select_one("a.last")
    if last:
        m = re.search(r"page-(\d+)", last.get("href", ""))
        if m: return int(m.group(1))
    nums = [int(m.group(1)) for a in pg.find_all("a")
            if (m := re.search(r"page-(\d+)", a.get("href", "")))]
    return max(nums) if nums else 1

def parse_listing_page(soup, grid_type):
    cfg     = GRID_TYPES[grid_type]
    results = []
    tbody = soup.select_one("table.stat_hist tbody")
    if not tbody: return results
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 7: continue
        link = cells[1].find("a")
        if not link: continue
        hist_href = link.get("href", "")
        record_id, season = _parse_ids(hist_href)
        if not record_id: continue
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
            url_results = BASE_URL + hist_href,
            url_stats   = f"{BASE_URL}/fr/lotofoot/repartition/{cfg['path']}/{record_id}/",
        ))
    return results

def _build_listing_url(grid_type, page):
    """Construit l'URL de listing en tenant compte du sous-type nb_matchs."""
    cfg     = GRID_TYPES[grid_type]
    url_key = GRID_URL_MAP[grid_type]
    nb      = cfg.get("nb")
    if nb:
        return URL_LISTING_WITH_NB.format(base=BASE_URL, grid=url_key, nb=nb, page=page)
    return URL_LISTING.format(base=BASE_URL, grid=url_key, page=page)

def fetch_listing_page(session, grid_type, page):
    url = _build_listing_url(grid_type, page)
    logger.info(f"[{grid_type}] listing page {page}")
    soup = fetch(session, url, delay=DELAY_LISTING)
    if soup is None: return None, []
    return soup, parse_listing_page(soup, grid_type)
