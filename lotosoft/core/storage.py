import json, logging
from pathlib import Path
from .config import DATA_DIR, GRID_TYPES
from .listing import RecordRef
from .parser_a import StatsPage, MatchStats
from .parser_b import ResultsPage, MatchResult

logger = logging.getLogger(__name__)

def _record_path(grid_type, season, record_id):
    data_dir = GRID_TYPES[grid_type]["data_dir"]
    p = Path(DATA_DIR) / data_dir / season
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{record_id}.json"

def _build_match(num, a, b):
    m = {"num": num}
    m["time"]   = a.time   if a else None
    m["home"]   = b.home   if b else (a.match_raw if a else None)
    m["away"]   = b.away   if b else None
    m["result"] = b.result if b else None
    m["score"]  = a.score  if a else None
    for k in ("cote_1","cote_n","cote_2",
              "cyborg_pct_1","cyborg_pct_n","cyborg_pct_2",
              "cyborg_pct_u","cyborg_pct_o",
              "cyborg_prono","cyborg_prono_uo",
              "cyborg_fav","cyborg_fav_uo",
              "bettor_pct_1","bettor_pct_n","bettor_pct_2"):
        m[k] = getattr(a, k, None) if a else None
    return m

def build_record(ref, stats, results):
    a_by_num = {m.num: m for m in (stats.matches   if stats   else [])}
    b_by_num = {m.num: m for m in (results.matches if results else [])}
    nums = sorted(set(list(a_by_num) + list(b_by_num)) or [])
    return {
        "record_id":          ref.record_id,
        "grid_type":          ref.grid_type,
        "season":             ref.season,
        "date":               ref.date_str,
        "date_full":          results.date_str if results else None,
        "competition":        ref.competition,
        "pactole_eur":        ref.pactole,
        "enjeux_eur":         ref.enjeux,
        "rang1_eur":          ref.rang1,
        "rang2_eur":          ref.rang2,
        "nb_entries":         stats.nb_entries         if stats else None,
        "total_combinations": stats.total_combinations if stats else None,
        "matches": [_build_match(n, a_by_num.get(n), b_by_num.get(n)) for n in nums],
        "ranks": [
            {"rank": r.rank, "nb_winners": r.nb_winners, "payout_eur": r.payout_eur}
            for r in (results.ranks if results else [])
        ],
        "stats": results.stats if results else {},
    }

def save_record(ref, stats, results):
    path = _record_path(ref.grid_type, ref.season, ref.record_id)
    new  = build_record(ref, stats, results)
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            old_by_num = {m["num"]: m for m in old.get("matches", [])}
            for m in new["matches"]:
                o = old_by_num.get(m["num"], {})
                for k, v in m.items():
                    if v is None and o.get(k) is not None: m[k] = o[k]
            if not new["ranks"] and old.get("ranks"): new["ranks"] = old["ranks"]
            if not new["stats"] and old.get("stats"): new["stats"] = old["stats"]
        except Exception as e:
            logger.warning(f"upsert {path}: {e}")
    path.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def count_files(grid_type):
    data_dir = GRID_TYPES[grid_type]["data_dir"]
    d = Path(DATA_DIR) / data_dir
    return len(list(d.rglob("*.json"))) if d.exists() else 0
