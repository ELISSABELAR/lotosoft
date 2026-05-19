"""
Parser A — page de répartition / statistiques pré-match.

FIX : accepte les tables prono-cyb-des avec 5 colonnes minimum
(time, match, c1, cn, c2) — LF7/LF8 peuvent ne pas avoir les colonnes U/O.

Structure des colonnes (ordre typique LF15) :
  0  : heure
  1  : match (class="match")
  2  : cote 1  (class="cote-d")  — format "74%1,14" ou "30%" ou "-1,84" ou "-"
  3  : cote N
  4  : cote 2
  5  : prono cyborg 1N2  (class="prono_match")   — optionnel
  6  : U%               (class="cote-d")          — optionnel
  7  : O%               (class="cote-d")          — optionnel
  8  : prono cyborg U/O (class="prono_match")     — optionnel
  9  : score            (class="dev_desktop_td_score") — optionnel

Règle skip : si cote_1 OU cote_n OU cote_2 est None pour AU MOINS UN match
→ toute la grille est ignorée (retourne None).
"""

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
    nb_entries:         int | None        = None
    total_combinations: int | None        = None
    matches:            list[MatchStats]  = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing cellule cote-d
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cote_cell(text):
    """
    "74%1,14"  → (cyborg_pct=74.0, cote=1.14)  cote présente ✓
    "30%"      → (30.0, None)                   cote manquante → skip grille
    "-1,84"    → (None, 1.84)                   cote présente ✓
    "-"        → (None, None)                   cote manquante → skip grille
    "23%"      → (23.0, None)                   colonnes U/O seulement (pas de skip)
    """
    text = text.strip()
    if text in ("-", ""):
        return None, None
    if "%" in text:
        pct_str, _, cote_str = text.partition("%")
        pct  = to_float(pct_str)
        cote = to_float(cote_str) if cote_str else None
        return pct, cote
    if text.startswith("-") and len(text) > 1:
        return None, to_float(text[1:])
    return None, to_float(text)


def _cell(cells, idx):
    """Retourne cells[idx] ou None si hors limites."""
    return cells[idx] if idx < len(cells) else None


def _parse_bettor_table(table):
    """Parse TABLE 0/1/2 → {match_num: bettor_pct}."""
    result = {}
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) < 3 or row.find("th"):
            continue
        try:
            num = int(clean(cells[0].get_text()))
        except ValueError:
            continue
        pct = to_float(clean(cells[2].get_text()))
        if num and pct is not None:
            result[num] = pct
    return result


def _parse_main_table(table):
    """
    Parse la table prono-cyb-des.
    FIX : accepte minimum 5 colonnes (time, match, c1, cn, c2).
    Les colonnes U/O et score sont optionnelles.
    """
    matches = []
    num = 1

    for row in table.find_all("tr"):
        if row.find("th"):
            continue
        cells = row.find_all("td")

        # Minimum : time + match + 3 cotes = 5 colonnes
        if len(cells) < 5:
            continue

        m = MatchStats(num=num)

        # Col 0 : heure
        m.time = clean(cells[0].get_text())

        # Col 1 : nom du match
        m.match_raw = clean(cells[1].get_text())

        # Col 2/3/4 : cotes 1, N, 2
        txt1 = clean(cells[2].get_text())
        txtn = clean(cells[3].get_text())
        txt2 = clean(cells[4].get_text())

        m.cyborg_pct_1, m.cote_1 = _parse_cote_cell(txt1)
        m.cyborg_pct_n, m.cote_n = _parse_cote_cell(txtn)
        m.cyborg_pct_2, m.cote_2 = _parse_cote_cell(txt2)

        # Favori (cote-bet) parmi 1/N/2
        if "cote-bet" in cells[2].get("class", []):
            m.cyborg_fav = "1"
        elif "cote-bet" in cells[3].get("class", []):
            m.cyborg_fav = "N"
        elif "cote-bet" in cells[4].get("class", []):
            m.cyborg_fav = "2"

        # Col 5 : prono cyborg 1N2 (optionnel)
        c5 = _cell(cells, 5)
        if c5:
            p = clean(c5.get_text())
            m.cyborg_prono = p if p and p != "-" else None

        # Col 6/7 : U/O (optionnel)
        c6 = _cell(cells, 6)
        c7 = _cell(cells, 7)
        if c6:
            m.cyborg_pct_u, _ = _parse_cote_cell(clean(c6.get_text()))
            if "cote-bet" in c6.get("class", []):
                m.cyborg_fav_uo = "U"
        if c7:
            m.cyborg_pct_o, _ = _parse_cote_cell(clean(c7.get_text()))
            if "cote-bet" in c7.get("class", []):
                m.cyborg_fav_uo = "O"

        # Col 8 : prono U/O (optionnel)
        c8 = _cell(cells, 8)
        if c8:
            pu = clean(c8.get_text())
            m.cyborg_prono_uo = pu if pu and pu != "-" else None

        # Col 9 : score (optionnel)
        c9 = _cell(cells, 9)
        if c9:
            sc = clean(c9.get_text())
            m.score = sc if re.match(r"^\d+[-–]\d+$", sc) else None

        matches.append(m)
        num += 1

    return matches


