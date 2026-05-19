# lotosoft

Football statistics analysis tool.

## Data

```
data/
  grid-15/
    2025-2026/
      2026-grille-36.json
      ...
    2004-2005/
      ...
  grid-12/
  grid-8/
  grid-7/
state/
  grid-15.json
  ...
```

## Usage

```bash
pip install -r requirements.txt
python app.py --type grid-15 --batch-size 20
python audit.py   # test all grid types
```
