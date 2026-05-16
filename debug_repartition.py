#!/usr/bin/env python3
"""
debug_repartition.py — Inspecte la structure HTML d'une page de répartition.

À lancer UNE FOIS depuis une machine ayant accès au site,
pour valider que le parser détecte bien les colonnes.

    python debug_repartition.py
    python debug_repartition.py --url .../lf7/2026-grille-58/
    python debug_repartition.py --save   # sauvegarde le HTML dans debug/
    python debug_repartition.py --all-tables  # affiche TOUS les tableaux
"""

import argparse, json, re, sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from scraper.config import HEADERS, BASE_URL
from scraper.repartition import parse_repartition_page

DEFAULT_URL = f"{BASE_URL}/fr/lotofoot/repartition/lf7/2026-grille-58/"


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "iso-8859-15"
    return BeautifulSoup(r.text, "lxml"), r.text


def inspect(soup, all_tables=False):
    tables = soup.find_all("table")
    print(f"\n{'='*65}")
    print(f"  {len(tables)} tableau(x) dans la page")
    print(f"{'='*65}")

    for ti, table in enumerate(tables):
        cls = " ".join(table.get("class", [])) or "(sans classe)"
        rows = table.find_all("tr")
        max_show = len(rows) if all_tables else min(6, len(rows))

        print(f"\n── Table [{ti}] class='{cls}'  ({len(rows)} lignes) ──")
        for ri, row in enumerate(rows[:max_show]):
            cells = row.find_all(["th", "td"])
            line  = f"  L{ri:02d} ({len(cells)} cells) "
            for ci, c in enumerate(cells[:12]):
                tag  = c.name
                cls2 = ".".join(c.get("class", [])) or ""
                txt  = " ".join(c.get_text().split())[:18]
                line += f"[{ci}:{tag}{'.' + cls2 if cls2 else ''}='{txt}'] "
            print(line)
        if len(rows) > max_show:
            print(f"  … {len(rows) - max_show} lignes supplémentaires")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--all-tables", action="store_true")
    args = ap.parse_args()

    print(f"Fetching : {args.url}")
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

    inspect(soup, all_tables=args.all_tables)

    print(f"\n{'='*65}")
    print("  Résultat du parser scraper/repartition.py")
    print(f"{'='*65}")

    grille_id = args.url.rstrip("/").split("/")[-1]
    rep = parse_repartition_page(soup, grille_id, "loto-foot-7", args.url)

    if rep is None:
        print("\n⚠️  Parser → None")
        print("   Causes possibles :")
        print("   • Cotes absentes (grille trop ancienne ou en attente)")
        print("   • Sélecteurs CSS à ajuster dans scraper/repartition.py")
        print("   → Regardez inspect() ci-dessus pour trouver les bonnes classes")
    else:
        print(f"\n✅  {len(rep.matches)} match(s), cotes complètes={rep.has_all_cotes}")
        for m in rep.matches:
            print(
                f"  {m.num:2d}. {m.home[:22]:22s} - {m.away[:22]:22s} | "
                f"Cotes {m.cote_1}/{m.cote_n}/{m.cote_2} | "
                f"Pct {m.pct_1}%/{m.pct_n}%/{m.pct_2}% | "
                f"→ {m.result or '?'} {m.score or ''}"
            )
        print("\nJSON :")
        print(json.dumps({
            "grille_id": rep.grille_id,
            "matches": [{
                "num": m.num, "home": m.home, "away": m.away,
                "cotes": {"1": m.cote_1, "N": m.cote_n, "2": m.cote_2},
                "pct":   {"1": m.pct_1,  "N": m.pct_n,  "2": m.pct_2},
                "result": m.result, "score": m.score,
            } for m in rep.matches]
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
