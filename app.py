"""
Stock Screener — Price vs VWAP & EMA8 (1-Minute Chart)
--------------------------------------------------------
Screens a fixed watchlist of large-cap US stocks and flags whether the
latest 1-minute price is:
  - ABOVE both VWAP and EMA(8)   -> bullish
  - BELOW both VWAP and EMA(8)   -> bearish
  - Mixed / no clear signal otherwise

Data source: Yahoo Finance intraday bars (via yfinance).
NOTE: Nasdaq.com does not provide a public API for intraday OHLCV data,
so this app uses Yahoo Finance, which is free, reliable, and has no
key/auth requirements — ideal for GitHub + Streamlit Cloud deployment.

Run locally:
    streamlit run app.py

Deploy:
    Push this repo to GitHub, then deploy on https://share.streamlit.io
    pointing at app.py. Add requirements.txt (included) to the repo root.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="VWAP / EMA8 Screener", layout="wide")

# ----------------------------------------------------------------------
# Watchlist
# ----------------------------------------------------------------------
STOCKS = {
    "Nvidia": "NVDA",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Alphabet (A)": "GOOGL",
    "Alphabet (C)": "GOOG",
    "Broadcom": "AVGO",
    "Meta Platforms": "META",
    "Tesla": "TSLA",
    "Berkshire Hathaway": "BRK-B",
    "Eli Lilly": "LLY",
    "Walmart": "WMT",
    "JPMorgan Chase": "JPM",
    "Exxon Mobil": "XOM",
    "Visa": "V",
    "Johnson & Johnson": "JNJ",
    "AMD": "AMD",
    "Intel": "INTC",
    "Oracle": "ORCL",
    "Costco": "COST",
    "Procter & Gamble": "PG",
    "Home Depot": "HD",
    "Mastercard": "MA",
    "AbbVie": "ABBV",
    "Chevron": "CVX",
    "Coca-Cola": "KO",
    "PepsiCo": "PEP",
    "Merck": "MRK",
    "Adobe": "ADBE",
    "Cisco": "CSCO",
}

EMA_LEN = 8


# ----------------------------------------------------------------------
# Data helpers
# ----------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Download intraday OHLCV bars for a single ticker."""
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        return df

    # yfinance sometimes returns MultiIndex columns (single ticker download)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add VWAP (reset each trading day) and EMA(8) columns."""
    df = df.copy()
    df["date"] = df.index.date

    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    df["tp_vol"] = typical_price * df["Volume"]
    df["cum_tp_vol"] = df.groupby("date")["tp_vol"].cumsum()
    df["cum_vol"] = df.groupby("date")["Volume"].cumsum()
    df["VWAP"] = df["cum_tp_vol"] / df["cum_vol"]

    df["EMA8"] = df["Close"].ewm(span=EMA_LEN, adjust=False).mean()
    return df


def get_condition(df: pd.DataFrame) -> str:
    if df.empty:
        return "No Data"
    last = df.iloc[-1]
    price, vwap, ema8 = last["Close"], last["VWAP"], last["EMA8"]
    if pd.isna(vwap) or pd.isna(ema8):
        return "No Data"
    if price > vwap and price > ema8:
        return "Above Both (Bullish)"
    if price < vwap and price < ema8:
        return "Below Both (Bearish)"
    return "Mixed"


def get_strength(df: pd.DataFrame, condition: str) -> str:
    """
    Classify Bullish/Bearish signals as "Strong" when the trend is aligned:
      - Strong Bullish: price > EMA8 > VWAP  (short-term trend also above VWAP)
      - Strong Bearish: price < EMA8 < VWAP  (short-term trend also below VWAP)
    Anything else (including Mixed/No Data) is left blank.
    """
    if df.empty or condition not in ("Above Both (Bullish)", "Below Both (Bearish)"):
        return ""
    last = df.iloc[-1]
    vwap, ema8 = last["VWAP"], last["EMA8"]
    if pd.isna(vwap) or pd.isna(ema8):
        return ""
    if condition == "Above Both (Bullish)" and ema8 > vwap:
        return "Strong Bullish"
    if condition == "Below Both (Bearish)" and ema8 < vwap:
        return "Strong Bearish"
    return ""


def plot_chart(df: pd.DataFrame, name: str, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["VWAP"], mode="lines",
            name="VWAP", line=dict(color="#ff9800", width=1.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["EMA8"], mode="lines",
            name="EMA(8)", line=dict(color="#2196f3", width=1.5),
        )
    )
    fig.update_layout(
        title=f"{name} ({ticker}) — 1 Minute Chart",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"]),          # hide weekends
            dict(bounds=[20, 9.5], pattern="hour"),  # hide non-market hours (approx, US/Eastern)
        ]
    )
    return fig


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.title("📊 Stock Screener — Price vs VWAP & EMA(8)")
st.caption(
    "Data: Yahoo Finance 1-minute intraday bars. "
    "Bullish = price above both VWAP and EMA(8). Bearish = price below both."
)

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("Lookback period", ["1d", "5d"], index=0)
    interval = st.selectbox("Interval", ["1m", "5m", "15m"], index=0)
    filter_choice = st.radio(
        "Filter",
        ["All", "Above Both (Bullish)", "Below Both (Bearish)", "Mixed", "No Data"],
    )

    st.divider()
    st.subheader("Auto-Refresh")
    autorefresh_choice = st.selectbox(
        "Refresh every",
        ["Off", "1 min", "2 min", "3 min", "4 min", "5 min"],
        index=0,
        help="Automatically re-fetches data and reruns the app at this interval.",
    )

    if st.button("🔄 Refresh Data Now"):
        st.cache_data.clear()
        st.rerun()

    st.caption(
        "⚠️ 1-minute bars are only available for the last ~7 trading days "
        "and only populate while US markets are open."
    )

