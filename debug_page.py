#!/usr/bin/env python3
"""
debug_page.py — Inspecte la structure HTML d'une page pronosoft.

Utile pour ajuster les parseurs si les sélecteurs CSS ne correspondent pas.

    # Page historique
    python debug_page.py --url https://www.pronosoft.com/fr/lotosports/historiques/loto-foot-7/2025-2026/2026-grille-60/

    # Page répartition
    python debug_page.py --url https://www.pronosoft.com/fr/lotofoot/repartition/lf7/2026-grille-60/

    # Avec sauvegarde HTML
    python debug_page.py --url <url> --save

    # Tous les tableaux en détail
    python debug_page.py --url <url> --full
"""

import argparse, json, re, sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from scraper.config import HEADERS
from scraper.historique import parse_historique_page
from scraper.repartition import parse_repartition_page


def fetch(url: str):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "iso-8859-15"
    return BeautifulSoup(r.text, "lxml"), r.text


def inspect_tables(soup: BeautifulSoup, full: bool = False):
    tables = soup.find_all("table")
    print(f"\n{'='*65}\n  {len(tables)} tableau(x) trouvé(s)\n{'='*65}")
    for ti, tbl in enumerate(tables):
        cls  = " ".join(tbl.get("class", [])) or "(sans classe)"
        rows = tbl.find_all("tr")
        limit = len(rows) if full else min(6, len(rows))
        print(f"\n── Table [{ti}] '{cls}'  ({len(rows)} lignes) ──")
        for ri, row in enumerate(rows[:limit]):
            cells = row.find_all(["th", "td"])
            line  = f"  L{ri:02d} ({len(cells):2d}c)  "
            for ci, c in enumerate(cells[:10]):
                cls2 = ".".join(c.get("class", []))
                txt  = " ".join(c.get_text().split())[:20]
                label = f"{c.name}" + (f".{cls2}" if cls2 else "")
                line += f"[{ci}:{label}='{txt}'] "
            print(line)
        if len(rows) > limit:
            print(f"  ... {len(rows) - limit} lignes supplémentaires")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--save", action="store_true", help="Sauvegarde HTML dans debug/")
    ap.add_argument("--full", action="store_true", help="Affiche toutes les lignes")
    args = ap.parse_args()

    print(f"\nURL : {args.url}")
    try:
        soup, raw = fetch(args.url)
    except Exception as e:
        print(f"[ERREUR] {e}")
        sys.exit(1)

    if args.save:
        Path("debug").mkdir(exist_ok=True)
        slug = re.sub(r"[^a-z0-9-]", "_", args.url.rstrip("/").split("/")[-1])
        p = Path("debug") / f"{slug}.html"
        p.write_text(raw, encoding="utf-8")
        print(f"HTML sauvegardé : {p}")

    inspect_tables(soup, full=args.full)

    # Détecte le type de page et lance le bon parser
    grille_id = args.url.rstrip("/").split("/")[-1]
    print(f"\n{'='*65}\n  Résultat du parser\n{'='*65}")

    if "/historiques/" in args.url:
        result = parse_historique_page(soup, grille_id, args.url)
        print(f"\n✅ Historique — {len(result.matches)} match(s)")
        for m in result.matches:
            print(f"  {m.num:2d}. {m.home[:25]:25s} - {m.away[:25]:25s} "
                  f"| {m.result or '?'} {m.score or ''} | prono={m.prono}")

    elif "/repartition/" in args.url:
        result = parse_repartition_page(soup, grille_id, args.url)
        print(f"\n✅ Répartition — {len(result.matches)} match(s)")
        for m in result.matches:
            print(f"  {m.num:2d}. {m.home[:20]:20s} - {m.away[:20]:20s} "
                  f"| cotes {m.cote_1}/{m.cote_n}/{m.cote_2} "
                  f"| pct {m.pct_1}%/{m.pct_n}%/{m.pct_2}% "
                  f"| {m.result or '?'}")

    else:
        print("\n(page listing — pas de parser spécifique, voir inspect ci-dessus)")

    if hasattr(result, "matches"):
        print("\nJSON extrait :")
        print(json.dumps({
            "grille_id": grille_id,
            "matches": [vars(m) for m in result.matches[:3]]
        }, ensure_ascii=False, indent=2))
        if len(result.matches) > 3:
            print(f"  ... {len(result.matches) - 3} matchs supplémentaires")


if __name__ == "__main__":
    main()
