#!/usr/bin/env python3
"""
app.py — Batch runner (GitHub Actions).

Usage :
    python app.py --type grid-15
    python app.py --type grid-12 --batch-size 10
    python app.py --type grid-7  --force-page 1
"""
import argparse, logging, os, sys, time
from core.config  import GRID_TYPES, BATCH_SIZE
from core.state   import RunState
from core.listing import fetch_listing_page, detect_total_pages
from core.parser_a import fetch_stats
from core.parser_b import fetch_results
from core.storage  import save_record, count_files
from core.utils    import make_session


def setup_logging(verbose=False):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("run.log", encoding="utf-8", mode="a"),
        ],
    )


logger = logging.getLogger(__name__)


def run(grid_type, batch_size, force_page):
    cfg     = GRID_TYPES[grid_type]
    state   = RunState(grid_type)
    session = make_session()
    start   = force_page if force_page else state.next_page
    pages   = 1 if force_page else batch_size

    logger.info(f"[{grid_type}] pages {start}→{start+pages-1} | done={len(state.done)}")

    n_total = n_stats = n_results = n_skip = 0

    for offset in range(pages):
        page = start + offset
        if state.total_pages > 0 and page > state.total_pages:
            state.complete = True
            break

        soup, refs = fetch_listing_page(session, grid_type, page)
        if soup is None:
            if not force_page:
                state.advance()
            continue

        if page == 1 and state.total_pages == 0:
            state.total_pages = detect_total_pages(soup)
            logger.info(f"[{grid_type}] total pages: {state.total_pages}")

        if not refs:
            if not force_page:
                state.advance()
            continue

        logger.info(f"[{grid_type}] page {page}: {len(refs)} records")

        for ref in refs:
            if state.is_done(ref.record_id):
                continue

            logger.info(f"  {ref.record_id}  {ref.date_str} | {ref.competition}")
            logger.debug(f"    url_stats:   {ref.url_stats}")
            logger.debug(f"    url_results: {ref.url_results}")

            # 1. Répartition (skip si cote manquante ou page absente)
            stats = fetch_stats(session, ref.url_stats, ref.record_id, grid_type)
            if stats is None:
                n_skip += 1
                state.mark(ref.record_id)
                n_total += 1
                continue
            n_stats += 1

            # 2. Résultats officiels
            results = fetch_results(session, ref.url_results, ref.record_id, cfg["size"])
            if results:
                n_results += 1

            # 3. Sauvegarde
            save_record(ref, stats, results)
            state.mark(ref.record_id)
            n_total += 1

        if not force_page:
            state.advance()

    state.stats["total"]      += n_total
    state.stats["stats_ok"]   += n_stats
    state.stats["results_ok"] += n_results
    state.stats["skipped"]    += n_skip
    if not force_page:
        state.save()

    files = count_files(grid_type)
    logger.info(
        f"[{grid_type}] done: total={n_total} stats={n_stats} "
        f"results={n_results} skip={n_skip} files={files}"
    )
    return n_total, n_stats, n_results, n_skip, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type",       required=True, choices=list(GRID_TYPES.keys()))
    ap.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    ap.add_argument("--force-page", type=int, default=None)
    ap.add_argument("--verbose",    action="store_true")
    args = ap.parse_args()
    setup_logging(args.verbose)
    t0 = time.time()
    run(args.type, args.batch_size, args.force_page)
    logger.info(f"Done in {time.time()-t0:.1f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
