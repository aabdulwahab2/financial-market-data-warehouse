"""
extract_yfinance.py
-------------------
Extracts daily OHLCV price data for all tickers via yfinance.
Outputs a long-format CSV to data/raw/prices_raw.csv.

Design decisions:
- Long format (one row per ticker per date) for star schema compatibility
- Uses auto_adjust=True for split/dividend adjusted prices
- Incremental: only fetches dates not already in the raw file
- Batch download (all tickers at once) for speed
"""

import sys
from pathlib import Path

# Allow running this file directly (python etl/extract/extract_yfinance.py)
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import logging

from src.config import TICKER_THEMES, TICKER_LIST, DATA_RAW, START_DATE, END_DATE

logger = logging.getLogger(__name__)

RAW_PATH = DATA_RAW / "prices_raw.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_fetch_range(start: str, end: str) -> tuple[str, str]:
    """
    If a raw file already exists, only fetch dates after the last
    date we already have (incremental load). Otherwise fetch full range.
    """
    if RAW_PATH.exists():
        existing = pd.read_csv(RAW_PATH, usecols=["date"], parse_dates=["date"])
        last_date = existing["date"].max().date()
        fetch_start = str(last_date + timedelta(days=1))
        logger.info(f"Incremental mode: fetching from {fetch_start} (last stored: {last_date})")
        return fetch_start, end
    logger.info(f"Full load: fetching {start} -> {end}")
    return start, end


def _download(tickers: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download OHLCV data for all tickers in a single batch call.
    Returns a long-format DataFrame.
    """
    raw = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        df = raw.stack(level=1, future_stack=True).reset_index()
        df.columns.name = None
        df = df.rename(columns={"level_1": "ticker", "Date": "date"})
    else:
        df = raw.reset_index()
        df["ticker"] = tickers[0]
        df = df.rename(columns={"Date": "date"})

    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names, add theme, drop nulls.
    """
    if df.empty:
        return df

    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

    if "close" in df.columns:
        df = df.rename(columns={"close": "adj_close"})

    df["theme"] = df["ticker"].map(TICKER_THEMES)
    df["date"]  = pd.to_datetime(df["date"]).dt.date

    df = df.dropna(subset=["adj_close"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    keep_cols = ["date", "ticker", "theme", "open", "high", "low", "adj_close", "volume"]
    return df[[c for c in keep_cols if c in df.columns]]


def _save(df: pd.DataFrame) -> None:
    """
    Append to existing raw file or create new one.
    """
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)

    if RAW_PATH.exists() and not df.empty:
        df.to_csv(RAW_PATH, mode="a", header=False, index=False)
        logger.info(f"Appended {len(df):,} rows to {RAW_PATH}")
    else:
        df.to_csv(RAW_PATH, index=False)
        logger.info(f"Wrote {len(df):,} rows to {RAW_PATH}")


# ── Public entry point ────────────────────────────────────────────────────────

def run(
    tickers: list[str] | None = None,
    start: str = START_DATE,
    end: str = END_DATE,
) -> pd.DataFrame:
    """
    Main extraction function. Called by run_pipeline.py.
    Returns the extracted DataFrame (also saved to disk).
    """
    tickers = tickers or TICKER_LIST
    fetch_start, fetch_end = _get_fetch_range(start, end)

    logger.info(f"Extracting {len(tickers)} tickers: {fetch_start} -> {fetch_end}")

    raw_df = _download(tickers, fetch_start, fetch_end)

    if raw_df.empty:
        logger.info("No new data returned (already up to date or market closed range).")
        return raw_df

    clean_df = _clean(raw_df)

    if clean_df.empty:
        logger.info("No new data to save after cleaning.")
        return clean_df

    _save(clean_df)
    return clean_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    df = run()
    if not df.empty:
        print(df.head(10).to_string())
        print(f"\nShape: {df.shape}")
        print(f"Date range: {df['date'].min()} -> {df['date'].max()}")
        print(f"Tickers: {sorted(df['ticker'].unique())}")
    else:
        print("No data extracted.")