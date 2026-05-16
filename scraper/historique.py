"""
Parser de la page Historique / Résultats et rapports officiels.

URL : /fr/lotosports/historiques/{grid}/{season}/{grille_id}/

Structure :
  TABLE class="hist"  :  liste des matchs avec résultats
    Colonnes : match_num | home (class="home") | result (class="result") | away (class="ext")
    Le résultat gagnant est dans <span class="res">X</span>

  TABLE suivante (sans classe spéciale) : rapports par rang
    Colonnes : rang | nb_gagnants | rapport_eur
    Ex : 15 | 1 | 1 000 000 €

  Autres tables (stats) : nb_1/N/2, consécutifs, diagonales, paires...
    → stockées telles quelles dans page.stats
"""

import logging
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag
from .config import DELAY_HISTORIQUE
from .utils import clean, to_float

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HistMatch:
    num:    int
    home:   str
    away:   str
    result: str | None = None   # "1", "N", "2"


@dataclass
class Rang:
    rang:          int
    nb_gagnants:   int
    rapport_eur:   float | None


@dataclass
class HistoriquePage:
    grille_id: str
    url:       str
    date_str:  str                  = ""     # "Dimanche 10 mai à 14h55"
    matches:   list[HistMatch]      = field(default_factory=list)
    rangs:     list[Rang]           = field(default_factory=list)
    stats:     dict                 = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing table "hist"
# ─────────────────────────────────────────────────────────────────────────────

def _parse_hist_table(table: Tag) -> tuple[str, list[HistMatch]]:
    """
    Retourne (date_str, liste de HistMatch).
    La première ligne contient souvent une date (colspan).
    Le résultat gagnant est le <span class="res"> dans la cellule result.
    """
    date_str = ""
    matches: list[HistMatch] = []

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])

        # Ligne de date (colspan) — ex: "Dimanche 10 mai à 14h55"
        if len(cells) == 1:
            txt = clean(cells[0].get_text())
            if txt and not txt.isdigit():
                date_str = txt
            continue

        if len(cells) < 4:
            continue

        # Numéro match
        try:
            num = int(clean(cells[0].get_text()))
        except ValueError:
            continue

        # Équipes (classes "home" et "ext")
        home_cell = row.select_one("td.home") or cells[1]
        away_cell = row.select_one("td.ext")  or cells[3]
        home = clean(home_cell.get_text())
        away = clean(away_cell.get_text())

        # Résultat : <span class="res"> contient le signe gagnant ("1","N","2")
        result_cell = row.select_one("td.result")
        result = None
        if result_cell:
            res_span = result_cell.find("span", class_="res")
            if res_span:
                txt = clean(res_span.get_text())
                if txt in ("1", "N", "2"):
                    result = txt

        matches.append(HistMatch(num=num, home=home, away=away, result=result))

    return date_str, matches


# ─────────────────────────────────────────────────────────────────────────────
# Parsing table des rapports par rang
# ─────────────────────────────────────────────────────────────────────────────

def _parse_rangs_table(table: Tag, grid_size: int) -> list[Rang]:
    """
    Table avec : rang | nb_gagnants | rapport_eur
    Les rangs vont de grid_size à grid_size-3 (ex: 15,14,13,12 pour LF15).
    """
    rangs: list[Rang] = []
    for row in table.find_all("tr"):
        if row.find("th"):
            continue
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        try:
            rang = int(clean(cells[0].get_text()))
            nb   = int(clean(cells[1].get_text()).replace(" ", "").replace("\xa0", ""))
            rpt  = to_float(cells[2].get_text())
        except (ValueError, IndexError):
            continue
        rangs.append(Rang(rang=rang, nb_gagnants=nb, rapport_eur=rpt))
    return rangs


# ─────────────────────────────────────────────────────────────────────────────
# Parsing tables de stats globales (1N2, consécutifs, diagonales, paires)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_stats_tables(tables: list[Tag]) -> dict:
    """
    Extrait les statistiques des tables après le tableau des rangs.
    On lit les valeurs en texte brut par ordre.

    Table 0 (après rangs) : nb_1 | nb_n | nb_2
    Table 1               : cons_1 | cons_n | cons_2
    Table 2               : diagonales | symetries | alternances
    Table 3               : paires | tierces | quartes
    """
    stats: dict = {}
    keys_by_table = [
        ("nb_1", "nb_n", "nb_2"),
        ("cons_1", "cons_n", "cons_2"),
        ("diagonales", "symetries", "alternances"),
        ("paires", "tierces", "quartes"),
    ]
    for ti, table in enumerate(tables[:4]):
        if ti >= len(keys_by_table):
            break
        keys = keys_by_table[ti]
        vals = []
        for row in table.find_all("tr"):
            for cell in row.find_all("td"):
                v = to_float(clean(cell.get_text()))
                if v is not None:
                    vals.append(v)
        for ki, key in enumerate(keys):
            stats[key] = int(vals[ki]) if ki < len(vals) else None
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Parsing global
# ─────────────────────────────────────────────────────────────────────────────

def parse_historique_page(
    soup: BeautifulSoup,
    grille_id: str,
    url: str,
    grid_size: int,
) -> HistoriquePage | None:
    """Parse la page historique/rapports officiels. Retourne None si page vide."""
    page = HistoriquePage(grille_id=grille_id, url=url)
    bloc = soup.find(id="bloccontenu") or soup
    tables = bloc.find_all("table")

    if not tables:
        logger.warning(f"{grille_id}: aucune table dans la page historique")
        return None

    # Table hist = première table avec class "hist"
    hist_table = bloc.find("table", class_="hist")
    if not hist_table:
        logger.warning(f"{grille_id}: table 'hist' introuvable")
        return None

    page.date_str, page.matches = _parse_hist_table(hist_table)
    if not page.matches:
        return None

    # Table rangs = table juste après "hist" (sans classe particulière)
    hist_idx = tables.index(hist_table)
    remaining = tables[hist_idx + 1:]

    if remaining:
        page.rangs = _parse_rangs_table(remaining[0], grid_size)

    if len(remaining) > 1:
        page.stats = _parse_stats_tables(remaining[1:])

    logger.debug(
        f"{grille_id}: {len(page.matches)} matchs hist, "
        f"{len(page.rangs)} rangs, "
        f"date='{page.date_str}'"
    )
    return page


def fetch_historique(
    session,
    url: str,
    grille_id: str,
    grid_size: int,
) -> HistoriquePage | None:
    from .utils import fetch as _fetch
    soup = _fetch(session, url, delay=DELAY_HISTORIQUE)
    if soup is None:
        return None
    return parse_historique_page(soup, grille_id, url, grid_size)
