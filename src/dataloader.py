"""
dataloader.py — Fetch historical crypto OHLCV data from the Binance public data dump.

No API key required. Data comes from https://data.binance.vision (monthly zipped
klines). Supports daily ("1d") and hourly ("1h") bars, full listing history.

Usage
-----
    from src.dataloader import fetch_symbol, load_cached

    btc = fetch_symbol("BTCUSDT", interval="1d", start="2017-08", end="2026-09")
    btc = load_cached("BTCUSDT", interval="1d")   # read from data/ if already saved
"""

from __future__ import annotations

import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]

# Coins tracked in this project. USDC/USDT is included as a near-zero-volatility
# contrast asset (and its depeg episodes are pedagogically interesting for GARCH).
COINS = {
    "BTCUSDT":  "Bitcoin",
    "ETHUSDT":  "Ethereum",
    "SOLUSDT":  "Solana",
    "DOGEUSDT": "Dogecoin",
    "USDCUSDT": "USD Coin (stablecoin contrast)",
}

# First month each pair is available on Binance spot.
LISTING_MONTH = {
    "BTCUSDT": "2017-08", "ETHUSDT": "2017-08", "SOLUSDT": "2020-08",
    "DOGEUSDT": "2019-07", "USDCUSDT": "2018-11",
}


def _month_range(start: str, end: str) -> list[str]:
    """Inclusive list of 'YYYY-MM' strings between start and end."""
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _fetch_month(symbol: str, interval: str, ym: str, retries: int = 3) -> pd.DataFrame | None:
    """Download one monthly kline zip; return a tidy DataFrame or None."""
    url = (f"https://data.binance.vision/data/spot/monthly/klines/"
           f"{symbol}/{interval}/{symbol}-{interval}-{ym}.zip")
    for _ in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                return None  # pair did not exist yet / month not published
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(z.namelist()[0]) as f:
                    df = pd.read_csv(f, header=None, names=KLINE_COLS, dtype=str)
            df = df[df["open_time"] != "open_time"]  # some files carry a header row
            df["open_time"] = pd.to_numeric(df["open_time"])
            unit = "ms" if df["open_time"].iloc[0] < 1e13 else "us"
            df["timestamp"] = pd.to_datetime(df["open_time"], unit=unit)
            for c in ["open", "high", "low", "close", "volume", "quote_volume"]:
                df[c] = df[c].astype(float)
            return df[["timestamp", "open", "high", "low", "close", "volume"]]
        except Exception:
            time.sleep(1.0)
    return None


def fetch_symbol(symbol: str, interval: str = "1d",
                 start: str | None = None, end: str | None = None,
                 save: bool = True) -> pd.DataFrame:
    """
    Fetch full OHLCV history for one Binance spot pair.

    Parameters
    ----------
    symbol   : e.g. "BTCUSDT"
    interval : "1d" or "1h"
    start    : first month "YYYY-MM" (defaults to the pair's listing month)
    end      : last month "YYYY-MM" (defaults to the last *completed* month)
    save     : write the result to data/{daily|hourly}/{symbol}_{interval}.csv

    Returns
    -------
    DataFrame indexed by timestamp with OHLCV columns plus `log_return`
    (first difference of log close prices — the series we will model).
    """
    if start is None:
        start = LISTING_MONTH.get(symbol, "2017-08")
    if end is None:
        end = pd.Timestamp.now().to_period("M").__sub__(1).strftime("%Y-%m")

    months = _month_range(start, end)
    with ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(lambda ym: _fetch_month(symbol, interval, ym), months))
    parts = [p for p in parts if p is not None]
    if not parts:
        raise ValueError(f"No data returned for {symbol} {interval} {start}..{end}")

    df = (pd.concat(parts)
            .drop_duplicates("timestamp")
            .sort_values("timestamp")
            .reset_index(drop=True))
    df["log_return"] = np.log(df["close"]).diff()

    if save:
        sub = {"1d": "daily", "1h": "hourly"}.get(interval, "daily")
        out = DATA_ROOT / sub / f"{symbol}_{interval}.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
    return df


def load_cached(symbol: str, interval: str = "1d") -> pd.DataFrame:
    """Load a previously saved CSV from data/, fetching it first if missing."""
    sub = {"1d": "daily", "1h": "hourly"}.get(interval, "daily")
    path = DATA_ROOT / sub / f"{symbol}_{interval}.csv"
    if not path.exists():
        return fetch_symbol(symbol, interval=interval)
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def load_all(interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Load every coin in COINS as {symbol: DataFrame}."""
    return {sym: load_cached(sym, interval=interval) for sym in COINS}


if __name__ == "__main__":
    for sym in COINS:
        d = load_cached(sym, "1d")
        print(f"{sym:9s}  {len(d):5d} rows   {d.timestamp.min().date()} -> {d.timestamp.max().date()}")
