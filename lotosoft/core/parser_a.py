"""Parser A — pre-match statistics page."""
import re, logging
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag
from .config import GRID_TYPES, DELAY_STATS
from .utils import fetch, clean, to_float

logger = logging.getLogger(__name__)

@dataclass
class MatchStats:
    num:             int
    time:            str          = ""
    match_raw:       str          = ""
    cyborg_pct_1:    float | None = None
    cyborg_pct_n:    float | None = None
    cyborg_pct_2:    float | None = None
    cyborg_pct_u:    float | None = None
    cyborg_pct_o:    float | None = None
    cyborg_prono:    str   | None = None
    cyborg_prono_uo: str   | None = None
    cyborg_fav:      str   | None = None
    cyborg_fav_uo:   str   | None = None
    cote_1:          float | None = None
    cote_n:          float | None = None
    cote_2:          float | None = None
    bettor_pct_1:    float | None = None
    bettor_pct_n:    float | None = None
    bettor_pct_2:    float | None = None
    score:           str   | None = None

@dataclass
class StatsPage:
    record_id:          str
    grid_type:          str
    url:                str
    nb_entries:         int | None       = None
    total_combinations: int | None       = None
    matches:            list[MatchStats] = field(default_factory=list)

def _parse_cell(text):
    text = text.strip()
    if text == "-": return None, None
    if "%" in text:
        pct_str, _, cote_str = text.partition("%")
        return to_float(pct_str), (to_float(cote_str) if cote_str else None)
    if text.startswith("-") and len(text) > 1:
        return None, to_float(text[1:])
    return None, to_float(text)

def _parse_bettor_table(table):
    result = {}
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 3 or row.find("th"): continue
        try: num = int(clean(cells[0].get_text()))
        except ValueError: continue
        pct = to_float(clean(cells[2].get_text()))
        if num and pct is not None: result[num] = pct
    return result

def _parse_main_table(table):
    matches = []
    num = 1
    for row in table.find_all("tr"):
        if row.find("th"): continue
        cells = row.find_all("td")
        if len(cells) < 9: continue
        m = MatchStats(num=num)
        m.time      = clean(cells[0].get_text())
        m.match_raw = clean(cells[1].get_text())
        txt1 = clean(cells[2].get_text())
        txtn = clean(cells[3].get_text())
        txt2 = clean(cells[4].get_text())
        m.cyborg_pct_1, m.cote_1 = _parse_cell(txt1)
        m.cyborg_pct_n, m.cote_n = _parse_cell(txtn)
        m.cyborg_pct_2, m.cote_2 = _parse_cell(txt2)
        if "cote-bet" in cells[2].get("class", []): m.cyborg_fav = "1"
        if "cote-bet" in cells[3].get("class", []): m.cyborg_fav = "N"
        if "cote-bet" in cells[4].get("class", []): m.cyborg_fav = "2"
        p = clean(cells[5].get_text())
        m.cyborg_prono = p if p and p != "-" else None
        m.cyborg_pct_u, _ = _parse_cell(clean(cells[6].get_text()))
        m.cyborg_pct_o, _ = _parse_cell(clean(cells[7].get_text()))
        if "cote-bet" in cells[6].get("class", []): m.cyborg_fav_uo = "U"
        if "cote-bet" in cells[7].get("class", []): m.cyborg_fav_uo = "O"
        pu = clean(cells[8].get_text())
        m.cyborg_prono_uo = pu if pu and pu != "-" else None
        sc = clean(cells[9].get_text()) if len(cells) > 9 else ""
        m.score = sc if re.match(r"^\d+[-–]\d+$", sc) else None
        matches.append(m)
        num += 1
    return matches

def parse_stats_page(soup, record_id, grid_type, url):
    mult = GRID_TYPES[grid_type]["multiplier"]
    page = StatsPage(record_id=record_id, grid_type=grid_type, url=url)
    bloc = soup.find(id="bloccontenu") or soup
    for h2 in bloc.find_all("h2"):
        txt = clean(h2.get_text())
        m = re.search(r"\((\d[\d\s]*)\s*pronostic", txt, re.I)
        if m:
            page.nb_entries = int(m.group(1).replace(" ", ""))
            page.total_combinations = page.nb_entries * mult
            break
    all_tables = bloc.find_all("table")
    main_table = bloc.find("table", class_="prono-cyb-des")
    if not main_table:
        return None
    pre = [t for t in all_tables if t is not main_table]
    b1 = _parse_bettor_table(pre[0]) if len(pre) >= 1 else {}
    bn = _parse_bettor_table(pre[1]) if len(pre) >= 2 else {}
    b2 = _parse_bettor_table(pre[2]) if len(pre) >= 3 else {}
    matches = _parse_main_table(main_table)
    if not matches: return None
    for m in matches:
        if m.cote_1 is None or m.cote_n is None or m.cote_2 is None:
            logger.info(f"{record_id}: missing cote match {m.num} → skip")
            return None
    for m in matches:
        m.bettor_pct_1 = b1.get(m.num)
        m.bettor_pct_n = bn.get(m.num)
        m.bettor_pct_2 = b2.get(m.num)
    page.matches = matches
    return page

def fetch_stats(session, url, record_id, grid_type):
    soup = fetch(session, url, delay=DELAY_STATS)
    if soup is None: return None
    return parse_stats_page(soup, record_id, grid_type, url)
