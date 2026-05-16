# 🏈 LotoFoot Scraper

Scraper incrémental **100 % GitHub Actions** pour l'historique complet des grilles LotoFoot 7, 8, 12 et 15.

---

## 📁 Arborescence des données

Miroir de la structure des URLs pronosoft :

```
data/
  loto-foot-7/
    2025-2026/
      2026-grille-60.json
      2026-grille-59.json
      ...
    2024-2025/
      2025-grille-XX.json
      ...
  loto-foot-8/
    ...
  loto-foot-12/
    ...
  loto-foot-15/
    ...

state/
  loto-foot-7.json    ← progression du scraping (page courante, grilles vues)
  loto-foot-8.json
  loto-foot-12.json
  loto-foot-15.json
```

---

## 📄 Format d'un fichier grille

`data/loto-foot-7/2025-2026/2026-grille-60.json`

```json
{
  "grille_id": "2026-grille-60",
  "grid_type": "loto-foot-7",
  "season": "2025-2026",
  "date": "14/05",
  "competition": "Ligue 1",
  "rapport": {
    "pactole_eur": 100000,
    "enjeux_eur": 225883,
    "rang1_eur": 154.0,
    "rang2_eur": 14.7
  },
  "historique_url": "https://www.pronosoft.com/fr/lotosports/historiques/loto-foot-7/2025-2026/2026-grille-60/",
  "repartition_url": "https://www.pronosoft.com/fr/lotofoot/repartition/lf7/2026-grille-60/",
  "historique": {
    "url": "https://...",
    "raw_title": "Résultats Grille 60 LotoFoot 7",
    "matches": [
      { "num": 1, "home": "PSG", "away": "Marseille", "result": "1", "score": "2-0", "prono": null }
    ]
  },
  "repartition": {
    "url": "https://...",
    "matches": [
      {
        "num": 1,
        "home": "PSG",
        "away": "Marseille",
        "cotes": { "1": 1.45, "N": 4.20, "2": 6.50 },
        "pct":   { "1": 58.3, "N": 24.1, "2": 17.6 },
        "result": "1",
        "score": "2-0"
      }
    ]
  }
}
```

**Aucun filtrage** : chaque grille est sauvegardée même si la répartition ou l'historique est vide. Le nettoyage se fait en post-traitement.

---

## 🚀 Mise en place (5 minutes)

### 1. Créer le repo GitHub
```bash
git clone https://github.com/<vous>/lotofoot-scraper.git
cd lotofoot-scraper
git push origin main
```

### 2. Activer les permissions Actions
**Settings → Actions → General → Workflow permissions**  
→ Sélectionner **"Read and write permissions"**

### 3. Premier run manuel
**Actions → 🏈 LotoFoot Scraper → Run workflow**
- Grid : `loto-foot-7`
- Batch size : `20`

Le job scrape 20 pages du listing (~400 grilles), pour chacune télécharge
l'historique + la répartition, commite `state/` et `data/`, et s'arrête.

### 4. Les runs suivants sont automatiques
4 runs/jour × 4 grilles en parallèle.  
Avec 20 pages/run et ~244 pages pour LF7 → **historique complet en ~3 jours**.

---

## ⚙️ Sources scrapées par grille

| Source | URL | Contenu |
|---|---|---|
| **Listing rapports** | `/rapports/loto-foot-7/date/page-N/` | Liste des grilles, date, compétition, pactole, enjeux, rang1/2 |
| **Historique** | `/historiques/loto-foot-7/2025-2026/2026-grille-60/` | Matchs, équipes, résultats, scores |
| **Répartition** | `/repartition/lf7/2026-grille-60/` | Cotes 1/N/2, % de mises |

---

## 🔄 Logique incrémentale

```
state/loto-foot-7.json  →  next_page: 45

Run N :
  Pages 45 à 64 (batch = 20)
  Pour chaque grille non encore vue :
    → GET historiques/.../2026-grille-XX/   → data/loto-foot-7/2025-2026/2026-grille-XX.json
    → GET repartition/lf7/2026-grille-XX/  → (fusionné dans le même fichier)
  Sauvegarde state → next_page: 65
  Commit state/ + data/

Run N+1 :
  Repart de next_page: 65
```

---

## 🐛 Diagnostic

Si le parser ne reconnaît pas les colonnes d'une page :

```bash
pip install requests beautifulsoup4 lxml

# Page historique
python debug_page.py --url https://www.pronosoft.com/fr/lotosports/historiques/loto-foot-7/2025-2026/2026-grille-60/

# Page répartition
python debug_page.py --url https://www.pronosoft.com/fr/lotofoot/repartition/lf7/2026-grille-60/

# Avec sauvegarde HTML + tous les tableaux
python debug_page.py --url <url> --save --full
```

Le script affiche la structure des tableaux et le résultat du parser.  
Si les colonnes sont décalées → ajuster `_parse_row()` dans `scraper/historique.py` ou `scraper/repartition.py`.

---

## 📈 Suivi dans GitHub

Après chaque run, l'onglet **Actions → Summary** affiche :

| Grille | Page | Total | Grilles vues | Hist OK | Rép OK | Complet |
|---|---|---|---|---|---|---|
| loto-foot-7 | 65 | 244 | 1280 | 1100 | 950 | ⏳ |
| loto-foot-15 | 12 | 89 | 220 | 200 | 160 | ⏳ |
