#!/usr/bin/env python3
"""
audit.py — Audit toutes les grilles via GitHub Actions.

Télécharge la page 1 du listing pour chaque type, puis pour la première
grille non-skippée :
  - Affiche l'URL répartition extraite du HTML
  - Montre les tables trouvées dans la page répartition
  - Détaille le résultat du parser

Usage dans GitHub Actions (voir workflow update.yml) :
    python audit.py

En local (avec accès au site) :
    python audit.py --verbose
"""

import logging, sys
from core.config   import GRID_TYPES
from core.listing  import fetch_listing_page, detect_total_pages
from core.parser_a import parse_stats_page, fetch_stats
from core.parser_b import parse_results_page
from core.utils    import make_session, fetch, clean

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SEPARATOR = "=" * 65


def audit_grid(session, grid_type):
    print(f"\n{SEPARATOR}")
    print(f"  AUDIT: {grid_type} ({GRID_TYPES[grid_type]['label']})")
    print(SEPARATOR)

    # 1. Listing page 1
    soup, refs = fetch_listing_page(session, grid_type, 1)
    if soup is None:
        print("  ❌ Listing page 1 inaccessible")
        return

    total = detect_total_pages(soup)
    print(f"  ✓ Listing page 1 OK — {len(refs)} grilles — {total} pages au total")

    if not refs:
        print("  ❌ Aucune grille dans le listing")
        return

    # Affiche les URLs extraites pour les 3 premières grilles
    print(f"\n  URLs extraites du HTML (3 premières grilles) :")
    for ref in refs[:3]:
        print(f"    {ref.record_id} | stats: {ref.url_stats}")

    # 2. Test sur la première grille
    ref = refs[0]
    print(f"\n  Test répartition sur {ref.record_id} ({ref.date_str}) :")
    print(f"    URL : {ref.url_stats}")

    soup2, status = fetch(session, ref.url_stats, delay=1.5)
    if soup2 is None:
        print(f"  ❌ HTTP {status} → URL incorrecte ou page absente")
        return

    print(f"  ✓ Page chargée (HTTP 200)")

    # Tables dans la page
    bloc   = soup2.find(id="bloccontenu") or soup2
    tables = bloc.find_all("table")
    print(f"\n  Tables trouvées ({len(tables)}) :")
    for i, t in enumerate(tables):
        cls  = " ".join(t.get("class", [])) or "(sans classe)"
        rows = t.find_all("tr")
        # Compte les colonnes de la première ligne non-header
        ncols = 0
        for r in rows:
            cells = r.find_all("td")
            if cells:
                ncols = len(cells)
                break
        marker = " ← TABLE PRINCIPALE" if "prono-cyb-des" in cls else ""
        print(f"    [{i}] class='{cls}' — {len(rows)} lignes, ~{ncols} cols/ligne{marker}")

    # Parse
    print(f"\n  Résultat du parser :")
    result = parse_stats_page(soup2, ref.record_id, grid_type, ref.url_stats)
    if result is None:
        print("  ❌ parse_stats_page → None")
        # Diagnostic : afficher le contenu de prono-cyb-des si présente
        main = bloc.find("table", class_="prono-cyb-des")
        if main:
            print("     Table prono-cyb-des trouvée, premières lignes :")
            for r in main.find_all("tr")[:4]:
                cells = r.find_all(["th","td"])
                row_data = [f"[{' '.join(c.get('class',[])) or c.name}|{clean(c.get_text())[:20]}]"
                            for c in cells]
                print("     " + " ".join(row_data))
        else:
            print("     Table prono-cyb-des ABSENTE dans la page")
    else:
        print(f"  ✓ {len(result.matches)} matchs parsés | nb_entries={result.nb_entries}")
        for m in result.matches[:3]:
            print(
                f"    {m.num:2d}. {m.match_raw[:30]:30s} | "
                f"c1={m.cote_1} cn={m.cote_n} c2={m.cote_2} | "
                f"b1={m.bettor_pct_1}%"
            )
        if len(result.matches) > 3:
            print(f"    ... {len(result.matches)-3} autres matchs")


def main():
    session = make_session()
    for grid_type in GRID_TYPES:
        try:
            audit_grid(session, grid_type)
        except Exception as e:
            print(f"\n  ❌ Erreur inattendue pour {grid_type}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{SEPARATOR}")
    print("  Audit terminé")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
