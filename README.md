# VWAP / EMA(8) Stock Screener

A Streamlit app that screens a watchlist of large-cap US stocks on **1-minute
intraday bars** and flags whether price is trading **above** or **below**
both the **VWAP** and the **EMA(8)** — with TradingView-style candlestick
charts (Plotly) for each stock.

## ⚠️ Important note on data source

You asked to pull data "using Nasdaq.com" — but Nasdaq.com does not expose a
public API for intraday OHLCV bars, so there's no reliable way to fetch
1-minute candles from it directly. This app instead uses **Yahoo Finance**
(via the `yfinance` library), which is free, requires no API key, and is the
standard approach for this kind of screener. The tickers and logic are
otherwise exactly what you asked for.

## What it does

- Fetches 1-minute (or 5m/15m) intraday bars for all 30 watchlist stocks.
- Computes:
  - **VWAP** — volume-weighted average price, reset at the start of each
    trading day.
  - **EMA(8)** — 8-period exponential moving average of the close.
- Flags each stock as:
  - **Above Both (Bullish)** — last price > VWAP and > EMA(8)
  - **Below Both (Bearish)** — last price < VWAP and < EMA(8)
  - **Mixed** — anything else
- Lets you filter the table by condition.
- Shows an interactive candlestick chart (with VWAP + EMA8 overlays) for
  any selected stock, similar in style to TradingView.

## Files

```
stock_screener/
├── app.py              # main Streamlit app
├── requirements.txt     # Python dependencies
└── README.md
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Deploy on GitHub + Streamlit Community Cloud

1. Create a new GitHub repo and push these files to it:
   ```bash
   git init
   git add app.py requirements.txt README.md
   git commit -m "Initial commit: VWAP/EMA8 screener"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. Go to **https://share.streamlit.io** (Streamlit Community Cloud) and sign
   in with GitHub.
3. Click **"New app"**, select your repo/branch, and set the main file path
   to `app.py`.
4. Click **Deploy**. Streamlit Cloud will read `requirements.txt`
   automatically and install dependencies.

That's it — no API keys or secrets are needed.

## Notes & limitations

- **Market hours**: 1-minute bars only populate while US markets are open
  (9:30 AM–4:00 PM Eastern, Mon–Fri). Outside those hours you'll see the
  last completed session's bars, or "No Data" for illiquid symbols.
- **Lookback limit**: Yahoo Finance only serves 1-minute data for the last
  ~7 calendar days. Use the "5d" lookback in the sidebar if "1d" looks thin
  right after the open.
- **Caching**: Data is cached for 60 seconds (`st.cache_data(ttl=60)`) to
  avoid hammering Yahoo Finance on every rerun. Use the "🔄 Refresh Data"
  button to force a fresh pull.
- **Rate limiting**: Yahoo Finance may occasionally throttle requests when
  scanning 30 tickers back to back. If you see intermittent "No Data" /
  "Error" rows, just click Refresh again after a few seconds.
- To change the watchlist, edit the `STOCKS` dictionary at the top of
  `app.py`.
