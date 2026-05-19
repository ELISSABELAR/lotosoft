BASE_URL = "https://www.pronosoft.com"

# path = chemin dans l'URL répartition (lf7, lf8, lf12, lf15)
# NB : url_stats est maintenant extrait directement du HTML listing (colonne 2)
#      donc path est un fallback uniquement
GRID_TYPES = {
    "grid-7":  {"path": "lf7",  "label": "G7",  "size": 7,  "multiplier": 8},
    "grid-8":  {"path": "lf8",  "label": "G8",  "size": 8,  "multiplier": 16},
    "grid-12": {"path": "lf12", "label": "G12", "size": 12, "multiplier": 72},
    "grid-15": {"path": "lf15", "label": "G15", "size": 15, "multiplier": 216},
}

# Mapping grid_type → slug URL pronosoft pour le listing
GRID_SLUG = {
    "grid-7":  "loto-foot-7",
    "grid-8":  "loto-foot-8",
    "grid-12": "loto-foot-12",
    "grid-15": "loto-foot-15",
}

URL_LISTING = "{base}/fr/lotosports/rapports/{slug}/date/page-{page}/"

DELAY_LISTING  = 2.0
DELAY_RESULTS  = 1.5
DELAY_STATS    = 1.5

BATCH_SIZE = 20

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
