"""
config.py
---------
Central configuration for the Financial Market Data Warehouse.
All tickers, paths, dates, and settings live here.
No other file should hardcode these values.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# ── Project root ──────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent

# ── Data paths ────────────────────────────────────────────────────────────────

DATA_RAW       = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXPORTS   = ROOT / "data" / "exports"
DATABASE_PATH  = ROOT / "database" / "market_data.db"

# ── Date range ────────────────────────────────────────────────────────────────

START_DATE = "2019-01-01"
END_DATE   = "2025-12-31"

# ── Tickers ───────────────────────────────────────────────────────────────────

TICKER_THEMES = {
    "SPY":  "broad_market",
    "QQQ":  "broad_market",
    "DIA":  "broad_market",
    "IWM":  "broad_market",
    "NVDA": "ai_infrastructure",
    "AVGO": "ai_infrastructure",
    "MRVL": "ai_infrastructure",
    "COHR": "ai_infrastructure",
    "LITE": "ai_infrastructure",
    "FN":   "ai_infrastructure",
    "AAPL": "large_cap_tech",
    "MSFT": "large_cap_tech",
    "JPM":  "financials",
    "GS":   "financials",
    "V":    "financials",
    "MA":   "financials",
}

TICKER_LIST = list(TICKER_THEMES.keys())

# ── FRED macro series ─────────────────────────────────────────────────────────

FRED_SERIES = {
    "FEDFUNDS": "fed_funds_rate",
    "CPIAUCSL": "cpi",
    "UNRATE":   "unemployment_rate",
    "GS10":     "treasury_10y",
    "GS2":      "treasury_2y",
    "VIXCLS":   "vix",
    "GDP":      "gdp",
}

# ── API keys ──────────────────────────────────────────────────────────────────

FRED_API_KEY = os.getenv("FRED_API_KEY", "")