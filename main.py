#!/usr/bin/env python3
"""
Orchestrateur batch — GitHub Actions.

Pour chaque grille du listing :
  1. Répartition → cotes FDJ + cyborg + bettor % (skip si cote manquante)
  2. Historique  → équipes propres + résultats + rangs
  3. Fusion → data/{grid_type}/{season}/{grille_id}.json

Usage :
    python main.py --grid loto-foot-15
    python main.py --grid loto-foot-15 --batch-size 10
    python main.py --grid loto-foot-15 --force-page 1
"""
import argparse, logging, os, sys, time
from scraper.config import GRID_TYPES, BATCH_SIZE_PAGES
from scraper.state import ScraperState
from scraper.rapports import fetch_listing_page, detect_total_pages
from scraper.repartition import fetch_repartition
from scraper.historique import fetch_historique
from scraper.storage import save_grille, count_files
from scraper.utils import make_session

def setup_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler("scraper.log", encoding="utf-8", mode="a")],
    )

logger = logging.getLogger(__name__)

def run_batch(grid_type, batch_size, force_page):
    cfg     = GRID_TYPES[grid_type]
    state   = ScraperState(grid_type)
    session = make_session()
    start   = force_page if force_page else state.next_page
    pages   = 1 if force_page else batch_size

    logger.info(f"\n{'='*60}\n  {cfg['label']} | pages {start}→{start+pages-1} | "
                f"grilles vues: {len(state.grilles_done)}\n{'='*60}")

    n_total = n_rep = n_hist = n_skip = 0

    for offset in range(pages):
        page = start + offset
        if state.total_pages > 0 and page > state.total_pages:
            state.history_complete = True; break

        soup, refs = fetch_listing_page(session, grid_type, page)
        if soup is None:
            if not force_page: state.advance_page()
            continue

        if page == 1 and state.total_pages == 0:
            state.total_pages = detect_total_pages(soup)
            logger.info(f"[{grid_type}] Total pages: {state.total_pages}")

        if not refs:
            if not force_page: state.advance_page()
            continue

        logger.info(f"[{grid_type}] Page {page}: {len(refs)} grilles")

        for ref in refs:
            if state.is_done(ref.grille_id):
                continue

            logger.info(f"  {ref.grille_id}  {ref.date_str} | {ref.competition}")

            # 1. Répartition (skip si cote manquante)
            rep = fetch_repartition(session, ref.repartition_url, ref.grille_id, grid_type)
            if rep is None:
                logger.info(f"     → répartition: skippée (cote manquante ou page absente)")
                n_skip += 1
                state.mark_done(ref.grille_id)
                n_total += 1
                continue   # pas de sauvegarde pour cette grille
            n_rep += 1
            logger.info(f"     → répartition: OK ({len(rep.matches)} matchs)")

            # 2. Historique (résultats + noms propres + rangs)
            hist = fetch_historique(session, ref.historique_url, ref.grille_id, cfg["size"])
            if hist:
                n_hist += 1
                logger.info(f"     → historique: OK ({len(hist.matches)} matchs, "
                             f"{len(hist.rangs)} rangs)")
            else:
                logger.info(f"     → historique: absent ou non encore disponible")

            # 3. Sauvegarde
            save_grille(ref, rep, hist)
            state.mark_done(ref.grille_id)
            n_total += 1

        if not force_page:
            state.advance_page()

    state.stats["total"]   += n_total
    state.stats["rep_ok"]  += n_rep
    state.stats["hist_ok"] += n_hist
    state.stats["skipped"] += n_skip
    if not force_page:
        state.save()

    stats = {
        "grilles_this_run": n_total, "rep_ok": n_rep,
        "hist_ok": n_hist, "skipped": n_skip,
        "total_files": count_files(grid_type),
        "next_page": state.next_page, "total_pages": state.total_pages,
        "history_complete": state.history_complete, "cumulative": state.stats,
    }
    logger.info(f"\n[{grid_type}] Batch: total={n_total} rep={n_rep} "
                f"hist={n_hist} skip={n_skip} fichiers={stats['total_files']}")
    return stats

def write_github_summary(grid_type, stats, elapsed):
    f = os.environ.get("GITHUB_STEP_SUMMARY")
    if not f: return
    label = GRID_TYPES[grid_type]["label"]
    c = stats["cumulative"]
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(f"\n## 📊 {label}\n\n")
        fh.write("| Métrique | Valeur |\n|---|---|\n")
        for k, v in [
            ("Grilles ce run", stats["grilles_this_run"]),
            ("Répartition OK", stats["rep_ok"]),
            ("Historique OK",  stats["hist_ok"]),
            ("Skippées (cote manquante)", stats["skipped"]),
            ("**Fichiers total**", f"**{stats['total_files']}**"),
            ("Progression", f"{stats['next_page']-1}/{stats['total_pages']} pages"),
            ("Historique complet", "✅" if stats["history_complete"] else "⏳"),
            ("Durée", f"{elapsed:.0f}s"),
        ]:
            fh.write(f"| {k} | {v} |\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True, choices=list(GRID_TYPES.keys()))
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE_PAGES)
    ap.add_argument("--force-page", type=int, default=None)
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    setup_logging(args.verbose)
    t0 = time.time()
    stats = run_batch(args.grid, args.batch_size, args.force_page)
    elapsed = time.time() - t0
    logger.info(f"Durée: {elapsed:.1f}s")
    write_github_summary(args.grid, stats, elapsed)
    sys.exit(0)

if __name__ == "__main__":
    main()
