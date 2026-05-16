"""
Persistance : un fichier JSON par grille.

Arborescence :
  data/{grid_type}/{season}/{grille_id}.json

Format final (toutes sources fusionnées) :
{
  "grille_id":         "2026-grille-36",
  "grid_type":         "loto-foot-15",
  "season":            "2025-2026",
  "num":               36,
  "date":              "10/05",
  "date_full":         "Samedi 10 mai à 14h55",
  "competition":       "Ligue 1",
  "pactole_eur":       100000,
  "enjeux_eur":        225883,
  "nb_pronostics":     539,
  "total_grille_lines": 116424,
  "matches": [
    {
      "num":            1,
      "time":           "21h00",
      "home":           "Paris SG",        ← source : historique (noms propres séparés)
      "away":           "Brest",
      "result":         "1",               ← source : historique
      "score":          "1-0",             ← source : répartition
      "cote_1":         1.14,              ← source : répartition (cotes FDJ)
      "cote_n":         8.50,
      "cote_2":         15.0,
      "cyborg_pct_1":   74.0,             ← algo Pronosoft (≠ bettor %)
      "cyborg_pct_n":   18.0,
      "cyborg_pct_2":   8.0,
      "cyborg_pct_u":   23.0,
      "cyborg_pct_o":   77.0,
      "cyborg_prono":   "1",              ← prono algo Pronosoft 1N2
      "cyborg_prono_uo": "O",
      "cyborg_fav":     "1",              ← signe "cote-bet" dans tableau cyborg
      "cyborg_fav_uo":  "O",
      "bettor_pct_1":   86.9,             ← % joueurs concours Pronosoft
      "bettor_pct_n":   9.5,
      "bettor_pct_2":   3.6
    }
  ],
  "rangs": [
    {"rang": 15, "nb_gagnants": 1,    "rapport_eur": 1000000.0},
    {"rang": 14, "nb_gagnants": 16,   "rapport_eur": 13824.0},
    {"rang": 13, "nb_gagnants": 219,  "rapport_eur": 1010.0},
    {"rang": 12, "nb_gagnants": 1735, "rapport_eur": 127.4}
  ],
  "stats": {
    "nb_1": 5, "nb_n": 3, "nb_2": 7,
    "cons_1": 2, "cons_n": 2, "cons_2": 4,
    "diagonales": 0, "symetries": 2, "alternances": 8,
    "paires": 9, "tierces": 11, "quartes": 12
  }
}
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from .config import DATA_DIR
from .rapports import GrilleRef
from .repartition import RepartitionPage, MatchRepart
from .historique import HistoriquePage, HistMatch

logger = logging.getLogger(__name__)


def _grille_path(grid_type: str, season: str, grille_id: str) -> Path:
    p = Path(DATA_DIR) / grid_type / season
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{grille_id}.json"


def _build_match(
    num: int,
    rep_match: MatchRepart | None,
    hist_match: HistMatch | None,
) -> dict:
    m: dict = {"num": num}

    # Heure (répartition)
    if rep_match:
        m["time"] = rep_match.time or None

    # Équipes : historique en priorité (noms séparés proprement)
    if hist_match:
        m["home"]   = hist_match.home
        m["away"]   = hist_match.away
        m["result"] = hist_match.result
    elif rep_match:
        m["home"]   = rep_match.match_raw   # brut "Home-Away" concat
        m["away"]   = None
        m["result"] = None
    else:
        m["home"] = m["away"] = m["result"] = None

    # Score (répartition)
    m["score"] = rep_match.score if rep_match else None

    # Cotes FDJ
    if rep_match:
        m["cote_1"] = rep_match.cote_1
        m["cote_n"] = rep_match.cote_n
        m["cote_2"] = rep_match.cote_2
    else:
        m["cote_1"] = m["cote_n"] = m["cote_2"] = None

    # Cyborg (algo Pronosoft)
    if rep_match:
        m["cyborg_pct_1"]    = rep_match.cyborg_pct_1
        m["cyborg_pct_n"]    = rep_match.cyborg_pct_n
        m["cyborg_pct_2"]    = rep_match.cyborg_pct_2
        m["cyborg_pct_u"]    = rep_match.cyborg_pct_u
        m["cyborg_pct_o"]    = rep_match.cyborg_pct_o
        m["cyborg_prono"]    = rep_match.cyborg_prono
        m["cyborg_prono_uo"] = rep_match.cyborg_prono_uo
        m["cyborg_fav"]      = rep_match.cyborg_fav
        m["cyborg_fav_uo"]   = rep_match.cyborg_fav_uo
    else:
        for k in ("cyborg_pct_1","cyborg_pct_n","cyborg_pct_2",
                  "cyborg_pct_u","cyborg_pct_o","cyborg_prono",
                  "cyborg_prono_uo","cyborg_fav","cyborg_fav_uo"):
            m[k] = None

    # Bettor % (concours Pronosoft)
    if rep_match:
        m["bettor_pct_1"] = rep_match.bettor_pct_1
        m["bettor_pct_n"] = rep_match.bettor_pct_n
        m["bettor_pct_2"] = rep_match.bettor_pct_2
    else:
        m["bettor_pct_1"] = m["bettor_pct_n"] = m["bettor_pct_2"] = None

    return m


def build_record(
    ref:        GrilleRef,
    rep:        RepartitionPage | None,
    hist:       HistoriquePage  | None,
) -> dict:
    """Construit le dict JSON final en fusionnant les 3 sources."""

    # Index des matchs par num pour la fusion
    rep_by_num:  dict[int, MatchRepart] = {m.num: m for m in (rep.matches  if rep  else [])}
    hist_by_num: dict[int, HistMatch]   = {m.num: m for m in (hist.matches if hist else [])}

    # Nombre de matchs attendu
    nums = sorted(set(list(rep_by_num) + list(hist_by_num)) or [])

    record: dict = {
        "grille_id":          ref.grille_id,
        "grid_type":          ref.grid_type,
        "season":             ref.season,
        "date":               ref.date_str,
        "date_full":          hist.date_str if hist else None,
        "competition":        ref.competition,
        "pactole_eur":        ref.pactole,
        "enjeux_eur":         ref.enjeux,
        "rang1_listing_eur":  ref.rang1,   # rapport rang 1 vu dans le listing
        "rang2_listing_eur":  ref.rang2,
        "nb_pronostics":      rep.nb_pronostics        if rep  else None,
        "total_grille_lines": rep.total_grille_lines   if rep  else None,
        "matches": [
            _build_match(n, rep_by_num.get(n), hist_by_num.get(n))
            for n in nums
        ],
        "rangs": [
            {"rang": r.rang, "nb_gagnants": r.nb_gagnants, "rapport_eur": r.rapport_eur}
            for r in (hist.rangs if hist else [])
        ],
        "stats": hist.stats if hist else {},
    }
    return record


def save_grille(
    ref:  GrilleRef,
    rep:  RepartitionPage | None,
    hist: HistoriquePage  | None,
) -> Path:
    """
    Sauvegarde (upsert) le JSON d'une grille.
    Si le fichier existe, on fusionne pour ne pas perdre de données déjà présentes.
    """
    path = _grille_path(ref.grid_type, ref.season, ref.grille_id)

    new_record = build_record(ref, rep, hist)

    # Upsert : garde les données existantes si les nouvelles sont nulles
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            # Fusionne matches : garde bettor_pct/result existants si None dans le nouveau
            existing_by_num = {m["num"]: m for m in existing.get("matches", [])}
            for m in new_record["matches"]:
                old = existing_by_num.get(m["num"], {})
                for k, v in m.items():
                    if v is None and old.get(k) is not None:
                        m[k] = old[k]
            # Garde rangs existants si nouveaux vides
            if not new_record["rangs"] and existing.get("rangs"):
                new_record["rangs"] = existing["rangs"]
            if not new_record["stats"] and existing.get("stats"):
                new_record["stats"] = existing["stats"]
        except Exception as e:
            logger.warning(f"Upsert {path}: {e} → écrasement")

    path.write_text(
        json.dumps(new_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug(f"Sauvegardé → {path}")
    return path


def grille_exists(grid_type: str, season: str, grille_id: str) -> bool:
    return _grille_path(grid_type, season, grille_id).exists()


def count_files(grid_type: str) -> int:
    d = Path(DATA_DIR) / grid_type
    return len(list(d.rglob("*.json"))) if d.exists() else 0