# Map the selection to milliseconds and trigger the autorefresh timer.
_AUTOREFRESH_MS = {
    "Off": None,
    "1 min": 1 * 60 * 1000,
    "2 min": 2 * 60 * 1000,
    "3 min": 3 * 60 * 1000,
    "4 min": 4 * 60 * 1000,
    "5 min": 5 * 60 * 1000,
}
_interval_ms = _AUTOREFRESH_MS[autorefresh_choice]
if _interval_ms is not None:
    # st_autorefresh triggers a full app rerun every `interval_ms` ms.
    # The counter it returns is unused but kept so Streamlit tracks the component state.
    _refresh_count = st_autorefresh(interval=_interval_ms, key="data_autorefresh")
    st.sidebar.caption(f"Auto-refresh ON — every {autorefresh_choice} (tick #{_refresh_count})")
else:
    st.sidebar.caption("Auto-refresh is OFF")

results = []
data_cache: dict[str, pd.DataFrame] = {}

progress = st.progress(0, text="Fetching data...")
items = list(STOCKS.items())
for i, (name, ticker) in enumerate(items):
    try:
        raw = fetch_data(ticker, period=period, interval=interval)
        if raw.empty:
            results.append(
                {"Company": name, "Ticker": ticker, "Price": None,
                 "VWAP": None, "EMA8": None, "Condition": "No Data", "Strength": ""}
            )
        else:
            df = compute_indicators(raw)
            data_cache[ticker] = df
            last = df.iloc[-1]
            condition = get_condition(df)
            results.append(
                {
                    "Company": name,
                    "Ticker": ticker,
                    "Price": round(float(last["Close"]), 2),
                    "VWAP": round(float(last["VWAP"]), 2) if pd.notna(last["VWAP"]) else None,
                    "EMA8": round(float(last["EMA8"]), 2) if pd.notna(last["EMA8"]) else None,
                    "Condition": condition,
                    "Strength": get_strength(df, condition),
                }
            )
    except Exception:
        results.append(
            {"Company": name, "Ticker": ticker, "Price": None,
             "VWAP": None, "EMA8": None, "Condition": "Error", "Strength": ""}
        )
    progress.progress((i + 1) / len(items), text=f"Fetching {ticker}...")

progress.empty()

df_results = pd.DataFrame(results)
df_display = (
    df_results if filter_choice == "All"
    else df_results[df_results["Condition"] == filter_choice]
)


def _color_condition(val):
    return {
        "Above Both (Bullish)": "background-color:#1b5e20;color:white",
        "Below Both (Bearish)": "background-color:#b71c1c;color:white",
        "Mixed": "background-color:#444;color:white",
    }.get(val, "")


st.subheader(f"Screener Results ({len(df_display)} stocks)")
st.dataframe(
    df_display.style.map(_color_condition, subset=["Condition"]),
    width='stretch',
    hide_index=True,
)

st.divider()

# ------------------------------------------------------------------
# Strong Bullish / Strong Bearish table
#   Strong Bullish: price > EMA8 > VWAP (trend aligned above VWAP)
#   Strong Bearish: price < EMA8 < VWAP (trend aligned below VWAP)
#   Mixed / No Data / Error rows are excluded entirely.
# ------------------------------------------------------------------
df_strong = df_results[df_results["Strength"].isin(["Strong Bullish", "Strong Bearish"])].copy()
df_strong = df_strong.drop(columns=["Condition"]).rename(columns={"Strength": "Signal"})


def _color_strength(val):
    return {
        "Strong Bullish": "background-color:#1b5e20;color:white;font-weight:bold",
        "Strong Bearish": "background-color:#b71c1c;color:white;font-weight:bold",
    }.get(val, "")


st.subheader(f"🚀 Strong Bullish / Strong Bearish ({len(df_strong)} stocks)")
st.caption(
    "Strong Bullish = price > EMA(8) > VWAP. Strong Bearish = price < EMA(8) < VWAP. "
    "Mixed signals are excluded from this table."
)
if df_strong.empty:
    st.info("No stocks currently meet the Strong Bullish / Strong Bearish criteria.")
else:
    st.dataframe(
        df_strong.sort_values("Signal").style.map(_color_strength, subset=["Signal"]),
        width='stretch',
        hide_index=True,
    )

st.divider()
st.subheader(f"📈 Charts ({len(df_display)} stocks)")
st.caption("Showing charts for every stock in the filtered list above. "
           "Click a section to expand/collapse it.")

for _, row in df_display.iterrows():
    name, ticker, condition = row["Company"], row["Ticker"], row["Condition"]
    badge = {
        "Above Both (Bullish)": "🟢",
        "Below Both (Bearish)": "🔴",
        "Mixed": "🟡",
    }.get(condition, "⚪")

    with st.expander(f"{badge} {name} ({ticker}) — {condition}", expanded=True):
        if ticker in data_cache:
            st.plotly_chart(
                plot_chart(data_cache[ticker], name, ticker),
                width="stretch",
                key=f"chart_{ticker}",
            )
        else:
            st.warning("No intraday data available for this stock right now "
                       "(market may be closed, or data hasn't populated yet).")