# ─────────────────────────────────────────────────────────────────────────────
# Parsing global
# ─────────────────────────────────────────────────────────────────────────────

def parse_stats_page(soup, record_id, grid_type, url):
    """
    Parse la page répartition.
    Retourne None si :
    - table prono-cyb-des absente
    - aucun match trouvé
    - au moins un match a une cote manquante
    """
    mult  = GRID_TYPES[grid_type]["multiplier"]
    page  = StatsPage(record_id=record_id, grid_type=grid_type, url=url)
    bloc  = soup.find(id="bloccontenu") or soup

    # nb_entries depuis le h2 "Répartition 1N2 des joueurs (X pronostics)"
    for h2 in bloc.find_all("h2"):
        txt = clean(h2.get_text())
        m   = re.search(r"\((\d[\d\s]*)\s*pronostic", txt, re.I)
        if m:
            page.nb_entries         = int(m.group(1).replace(" ", "").replace("\xa0", ""))
            page.total_combinations = page.nb_entries * mult
            break

    # Localise la table principale
    all_tables  = bloc.find_all("table")
    main_table  = bloc.find("table", class_="prono-cyb-des")

    if not main_table:
        logger.info(f"  {record_id}: table prono-cyb-des absente → skip")
        return None

    # Tables bettor (avant prono-cyb-des)
    pre_tables = [t for t in all_tables if t is not main_table]
    b1 = _parse_bettor_table(pre_tables[0]) if len(pre_tables) >= 1 else {}
    bn = _parse_bettor_table(pre_tables[1]) if len(pre_tables) >= 2 else {}
    b2 = _parse_bettor_table(pre_tables[2]) if len(pre_tables) >= 3 else {}

    # Parse table principale
    matches = _parse_main_table(main_table)

    if not matches:
        logger.info(f"  {record_id}: 0 match parsé dans prono-cyb-des → skip")
        return None

    # Vérification cotes manquantes
    for m in matches:
        if m.cote_1 is None or m.cote_n is None or m.cote_2 is None:
            logger.info(
                f"  {record_id}: cote manquante match {m.num} "
                f"(c1={m.cote_1} cn={m.cote_n} c2={m.cote_2}) → skip"
            )
            return None

    # Fusion bettor %
    for m in matches:
        m.bettor_pct_1 = b1.get(m.num)
        m.bettor_pct_n = bn.get(m.num)
        m.bettor_pct_2 = b2.get(m.num)

    page.matches = matches
    logger.info(
        f"  {record_id}: {len(matches)} matchs OK | "
        f"nb_entries={page.nb_entries} | total_lines={page.total_combinations}"
    )
    return page


def fetch_stats(session, url, record_id, grid_type):
    soup, status = fetch(session, url, delay=DELAY_STATS)
    if soup is None:
        logger.info(f"  {record_id}: répartition HTTP {status} ({url}) → skip")
        return None
    return parse_stats_page(soup, record_id, grid_type, url)
