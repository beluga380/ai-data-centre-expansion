"""
Tab 2 - Builders and Locations: every transformation applied to the Epoch AI file.

Source file : data/raw/data_centers.csv  (downloaded unedited from
              https://epoch.ai/data/data_centers/data_centers.csv)
Licence     : CC BY, Epoch AI, 'AI data centers', epoch.ai

The raw file has one row per AI data centre site. This module does only four things,
so any number on the page can be traced back in two steps:

  1. load()            read the CSV and keep the columns the tab uses
  2. clean()           strip Epoch's confidence tags (#confident / #likely /
                       #speculative) from Owner, and fill blank owners
  3. share_table()     group by Owner or Country and sum power (MW)
  4. top_n_share()     add up the largest N groups as a % of the total

Nothing else is changed: no rows are dropped, no values are imputed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
from urllib.request import urlretrieve

RAW_URL = "https://epoch.ai/data/data_centers/data_centers.csv"
RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "data_centers.csv"

# Column names exactly as they appear in the Epoch header row.
COL_NAME = "Name"
COL_OWNER = "Owner"
COL_COUNTRY = "Country"
COL_POWER = "Current power (MW)"  # latest IT power, MW (Epoch looks this up from Timelines)
COL_COST = "Current total capital cost (2025 USD billions)"

UNATTRIBUTED = "Owner not disclosed"
TAG_PATTERN = re.compile(r"\s*#(confident|likely|speculative)\b", flags=re.IGNORECASE)


def load(path: str | Path = RAW_PATH) -> pd.DataFrame:
    """Step 1: read the raw Epoch file. If it is missing, download it once and save it
    to data/raw/ unedited, so the repository always holds the exact file used."""
    path = Path(os.environ.get("TAB2_DATA_PATH", path))  # override used only by tests
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(RAW_URL, path)  # byte-for-byte copy of Epoch's file
    df = pd.read_csv(path)
    return df[[COL_NAME, COL_OWNER, COL_COUNTRY, COL_POWER, COL_COST]].copy()


def clean_owner(value) -> str:
    """'Meta #confident' -> 'Meta'.  Blank -> 'Owner not disclosed'."""
    if pd.isna(value) or str(value).strip() == "":
        return UNATTRIBUTED
    return TAG_PATTERN.sub("", str(value)).strip()


def owner_confidence(value) -> str:
    """Keep Epoch's tag in its own column so the page can disclose it."""
    if pd.isna(value):
        return "none"
    match = TAG_PATTERN.search(str(value))
    return match.group(1).lower() if match else "untagged"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Step 2: tidy text fields and flag sites that are not yet drawing power."""
    out = df.copy()
    out["owner_confidence"] = out[COL_OWNER].map(owner_confidence)
    out[COL_OWNER] = out[COL_OWNER].map(clean_owner)
    out[COL_POWER] = pd.to_numeric(out[COL_POWER], errors="coerce").fillna(0)
    out[COL_COST] = pd.to_numeric(out[COL_COST], errors="coerce").fillna(0)
    out["operational"] = out[COL_POWER] > 0  # Epoch records 0 MW for sites not yet running
    return out


def share_table(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Step 3: total current power and site count per Owner or Country, largest first.
    share_pct = group MW / all MW * 100."""
    table = (
        df.groupby(by, as_index=False)
        .agg(power_mw=(COL_POWER, "sum"), sites=(COL_NAME, "count"))
        .sort_values("power_mw", ascending=False, ignore_index=True)
    )
    table["share_pct"] = table["power_mw"] / table["power_mw"].sum() * 100
    table["cumulative_pct"] = table["share_pct"].cumsum()
    return table


def top_n_share(table: pd.DataFrame, n: int, by: str) -> float:
    """Step 4: % of all current power held by the n largest groups.
    'Owner not disclosed' is not a single organisation, so it never counts toward the top n."""
    named = table[table[by] != UNATTRIBUTED]
    return named.head(n)["power_mw"].sum() / table["power_mw"].sum() * 100

