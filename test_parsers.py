#!/usr/bin/env python3
"""
test_parsers.py — Valide les parseurs sur les fichiers HTML réels.

Lance depuis la racine du projet :
    python test_parsers.py

Les 3 fichiers HTML doivent être dans le même dossier que ce script,
ou passer les chemins en argument :
    python test_parsers.py --rep33 /path/repart_33.html \
                           --rep36 /path/repart_36.html \
                           --hist36 /path/hist_36.html
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bs4 import BeautifulSoup
from scraper.repartition import parse_repartition_page
from scraper.historique import parse_historique_page


# ─────────────────────────────────────────────────────────────────────────────

def load_html(path: str) -> BeautifulSoup:
    with open(path, encoding="latin-1") as f:
        return BeautifulSoup(f.read(), "lxml")

def section(title: str):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

def ok(msg):  print(f"  ✅ {msg}")
def err(msg): print(f"  ❌ {msg}")
def info(msg):print(f"     {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 : Grille 33 — cotes manquantes → doit retourner None
# ─────────────────────────────────────────────────────────────────────────────

def test_grille33_skip(path: str):
    section("Grille 33 — doit être SKIPPÉE (cotes manquantes)")
    soup = load_html(path)
    result = parse_repartition_page(soup, "2026-grille-33", "loto-foot-15",
                                    "http://test/rep33/")
    if result is None:
        ok("parse_repartition_page → None  (skip correct)")
    else:
        err(f"parse_repartition_page → {len(result.matches)} matchs (devrait être None !)")
        for m in result.matches:
            if m.cote_1 is None or m.cote_n is None or m.cote_2 is None:
                info(f"Match {m.num:2d} {m.match_raw[:30]:30s} | "
                     f"c1={m.cote_1} cn={m.cote_n} c2={m.cote_2}  ← manquante")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 : Grille 36 — cotes complètes → doit retourner les données
# ─────────────────────────────────────────────────────────────────────────────

def test_grille36_repartition(path: str):
    section("Grille 36 — Répartition (cotes complètes)")
    soup = load_html(path)
    rep = parse_repartition_page(soup, "2026-grille-36", "loto-foot-15",
                                 "http://test/rep36/")
    if rep is None:
        err("parse_repartition_page → None (ne devrait pas être skippée !)")
        return None

    ok(f"{len(rep.matches)} matchs parsés")
    ok(f"nb_pronostics = {rep.nb_pronostics}  |  "
       f"total_grille_lines = {rep.total_grille_lines}  "
       f"(= {rep.nb_pronostics} × 216)")

    print("\n  Matchs (cyborg pct + cotes FDJ + bettor %) :")
    print(f"  {'#':>2} {'Match brut':<35} {'c1':>5} {'cn':>5} {'c2':>5} "
          f"{'cp1':>5} {'cpn':>5} {'cp2':>5} "
          f"{'b1':>6} {'bn':>6} {'b2':>6} {'score'}")
    print("  " + "-"*115)

    issues = []
    for m in rep.matches:
        missing_cotes  = [k for k, v in [("c1",m.cote_1),("cn",m.cote_n),("c2",m.cote_2)] if v is None]
        missing_bettor = [k for k, v in [("b1",m.bettor_pct_1),("bn",m.bettor_pct_n),("b2",m.bettor_pct_2)] if v is None]
        flag = "⚠" if missing_cotes else ""

        print(f"  {m.num:>2} {m.match_raw:<35} "
              f"{m.cote_1 or '-':>5} {m.cote_n or '-':>5} {m.cote_2 or '-':>5} "
              f"{m.cyborg_pct_1 or '-':>5} {m.cyborg_pct_n or '-':>5} {m.cyborg_pct_2 or '-':>5} "
              f"{m.bettor_pct_1 or '-':>6} {m.bettor_pct_n or '-':>6} {m.bettor_pct_2 or '-':>6} "
              f"{m.score or '-'} {flag}")

        if missing_cotes:
            issues.append(f"Match {m.num}: cote(s) manquante(s): {missing_cotes}")
        if missing_bettor:
            info(f"Match {m.num}: bettor % absent: {missing_bettor}")

    if not issues:
        ok("Toutes les cotes sont présentes")
    else:
        for i in issues: err(i)

    # Vérif bettor sum ≈ 100
    for m in rep.matches:
        if None not in (m.bettor_pct_1, m.bettor_pct_n, m.bettor_pct_2):
            total = m.bettor_pct_1 + m.bettor_pct_n + m.bettor_pct_2
            if abs(total - 100) > 5:
                info(f"Match {m.num}: bettor sum = {total:.1f}% (≠ 100)")

    return rep


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 : Historique grille 36 → résultats + rangs
# ─────────────────────────────────────────────────────────────────────────────

def test_grille36_historique(path: str):
    section("Grille 36 — Historique / Rapports officiels")
    soup = load_html(path)
    hist = parse_historique_page(soup, "2026-grille-36", "http://test/hist36/", grid_size=15)

    if hist is None:
        err("parse_historique_page → None")
        return None

    ok(f"{len(hist.matches)} matchs | date: '{hist.date_str}'")

    print("\n  Matchs (résultats) :")
    for m in hist.matches:
        res = m.result or "?"
        print(f"  {m.num:>2}. {m.home:<25} vs {m.away:<25}  → {res}")

    issues_res = [m.num for m in hist.matches if m.result is None]
    if not issues_res:
        ok("Tous les résultats parsés")
    else:
        err(f"Résultats manquants pour matchs: {issues_res}")

    print(f"\n  Rapports par rang ({len(hist.rangs)} rangs) :")
    for r in hist.rangs:
        print(f"  Rang {r.rang:>2} | {r.nb_gagnants:>6} gagnants | {r.rapport_eur:>12.2f} €")

    if hist.rangs:
        ok(f"{len(hist.rangs)} rangs parsés")
    else:
        err("Aucun rang parsé !")

    if hist.stats:
        ok(f"Stats: {hist.stats}")
    else:
        info("Stats globales absentes (page peut-être avant résultats)")

    return hist


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 : Fusion répartition + historique
# ─────────────────────────────────────────────────────────────────────────────

def test_fusion(rep, hist):
    if rep is None or hist is None:
        print("\n  (fusion ignorée — données manquantes)")
        return

    section("Fusion répartition + historique")
    from scraper.rapports import GrilleRef
    from scraper.storage import build_record

    ref = GrilleRef(
        grid_type="loto-foot-15", grille_id="2026-grille-36", season="2025-2026",
        date_str="10/05", competition="Ligue 1",
        pactole=None, enjeux=225883.0, rang1=154.0, rang2=14.7,
        historique_url="http://test/hist36/", repartition_url="http://test/rep36/",
    )

    record = build_record(ref, rep, hist)

    print(f"\n  JSON fusionné ({len(record['matches'])} matchs, "
          f"{len(record['rangs'])} rangs) :")
    print("  " + "-"*90)
    for m in record["matches"]:
        print(f"  {m['num']:>2}. {m['home'] or '?':<22} vs {m['away'] or '?':<22} "
              f"| res={m['result'] or '?'} score={m['score'] or '?'} "
              f"| c1={m['cote_1']} cn={m['cote_n']} c2={m['cote_2']} "
              f"| b1={m['bettor_pct_1']} bn={m['bettor_pct_n']} b2={m['bettor_pct_2']}")

    print("\n  Exemple JSON (match 1) :")
    print("  " + json.dumps(record["matches"][0], ensure_ascii=False, indent=4)
                    .replace("\n", "\n  "))
    ok("Fusion OK")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rep33", default=(
        "/mnt/user-data/uploads/Répartition_Loto_Foot_15_n_33_-_28_04_à_20h55.html"))
    ap.add_argument("--rep36", default=(
        "/mnt/user-data/uploads/Répartition_Loto_Foot_15_n_36_-_10_05_à_14h55.html"))
    ap.add_argument("--hist36", default=(
        "/mnt/user-data/uploads/Résultats_et_rapports_officiels_-_Grille_n_36_-_10_05_2026_à_15h00.html"))
    args = ap.parse_args()

    test_grille33_skip(args.rep33)
    rep  = test_grille36_repartition(args.rep36)
    hist = test_grille36_historique(args.hist36)
    test_fusion(rep, hist)

    print(f"\n{'='*65}")
    print("  Tests terminés")
    print(f"{'='*65}\n")

if __name__ == "__main__":
    main()
