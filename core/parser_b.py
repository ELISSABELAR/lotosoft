"""Parser B — page historique / résultats officiels."""
import logging, re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from .config import DELAY_RESULTS
from .utils import clean, to_float

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    num:    int
    home:   str
    away:   str
    result: str | None = None   # "1", "N", "2"


@dataclass
class RankRow:
    rank:       int
    nb_winners: int
    payout_eur: float | None


@dataclass
class ResultsPage:
    record_id: str
    url:       str
    date_str:  str               = ""
    matches:   list[MatchResult] = field(default_factory=list)
    ranks:     list[RankRow]     = field(default_factory=list)
    stats:     dict              = field(default_factory=dict)


def _parse_results_table(table):
    date_str = ""
    matches  = []
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) == 1:
            txt = clean(cells[0].get_text())
            if txt and not txt.isdigit():
                date_str = txt
            continue
        if len(cells) < 4:
            continue
        try:
            num = int(clean(cells[0].get_text()))
        except ValueError:
            continue
        home = clean((row.select_one("td.home") or cells[1]).get_text())
        away = clean((row.select_one("td.ext")  or cells[3]).get_text())
        result = None
        rc = row.select_one("td.result")
        if rc:
            rs = rc.find("span", class_="res")
            if rs:
                t = clean(rs.get_text())
                if t in ("1", "N", "2"):
                    result = t
        matches.append(MatchResult(num=num, home=home, away=away, result=result))
    return date_str, matches


def _parse_ranks_table(table):
    ranks = []
    for row in table.find_all("tr"):
        if row.find("th"):
            continue
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        try:
            rank = int(clean(cells[0].get_text()))
            nb   = int(re.sub(r"\D", "", cells[1].get_text()) or "0")
            pyt  = to_float(cells[2].get_text())
        except (ValueError, IndexError):
            continue
        ranks.append(RankRow(rank=rank, nb_winners=nb, payout_eur=pyt))
    return ranks


def _parse_stats(tables):
    stats = {}
    keys  = [
        ("nb_1", "nb_n", "nb_2"),
        ("cons_1", "cons_n", "cons_2"),
        ("diagonales", "symetries", "alternances"),
        ("paires", "tierces", "quartes"),
    ]
    for ti, table in enumerate(tables[:4]):
        if ti >= len(keys):
            break
        vals = []
        for row in table.find_all("tr"):
            for cell in row.find_all("td"):
                v = to_float(clean(cell.get_text()))
                if v is not None:
                    vals.append(v)
        for ki, key in enumerate(keys[ti]):
            stats[key] = int(vals[ki]) if ki < len(vals) else None
    return stats


def parse_results_page(soup, record_id, url, grid_size):
    page   = ResultsPage(record_id=record_id, url=url)
    bloc   = soup.find(id="bloccontenu") or soup
    tables = bloc.find_all("table")
    hist   = bloc.find("table", class_="hist")
    if not hist:
        logger.debug(f"  {record_id}: table hist absente")
        return None
    page.date_str, page.matches = _parse_results_table(hist)
    if not page.matches:
        return None
    idx       = tables.index(hist)
    remaining = tables[idx + 1:]
    if remaining:
        page.ranks = _parse_ranks_table(remaining[0])
    if len(remaining) > 1:
        page.stats = _parse_stats(remaining[1:])
    return page


def fetch_results(session, url, record_id, grid_size):
    from .utils import fetch as _fetch
    soup, status = _fetch(session, url, delay=DELAY_RESULTS)
    if soup is None:
        logger.debug(f"  {record_id}: historique HTTP {status}")
        return None
    return parse_results_page(soup, record_id, url, grid_size)
