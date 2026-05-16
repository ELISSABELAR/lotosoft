"""État incrémental persisté dans state/{grid_type}.json."""
import json, logging
from datetime import datetime, timezone
from pathlib import Path
from .config import STATE_DIR
logger = logging.getLogger(__name__)

class ScraperState:
    def __init__(self, grid_type):
        self.grid_type = grid_type
        self._path = Path(STATE_DIR) / f"{grid_type}.json"
        self.next_page = 1; self.total_pages = 0
        self.history_complete = False; self.grilles_done = set()
        self.stats = {"total": 0, "rep_ok": 0, "hist_ok": 0, "skipped": 0}
        self._load()

    def _load(self):
        if not self._path.exists(): return
        try:
            d = json.loads(self._path.read_text(encoding="utf-8"))
            self.next_page = d.get("next_page", 1)
            self.total_pages = d.get("total_pages", 0)
            self.history_complete = d.get("history_complete", False)
            self.grilles_done = set(d.get("grilles_done", []))
            self.stats = d.get("stats", self.stats)
            logger.info(f"[{self.grid_type}] État: page {self.next_page}/{self.total_pages or '?'}, "
                        f"{len(self.grilles_done)} grilles, complet={self.history_complete}")
        except Exception as e:
            logger.warning(f"[{self.grid_type}] Lecture état KO ({e})")

    def save(self):
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({
            "grid_type": self.grid_type, "next_page": self.next_page,
            "total_pages": self.total_pages, "history_complete": self.history_complete,
            "grilles_done": sorted(self.grilles_done), "stats": self.stats,
            "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark_done(self, gid): self.grilles_done.add(gid)
    def is_done(self, gid): return gid in self.grilles_done
    def advance_page(self):
        self.next_page += 1
        if self.total_pages > 0 and self.next_page > self.total_pages:
            self.history_complete = True
