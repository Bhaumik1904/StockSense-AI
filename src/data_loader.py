"""
data_loader.py
--------------
Module to fetch real-time and historical stock data using yfinance.
Provides helper functions for the rest of the application.

Fix: Applies SSL workaround for Windows environments and uses yf.download()
which is more reliable across yfinance versions.
"""

import ssl
import warnings
import yfinance as yf
import pandas as pd
from textblob import TextBlob

# ── SSL Fix (Windows / corporate firewall workaround) ──────────────────────
# Some Windows environments block Yahoo Finance's SSL handshake.
# This disables certificate verification for yfinance requests only.
try:
    _default_ctx = ssl.create_default_context()
    _default_ctx.check_hostname = False
    _default_ctx.verify_mode = ssl.CERT_NONE
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

warnings.filterwarnings("ignore")


def fetch_historical_data(ticker: str, period: str = "6mo") -> dict:
    """
    Fetch historical OHLCV data for a given stock ticker.

    Uses yf.download() which is more reliable than Ticker.history()
    across different yfinance versions (0.2.x and 1.x).

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        period: Period string ('1mo', '3mo', '6mo', '1y', '2y', '5y')

    Returns:
        Dictionary with dates and OHLCV data lists, or error details.
    """
    try:
        ticker = ticker.upper()

        # yf.download is the most stable cross-version API
        df = yf.download(
            ticker,
            period=period,
            progress=False,
            auto_adjust=True,   # Adjusts for splits & dividends
            threads=False,
        )

        if df is None or df.empty:
            return {"error": f"No data found for ticker '{ticker}'. Please verify the symbol (e.g. AAPL, TSLA, MSFT)."}

        # Flatten MultiIndex columns if present (yfinance 1.x returns MultiIndex)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Ensure required columns exist
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(set(df.columns)):
            return {"error": f"Incomplete data received for '{ticker}'. Missing columns: {required - set(df.columns)}"}

        # Reset index so Date becomes a column
        df = df.reset_index()

        # Normalize Date column (handles both DatetimeIndex and Timestamp)
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df["Date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")

        # Drop any rows with NaN close prices
        df = df.dropna(subset=["Close"])

        if len(df) < 5:
            return {"error": f"Not enough trading data for '{ticker}' in the selected period."}

        return {
            "ticker": ticker,
            "period": period,
            "dates":  df["Date"].tolist(),
            "open":   [round(float(v), 4) for v in df["Open"].tolist()],
            "high":   [round(float(v), 4) for v in df["High"].tolist()],
            "low":    [round(float(v), 4) for v in df["Low"].tolist()],
            "close":  [round(float(v), 4) for v in df["Close"].tolist()],
            "volume": [int(v) for v in df["Volume"].tolist()],
            "latest_open":   round(float(df["Open"].iloc[-1]),   4),
            "latest_close":  round(float(df["Close"].iloc[-1]),  4),
            "latest_high":   round(float(df["High"].iloc[-1]),   4),
            "latest_low":    round(float(df["Low"].iloc[-1]),    4),
            "latest_volume": int(df["Volume"].iloc[-1]),
            "latest_date":   df["Date"].iloc[-1],
            "error": None
        }

    except Exception as e:
        return {"error": f"Failed to fetch data for '{ticker}': {str(e)}"}


