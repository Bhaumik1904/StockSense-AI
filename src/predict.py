"""
predict.py
----------
High-level prediction pipeline that combines data_loader and model modules.
This is the main entry point called by the Flask route /predict.

Now supports:
  - model_type   : "linear" | "random_forest"
  - forecast_days: 1 | 7 | 30
"""

from src.data_loader import fetch_historical_data, fetch_news_and_sentiment
from src.model import train_model, predict_next_price


def run_prediction(ticker: str, period: str = "1y",
                   model_type: str = "linear",
                   forecast_days: int = 1) -> dict:
    """
    Full prediction pipeline: fetch data → train model → predict.

    Args:
        ticker       : Stock ticker symbol (e.g., 'TCS.NS')
        period       : Historical period for training
        model_type   : "linear" | "random_forest"
        forecast_days: Number of future days to forecast (1, 7, 30)

    Returns:
        Dictionary with historical data, prediction results, and model metrics.
    """
    # Step 1: Fetch historical stock data
    stock_data = fetch_historical_data(ticker, period=period)
    if stock_data.get("error"):
        return {"error": stock_data["error"]}

    close_prices = stock_data["close"]

    if len(close_prices) < 20:
        return {"error": f"Insufficient data for '{ticker}'. Need at least 20 trading days."}

    # Step 2: Train the selected ML model
    trained_model = train_model(close_prices, model_type=model_type)
    if trained_model.get("error"):
        return {"error": trained_model["error"]}

    # Step 3: Predict for the requested forecast horizon
    prediction = predict_next_price(close_prices, trained_model,
                                    forecast_days=forecast_days)
    if prediction.get("error"):
        return {"error": prediction["error"]}

    # Step 4: Fetch news & sentiment (non-blocking — returns empty on failure)
    news = fetch_news_and_sentiment(ticker)

    # Step 5: Compile and return
    return {
        "ticker":  ticker.upper(),
        "period":  period,
        "historical": {
            "dates":          stock_data["dates"],
            "close":          stock_data["close"],
            "open":           stock_data["open"],
            "high":           stock_data["high"],
            "low":            stock_data["low"],
            "volume":         stock_data["volume"],
            "latest_date":    stock_data["latest_date"],
            "latest_close":   stock_data["latest_close"],
            "latest_open":    stock_data["latest_open"],
            "latest_high":    stock_data["latest_high"],
            "latest_low":     stock_data["latest_low"],
            "latest_volume":  stock_data["latest_volume"],
        },
        "prediction": {
            "predicted_price":   prediction["predicted_price"],
            "last_actual_price": prediction["last_actual_price"],
            "change":            prediction["change"],
            "change_pct":        prediction["change_pct"],
            "trend":             prediction["trend"],
            "trend_key":         prediction["trend_key"],
            "forecast_series":   prediction["forecast_series"],
            "forecast_days":     prediction["forecast_days"],
            "model_name":        prediction["model_name"],
        },
        "model_metrics": {
            "mae": prediction["mae"],
            "r2":  prediction["r2"],
        },
        "news":  news,
        "error": None
    }
