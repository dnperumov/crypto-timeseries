# crypto-timeseries

A library of foundational time-series models — **ARMA/ARIMA, GARCH, VAR** — built, explained,
and benchmarked on real cryptocurrency data.

Course project roadmap:

1. **Phase 1 — Setup & data** (done): repo scaffold + data pipeline pulling full-history
   daily and 2-year hourly OHLCV for BTC, ETH, SOL, DOGE, and USDC (stablecoin contrast)
   from the Binance public data dump. Log returns computed and cached as CSV.
2. **Phase 2 — Model library**: clean, documented `fit / forecast / simulate` classes in `models/`.
3. **Phase 3 — Tutorial**: graduate-level notebooks covering intuition, math, and use cases.
4. **Phase 4 — Demo app**: run models on the data, compare forecasts, confidence intervals,
   volatility dynamics, and impulse responses; out-of-sample backtest vs. buy-and-hold.

## Layout

```
models/      model implementations (Phase 2)
src/         dataloader.py — data-fetching / caching module
data/        cached CSVs (daily full history, hourly last 2 years)
notebooks/   tutorials + exploration (01_data_exploration.ipynb)
demo/        demo application (Phase 4)
```

## Quick start

```bash
pip install -r requirements.txt
python src/dataloader.py          # fetch / verify cached data
jupyter lab notebooks/01_data_exploration.ipynb
```

## Data

Source: [Binance public data dump](https://data.binance.vision) — no API key required.
Monthly zipped klines are downloaded in parallel, tidied, deduplicated, and cached.
CSVs are gitignored (bulk data doesn't belong in git); `python src/dataloader.py`
refreshes the full dataset locally in about a minute.

| Pair     | Role                | Daily coverage        | Hourly coverage       |
|----------|---------------------|-----------------------|-----------------------|
| BTCUSDT  | market benchmark    | 2017-08 → present     | last 2 years          |
| ETHUSDT  | #2 asset (for VAR)  | 2017-08 → present     | last 2 years          |
| SOLUSDT  | high-beta altcoin   | 2020-08 → present     | last 2 years          |
| DOGEUSDT | meme / fat tails    | 2019-07 → present     | last 2 years          |
| USDCUSDT | stablecoin contrast | 2018-12 → present     | last 2 years          |
