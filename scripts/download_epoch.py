"""Download the Epoch AI data centres file into data/raw/ exactly as published.
Run once from the repo root:  python scripts/download_epoch.py
Never edit the saved file by hand; every change happens in src/tab2_prep.py."""

from datetime import date
from pathlib import Path
from urllib.request import urlretrieve

URL = "https://epoch.ai/data/data_centers/data_centers.csv"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "data_centers.csv"

OUT.parent.mkdir(parents=True, exist_ok=True)
urlretrieve(URL, OUT)
rows = sum(1 for _ in OUT.open(encoding="utf-8")) - 1
print(f"Saved {OUT} ({rows} rows) on {date.today()}. Record this date in the README.")
