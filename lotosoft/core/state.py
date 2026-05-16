import json, logging
from datetime import datetime, timezone
from pathlib import Path
from .config import STATE_DIR

logger = logging.getLogger(__name__)

class RunState:
    def __init__(self, grid_type):
        self.grid_type = grid_type
        self._path = Path(STATE_DIR) / f"{grid_type}.json"
        self.next_page = 1
        self.total_pages = 0
        self.complete = False
        self.done = set()
        self.stats = {"total": 0, "stats_ok": 0, "results_ok": 0, "skipped": 0}
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        try:
            d = json.loads(self._path.read_text(encoding="utf-8"))
            self.next_page   = d.get("next_page", 1)
            self.total_pages = d.get("total_pages", 0)
            self.complete    = d.get("complete", False)
            self.done        = set(d.get("done", []))
            self.stats       = d.get("stats", self.stats)
            logger.info(f"[{self.grid_type}] state: page {self.next_page}/{self.total_pages or '?'}, "
                        f"{len(self.done)} records, complete={self.complete}")
        except Exception as e:
            logger.warning(f"[{self.grid_type}] state read error ({e})")

    def save(self):
        Path(STATE_DIR).mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({
            "grid_type":   self.grid_type,
            "next_page":   self.next_page,
            "total_pages": self.total_pages,
            "complete":    self.complete,
            "done":        sorted(self.done),
            "stats":       self.stats,
            "last_run":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def mark(self, rid):
        self.done.add(rid)

    def is_done(self, rid):
        return rid in self.done

    def advance(self):
        self.next_page += 1
        if self.total_pages > 0 and self.next_page > self.total_pages:
            self.complete = True
