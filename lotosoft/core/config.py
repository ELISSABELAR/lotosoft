BASE_URL = "https://www.pronosoft.com"

GRID_TYPES = {
    "grid-7":  {"path": "lf7",  "label": "G7",  "size": 7,  "multiplier": 8,   "nb": None, "data_dir": "grid-7"},
    "grid-8":  {"path": "lf8",  "label": "G8",  "size": 8,  "multiplier": 16,  "nb": None, "data_dir": "grid-8"},
    "grid-12": {"path": "lf12", "label": "G12", "size": 12, "multiplier": 72,  "nb": None, "data_dir": "grid-12"},
    "grid-15": {"path": "lf15", "label": "G15", "size": 15, "multiplier": 216, "nb": "15", "data_dir": "grid-15/15"},
    "grid-14": {"path": "lf15", "label": "G14", "size": 14, "multiplier": 216, "nb": "14", "data_dir": "grid-15/14"},
}

URL_LISTING         = "{base}/fr/lotosports/rapports/{grid}/date/page-{page}/"
URL_LISTING_WITH_NB = "{base}/fr/lotosports/rapports/{grid}/{nb}/date/page-{page}/"
URL_RESULTS         = "{base}/fr/lotosports/historiques/{grid}/{season}/{record_id}/"
URL_STATS           = "{base}/fr/lotofoot/repartition/{path}/{record_id}/"

DELAY_LISTING  = 2.0
DELAY_RESULTS  = 1.5
DELAY_STATS    = 1.5

BATCH_SIZE     = 20

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

GRID_URL_MAP = {
    "grid-7":  "loto-foot-7",
    "grid-8":  "loto-foot-8",
    "grid-12": "loto-foot-12",
    "grid-15": "loto-foot-15",
    "grid-14": "loto-foot-15",
}
