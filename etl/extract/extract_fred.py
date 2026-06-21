"""
extract_fred.py
----------------
Extracts macroeconomic time series data from FRED (Federal Reserve
Economic Data) via the fredapi library.
Outputs a long-format CSV to data/raw/macro_raw.csv.

Design decisions:
- Each series keeps its NATIVE reporting frequency (no forced alignment here).
  Frequency harmonization happens in the transform layer, not extraction.
- Long format: one row per (date, series) for star schema compatibility.
- Full reload each run -- macro data is small (a few thousand rows total)
  and FRED occasionally revises historical values, so incremental loading
  would risk missing revisions. This is a deliberate contrast to the
  incremental yfinance extractor.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
from fredapi import Fred
import logging

from src.config import FRED_SERIES, FRED_API_KEY, DATA_RAW, START_DATE, END_DATE

logger = logging.getLogger(__name__)

RAW_PATH = DATA_RAW / "macro_raw.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_series(fred: Fred, series_id: str, series_name: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch a single FRED series and return it in long format.
    """
    try:
        data = fred.get_series(series_id, observation_start=start, observation_end=end)
    except Exception as e:
        logger.error(f"Failed to fetch {series_id}: {e}")
        return pd.DataFrame()

    if data is None or data.empty:
        logger.warning(f"No data returned for {series_id}")
        return pd.DataFrame()

    df = data.reset_index()
    df.columns = ["date", "value"]
    df["series_id"]   = series_id
    df["series_name"] = series_name
    df = df.dropna(subset=["value"])
    df["date"] = pd.to_datetime(df["date"]).dt.date

    logger.info(f"  {series_id} ({series_name}): {len(df)} observations")
    return df[["date", "series_id", "series_name", "value"]]


def _save(df: pd.DataFrame) -> None:
    """
    Full overwrite -- macro data is small and FRED revises history,
    so we always pull the complete, current series.
    """
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_PATH, index=False)
    logger.info(f"Wrote {len(df):,} rows to {RAW_PATH}")


# ── Public entry point ────────────────────────────────────────────────────────

def run(
    series: dict[str, str] | None = None,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame:
    """
    Main extraction function. Pulls all configured FRED series.
    """
    if not FRED_API_KEY:
        raise ValueError(
            "FRED_API_KEY is empty. Check that .env exists and contains "
            "a valid key, and that src/config.py loaded it correctly."
        )

    series = series or FRED_SERIES
    fred = Fred(api_key=FRED_API_KEY)

    logger.info(f"Extracting {len(series)} FRED series: {start} -> {end}")

    frames = []
    for series_id, series_name in series.items():
        df = _fetch_series(fred, series_id, series_name, start, end)
        if not df.empty:
            frames.append(df)

    if not frames:
        logger.warning("No FRED data extracted at all.")
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["series_id", "date"]).reset_index(drop=True)

    _save(combined)
    return combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    df = run()
    if not df.empty:
        print(df.head(10).to_string())
        print(f"\nShape: {df.shape}")
        print("\nRows per series:")
        print(df.groupby("series_name").size().to_string())
    else:
        print("No data extracted.")