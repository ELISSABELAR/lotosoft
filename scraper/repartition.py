"""
Parser de la page Répartition LotoFoot.

URL : /fr/lotofoot/repartition/{lf7|lf8|lf12|lf15}/{grille_id}/

Structure de la page (7 tables dans bloccontenu) :
  TABLE 0 : bettor % signe 1  (trié desc) — match_num | match_name | bettor_pct_1
  TABLE 1 : bettor % signe N  (trié desc) — match_num | match_name | bettor_pct_n
  TABLE 2 : bettor % signe 2  (trié desc) — match_num | match_name | bettor_pct_2
  TABLE 3 : autre tri (non utilisé pour l'instant)
  TABLE 4 : analyse post-match (match:sign | stat_ok/ko | pct_dominant)
  TABLE 5 : bettor % des signes minoritaires + cotes FDJ (triés par cote asc)
  TABLE 6 : prono-cyb-des — données CYBORG (probabilités algo + cotes FDJ + scores)

h2 "Répartition 1N2 des joueurs (X pronostics)" → nb_pronostics du concours Pronosoft

Cellule cote-d dans TABLE 6 :
  "74%1,14"  → cyborg_pct=74.0, cote=1.14
  "30%"      → cyborg_pct=30.0, cote=None   ← COTE MANQUANTE → skip grille
  "-1,84"    → cyborg_pct=None, cote=1.84   ← pas de pct cyborg, cote OK
  "-"        → cyborg_pct=None, cote=None   ← COTE MANQUANTE → skip grille

Les U/O (cells 6-7) sont toujours en format "PCT%" seulement → jamais de cote.

SKIP : si TOUTES les cotes (cote_1, cote_n, cote_2) ne sont pas des nombres
       pour AU MOINS UN match → grille invalide, retourne None.
"""

import re
import logging
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag
from .config import GRID_TYPES, DELAY_REPARTITION
from .utils import fetch, clean, to_float

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchRepart:
    num:            int
    time:           str          = ""
    match_raw:      str          = ""    # texte brut "Home-Away" (sans séparateur clair)
    # Cyborg (algo pronosoft)
    cyborg_pct_1:   float | None = None
    cyborg_pct_n:   float | None = None
    cyborg_pct_2:   float | None = None
    cyborg_pct_u:   float | None = None
    cyborg_pct_o:   float | None = None
    cyborg_prono:   str   | None = None  # "1","N","2","1N","N2","-"
    cyborg_prono_uo: str  | None = None  # "U","O","-"
    cyborg_fav:     str   | None = None  # signe avec classe "cote-bet" dans 1N2
    cyborg_fav_uo:  str   | None = None  # signe avec classe "cote-bet" dans U/O
    # Cotes FDJ (dans la cellule cyborg mais c'est bien la cote officielle FDJ)
    cote_1:         float | None = None
    cote_n:         float | None = None
    cote_2:         float | None = None
    # Bettor % (concours Pronosoft — tables 0/1/2)
    bettor_pct_1:   float | None = None
    bettor_pct_n:   float | None = None
    bettor_pct_2:   float | None = None
    # Score (disponible après le match)
    score:          str   | None = None


@dataclass
class RepartitionPage:
    grille_id:      str
    grid_type:      str
    url:            str
    nb_pronostics:  int | None       = None
    total_grille_lines: int | None   = None
    matches:        list[MatchRepart] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing cellule cote-d
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cote_cell(text: str) -> tuple[float | None, float | None]:
    """
    Retourne (cyborg_pct, cote_fdj).

    "74%1,14"  → (74.0, 1.14)
    "30%"      → (30.0, None)   ← cote manquante
    "-1,84"    → (None, 1.84)
    "-"        → (None, None)   ← cote manquante
    "23%"      → (23.0, None)   ← cellules U/O, pas de cote
    """
    text = text.strip()
    if text == "-":
        return None, None
    if "%" in text:
        pct_str, _, cote_str = text.partition("%")
        pct  = to_float(pct_str) if pct_str else None
        cote = to_float(cote_str) if cote_str else None
        return pct, cote
    if text.startswith("-") and len(text) > 1:
        return None, to_float(text[1:])
    return None, to_float(text)


def _cell_has_missing_cote(text: str) -> bool:
    """True si la cellule est une cote 1/N/2 sans valeur numérique."""
    _, cote = _parse_cote_cell(text)
    return cote is None


# ─────────────────────────────────────────────────────────────────────────────
# Parsing TABLE 0/1/2 → bettor %
# ─────────────────────────────────────────────────────────────────────────────

def _parse_bettor_table(table: Tag) -> dict[int, float]:
    """
    Parse une des tables bettor (TABLE 0, 1 ou 2).
    Retourne un dict {match_num (int) → bettor_pct (float)}.
    """
    result: dict[int, float] = {}
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


# ─────────────────────────────────────────────────────────────────────────────
# Parsing TABLE 6 (prono-cyb-des) → données Cyborg + cotes FDJ + scores
# ─────────────────────────────────────────────────────────────────────────────