def fetch_stock_info(ticker: str) -> dict:
    """
    Fetch basic metadata for a given stock ticker.
    Falls back gracefully if info is unavailable.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info or {}
        return {
            "symbol":      ticker.upper(),
            "name":        info.get("longName", ticker.upper()),
            "sector":      info.get("sector", "N/A"),
            "industry":    info.get("industry", "N/A"),
            "market_cap":  info.get("marketCap", 0),
            "currency":    info.get("currency", "USD"),
            "exchange":    info.get("exchange", "N/A"),
            "website":     info.get("website", ""),
            "description": info.get("longBusinessSummary", ""),
            "current_price":    info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "52_week_high":     info.get("fiftyTwoWeekHigh", 0),
            "52_week_low":      info.get("fiftyTwoWeekLow", 0),
            "pe_ratio":         info.get("trailingPE", 0),
            "dividend_yield":   info.get("dividendYield", 0),
            "error": None
        }
    except Exception as e:
        return {"symbol": ticker.upper(), "name": ticker.upper(), "error": str(e)}


def get_multiple_quotes(tickers: list) -> list:
    """
    Fetch latest quotes for a list of tickers (watchlist).
    Uses yf.download for batch efficiency.
    """
    results = []
    for ticker in tickers:
        try:
            df = yf.download(
                ticker.upper(),
                period="5d",
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]

            if df is not None and not df.empty and "Close" in df.columns:
                closes = df["Close"].dropna()
                if len(closes) >= 2:
                    latest   = round(float(closes.iloc[-1]), 4)
                    previous = round(float(closes.iloc[-2]), 4)
                    change   = round(latest - previous, 4)
                    change_pct = round((change / previous) * 100, 2) if previous != 0 else 0
                    results.append({
                "symbol": ticker.upper(),
                "price": latest,
                "change": change,
                "change_pct": change_pct,
                "trend": "up" if change >= 0 else "down"
            })
            continue
        except Exception:
            pass
        results.append({
            "symbol": ticker.upper(),
            "price": 0, "change": 0, "change_pct": 0, "trend": "neutral"
        })
    return results

import time
_TRENDING_CACHE = {"time": 0, "tickers": []}

def get_trending_indian_stocks(limit: int = 7) -> list:
    """
    Find the top trending Indian stocks (Top Gainers) for the day.
    Caches the results for 1 hour to ensure the dashboard loads instantly.
    """
    global _TRENDING_CACHE
    now = time.time()
    if now - _TRENDING_CACHE["time"] < 3600 and _TRENDING_CACHE["tickers"]:
        return _TRENDING_CACHE["tickers"][:limit]
        
    from src.tickers import INDIAN_STOCKS
    symbols = [item["symbol"] for item in INDIAN_STOCKS]
    
    try:
        df = yf.download(symbols, period="5d", interval="1d", group_by="ticker", threads=True, progress=False)
        gainers = []
        for symbol in symbols:
            if isinstance(df.columns, pd.MultiIndex):
                if symbol in df.columns.levels[0]:
                    sub_df = df[symbol].dropna()
                    if len(sub_df) >= 2:
                        closes = sub_df['Close']
                        latest = float(closes.iloc[-1])
                        prev = float(closes.iloc[-2])
                        if prev > 0:
                            pct = (latest - prev) / prev * 100
                            gainers.append((symbol, pct))
        
        gainers.sort(key=lambda x: x[1], reverse=True)
        top_symbols = [g[0] for g in gainers]
        
        if top_symbols:
            _TRENDING_CACHE["time"] = now
            _TRENDING_CACHE["tickers"] = top_symbols
            return top_symbols[:limit]
    except Exception as e:
        print(f"Error fetching trending: {e}")
        
    # Fallback to defaults
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS"][:limit]


def fetch_news_and_sentiment(ticker: str) -> dict:
    """
    Fetch the top 5 recent news articles for a stock and calculate sentiment
    using TextBlob on their titles.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        news_items = stock.news
        if not news_items:
            return {"articles": [], "overall_sentiment": "Neutral", "score": 0.0}
            
        articles = []
        total_polarity = 0.0
        
        # Top 5 articles
        for item in news_items[:5]:
            # yfinance newer versions nest data inside item['content']
            content = item.get("content", item)  # fallback to item itself for older versions
            title = content.get("title", "")
            if not title:
                continue

            # Publisher
            provider = content.get("provider", {})
            publisher = provider.get("displayName", "Unknown") if isinstance(provider, dict) else "Unknown"

            # Link
            click_url = content.get("clickThroughUrl", {})
            canonical_url = content.get("canonicalUrl", {})
            link = (
                click_url.get("url") if isinstance(click_url, dict) else
                canonical_url.get("url") if isinstance(canonical_url, dict) else
                item.get("link", "#")
            ) or "#"
            
            polarity = TextBlob(title).sentiment.polarity
            total_polarity += polarity
            
            articles.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "sentiment_score": round(polarity, 2)
            })
            
        avg_polarity = total_polarity / len(articles) if articles else 0.0
        
        # Categorize
        if avg_polarity > 0.2:
            label = "Strongly Bullish"
        elif avg_polarity > 0.05:
            label = "Bullish"
        elif avg_polarity < -0.2:
            label = "Strongly Bearish"
        elif avg_polarity < -0.05:
            label = "Bearish"
        else:
            label = "Neutral"
            
        return {
            "articles": articles,
            "overall_sentiment": label,
            "score": round(avg_polarity, 3)
        }
    except Exception as e:
        return {"articles": [], "overall_sentiment": "Neutral", "score": 0.0, "error": str(e)}
