#!/usr/bin/env python3
"""
test.py — Valide les parseurs sur les 3 fichiers HTML réels uploadés.

    python test.py
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bs4 import BeautifulSoup
from core.parser_a import parse_stats_page
from core.parser_b import parse_results_page
from core.storage  import build_record
from core.listing  import RecordRef

REP33  = "/mnt/user-data/uploads/Répartition_Loto_Foot_15_n_33_-_28_04_à_20h55.html"
REP36  = "/mnt/user-data/uploads/Répartition_Loto_Foot_15_n_36_-_10_05_à_14h55.html"
HIST36 = "/mnt/user-data/uploads/Résultats_et_rapports_officiels_-_Grille_n_36_-_10_05_2026_à_15h00.html"

def load(path):
    with open(path, encoding="latin-1") as f:
        return BeautifulSoup(f.read(), "lxml")

ok  = lambda msg: print(f"  ✅ {msg}")
err = lambda msg: print(f"  ❌ {msg}")
sep = lambda t:   print(f"\n{'='*60}\n  {t}\n{'='*60}")


def test_skip():
    sep("Grille 33 — doit être SKIPPÉE (cote manquante)")
    soup   = load(REP33)
    result = parse_stats_page(soup, "2026-grille-33", "grid-15", "http://test/")
    if result is None:
        ok("parse_stats_page → None  (skip correct ✓)")
    else:
        err(f"Devrait être None ! {len(result.matches)} matchs retournés")
        for m in result.matches:
            if None in (m.cote_1, m.cote_n, m.cote_2):
                print(f"     match {m.num} {m.match_raw[:25]} c1={m.cote_1} cn={m.cote_n} c2={m.cote_2}")


def test_rep36():
    sep("Grille 36 — Répartition (toutes cotes présentes)")
    soup   = load(REP36)
    result = parse_stats_page(soup, "2026-grille-36", "grid-15", "http://test/")
    if result is None:
        err("parse_stats_page → None (ne devrait PAS être skippée !)")
        return None

    ok(f"{len(result.matches)} matchs parsés")
    ok(f"nb_entries={result.nb_entries}  total_combinations={result.total_combinations}  (= {result.nb_entries}×216)")

    print(f"\n  {'#':>2} {'Match':<35} {'c1':>5} {'cn':>5} {'c2':>5} {'b1%':>6} {'bn%':>6} {'b2%':>6} score")
    print("  " + "-"*95)
    all_ok = True
    for m in result.matches:
        missing = [k for k,v in [("c1",m.cote_1),("cn",m.cote_n),("c2",m.cote_2)] if v is None]
        flag    = " ⚠" if missing else ""
        if missing:
            all_ok = False
        print(
            f"  {m.num:>2} {m.match_raw:<35} "
            f"{str(m.cote_1 or '-'):>5} {str(m.cote_n or '-'):>5} {str(m.cote_2 or '-'):>5} "
            f"{str(m.bettor_pct_1 or '-'):>6} {str(m.bettor_pct_n or '-'):>6} {str(m.bettor_pct_2 or '-'):>6} "
            f"{m.score or '-'}{flag}"
        )

    if all_ok:
        ok("Toutes les cotes présentes")
    else:
        err("Certaines cotes manquantes")

    # Vérifie que bettor sum ≈ 100
    for m in result.matches:
        if None not in (m.bettor_pct_1, m.bettor_pct_n, m.bettor_pct_2):
            s = m.bettor_pct_1 + m.bettor_pct_n + m.bettor_pct_2
            if abs(s - 100) > 5:
                print(f"  ⚠ match {m.num}: bettor sum = {s:.1f}% (≠ 100)")

    return result


def test_hist36():
    sep("Grille 36 — Historique / Résultats officiels")
    soup   = load(HIST36)
    result = parse_results_page(soup, "2026-grille-36", "http://test/", grid_size=15)
    if result is None:
        err("parse_results_page → None")
        return None

    ok(f"{len(result.matches)} matchs | date: '{result.date_str}'")
    print(f"\n  {'#':>2} {'Home':<25} {'Away':<25} res")
    print("  " + "-"*60)
    for m in result.matches:
        print(f"  {m.num:>2}. {m.home:<25} {m.away:<25} {m.result or '?'}")

    missing_res = [m.num for m in result.matches if m.result is None]
    if not missing_res:
        ok("Tous les résultats parsés")
    else:
        err(f"Résultats manquants : matchs {missing_res}")

    print(f"\n  Rangs ({len(result.ranks)}) :")
    for r in result.ranks:
        print(f"    rang {r.rank:>2} | {r.nb_winners:>6} gagnants | {r.payout_eur or '?':>12} €")
    ok(f"{len(result.ranks)} rangs parsés") if result.ranks else err("Aucun rang !")

    if result.stats:
        ok(f"Stats: {result.stats}")

    return result


def test_fusion(rep, hist):
    sep("Fusion répartition + historique → JSON final")
    if rep is None or hist is None:
        print("  (ignoré — données manquantes)")
        return

    ref = RecordRef(
        grid_type="grid-15", record_id="2026-grille-36", season="2025-2026",
        date_str="10/05", competition="Ligue 1",
        pactole=None, enjeux=225883.0, rang1=154.0, rang2=14.7,
        url_results="http://test/hist/", url_stats="http://test/rep/",
    )
    record = build_record(ref, rep, hist)

    print(f"  {len(record['matches'])} matchs fusionnés | {len(record['ranks'])} rangs")
    print(f"\n  {'#':>2} {'Home':<22} {'Away':<22} res  score  c1     cn     c2     b1%    bn%    b2%")
    print("  " + "-"*100)
    for m in record["matches"]:
        print(
            f"  {m['num']:>2} {str(m['home'] or '?'):<22} {str(m['away'] or '?'):<22} "
            f"{m['result'] or '?':>3}  {m['score'] or '?':>5}  "
            f"{str(m['cote_1'] or '-'):>5}  {str(m['cote_n'] or '-'):>5}  {str(m['cote_2'] or '-'):>5}  "
            f"{str(m['bettor_pct_1'] or '-'):>5}  {str(m['bettor_pct_n'] or '-'):>5}  {str(m['bettor_pct_2'] or '-'):>5}"
        )
    print("\n  Exemple JSON match 1 :")
    print("  " + json.dumps(record["matches"][0], ensure_ascii=False, indent=4).replace("\n","\n  "))
    ok("Fusion OK")


def main():
    test_skip()
    rep  = test_rep36()
    hist = test_hist36()
    test_fusion(rep, hist)
    print(f"\n{'='*60}\n  Tests terminés\n{'='*60}\n")


if __name__ == "__main__":
    main()