def _parse_cyborg_table(table: Tag) -> list[MatchRepart]:
    """
    Parse la table prono-cyb-des.
    Chaque ligne = 1 match, dans l'ordre de la grille (row index = match num).

    Colonnes :
      0  : heure
      1  : match (class="match")       — "Home-Away" (concat)
      2  : signe 1 (class="cote-d")    — "74%1,14"
      3  : signe N (class="cote-d")
      4  : signe 2 (class="cote-d")
      5  : prono 1N2 (class="prono_match")
      6  : U%  (class="cote-d")        — "23%"
      7  : O%  (class="cote-d")        — "77%"
      8  : prono U/O (class="prono_match")
      9  : score (class="dev_desktop_td_score")
    """
    matches: list[MatchRepart] = []
    num = 1

    for row in table.find_all("tr"):
        if row.find("th"):
            continue
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        m = MatchRepart(num=num)

        # Heure
        m.time = clean(cells[0].get_text())

        # Nom du match (brut)
        m.match_raw = clean(cells[1].get_text())

        # Signe 1 — détermine si "cote-bet" (favori parieurs)
        txt1 = clean(cells[2].get_text())
        m.cyborg_pct_1, m.cote_1 = _parse_cote_cell(txt1)
        if "cote-bet" in cells[2].get("class", []):
            m.cyborg_fav = "1"

        # Signe N
        txtn = clean(cells[3].get_text())
        m.cyborg_pct_n, m.cote_n = _parse_cote_cell(txtn)
        if "cote-bet" in cells[3].get("class", []):
            m.cyborg_fav = "N"

        # Signe 2
        txt2 = clean(cells[4].get_text())
        m.cyborg_pct_2, m.cote_2 = _parse_cote_cell(txt2)
        if "cote-bet" in cells[4].get("class", []):
            m.cyborg_fav = "2"

        # Prono Cyborg 1N2
        prono = clean(cells[5].get_text())
        m.cyborg_prono = prono if prono and prono != "-" else None

        # U% et O%
        txtu = clean(cells[6].get_text())
        txto = clean(cells[7].get_text())
        m.cyborg_pct_u, _ = _parse_cote_cell(txtu)
        m.cyborg_pct_o, _ = _parse_cote_cell(txto)
        if "cote-bet" in cells[6].get("class", []):
            m.cyborg_fav_uo = "U"
        if "cote-bet" in cells[7].get("class", []):
            m.cyborg_fav_uo = "O"

        # Prono U/O
        prono_uo = clean(cells[8].get_text())
        m.cyborg_prono_uo = prono_uo if prono_uo and prono_uo != "-" else None

        # Score
        score = clean(cells[9].get_text()) if len(cells) > 9 else ""
        m.score = score if re.match(r"^\d+[-–]\d+$", score) else None

        matches.append(m)
        num += 1

    return matches


# ─────────────────────────────────────────────────────────────────────────────
# Parsing global de la page
# ─────────────────────────────────────────────────────────────────────────────

def parse_repartition_page(
    soup: BeautifulSoup,
    grille_id: str,
    grid_type: str,
    url: str,
) -> RepartitionPage | None:
    """
    Parse la page répartition complète.
    Retourne None si au moins un match a une cote manquante (skip grille).
    """
    multiplier = GRID_TYPES[grid_type]["multiplier"]
    page = RepartitionPage(grille_id=grille_id, grid_type=grid_type, url=url)
    bloc = soup.find(id="bloccontenu") or soup

    # ── nb_pronostics depuis le h2 ───────────────────────────────────────────
    # "Répartition 1N2 des joueurs (539 pronostics)"
    for h2 in bloc.find_all("h2"):
        txt = clean(h2.get_text())
        m = re.search(r"\((\d[\d\s]*)\s*pronostic", txt, re.I)
        if m:
            page.nb_pronostics = int(m.group(1).replace(" ", ""))
            page.total_grille_lines = page.nb_pronostics * multiplier
            break

    # ── Localise les 7 tables ────────────────────────────────────────────────
    all_tables = bloc.find_all("table")
    cyborg_table = bloc.find("table", class_="prono-cyb-des")
    if not cyborg_table:
        logger.warning(f"{grille_id}: table prono-cyb-des introuvable")
        return None

    # Les 6 tables avant prono-cyb-des = stats bettor
    pre_tables = [t for t in all_tables if t is not cyborg_table]

    # TABLE 0 = bettor signe 1, TABLE 1 = signe N, TABLE 2 = signe 2
    bettor_1: dict[int, float] = {}
    bettor_n: dict[int, float] = {}
    bettor_2: dict[int, float] = {}

    if len(pre_tables) >= 1:
        bettor_1 = _parse_bettor_table(pre_tables[0])
    if len(pre_tables) >= 2:
        bettor_n = _parse_bettor_table(pre_tables[1])
    if len(pre_tables) >= 3:
        bettor_2 = _parse_bettor_table(pre_tables[2])

    # ── Parse Cyborg table ───────────────────────────────────────────────────
    matches = _parse_cyborg_table(cyborg_table)
    if not matches:
        logger.warning(f"{grille_id}: aucun match parsé dans prono-cyb-des")
        return None

    # ── Vérifie les cotes manquantes (skip rule) ─────────────────────────────
    for m in matches:
        if m.cote_1 is None or m.cote_n is None or m.cote_2 is None:
            logger.info(
                f"{grille_id}: cote manquante match {m.num} "
                f"({m.match_raw}) → grille ignorée"
            )
            return None

    # ── Fusionne bettor % ────────────────────────────────────────────────────
    for m in matches:
        m.bettor_pct_1 = bettor_1.get(m.num)
        m.bettor_pct_n = bettor_n.get(m.num)
        m.bettor_pct_2 = bettor_2.get(m.num)

    page.matches = matches
    logger.info(
        f"{grille_id}: {len(matches)} matchs OK, "
        f"nb_pronostics={page.nb_pronostics}, "
        f"total_lignes={page.total_grille_lines}"
    )
    return page


def fetch_repartition(
    session,
    url: str,
    grille_id: str,
    grid_type: str,
) -> RepartitionPage | None:
    from .utils import fetch as _fetch
    soup = _fetch(session, url, delay=DELAY_REPARTITION)
    if soup is None:
        return None
    return parse_repartition_page(soup, grille_id, grid_type, url)
