"""Configuration centrale."""

BASE_URL = "https://www.pronosoft.com"

GRID_TYPES = {
    "loto-foot-7":  {"path": "lf7",  "label": "LotoFoot 7",  "size": 7,  "multiplier": 8},    # 2^3
    "loto-foot-8":  {"path": "lf8",  "label": "LotoFoot 8",  "size": 8,  "multiplier": 16},   # 2^4
    "loto-foot-12": {"path": "lf12", "label": "LotoFoot 12", "size": 12, "multiplier": 72},   # 2^3 × 3^2
    "loto-foot-15": {"path": "lf15", "label": "LotoFoot 15", "size": 15, "multiplier": 216},  # 2^3 × 3^3
}

RAPPORTS_PAGE_URL = "{base}/fr/lotosports/rapports/{grid}/date/page-{page}/"
HISTORIQUE_URL    = "{base}/fr/lotosports/historiques/{grid}/{season}/{grille_id}/"
REPARTITION_URL   = "{base}/fr/lotofoot/repartition/{path}/{grille_id}/"

DELAY_LISTING     = 2.0
DELAY_HISTORIQUE  = 1.5
DELAY_REPARTITION = 1.5

BATCH_SIZE_PAGES  = 20

STATE_DIR = "state"
DATA_DIR  = "data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.pronosoft.com/",
}
