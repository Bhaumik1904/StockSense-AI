"""
model.py
--------
Machine Learning model module.
Supports two models:
  - Linear Regression (fast, baseline)
  - Random Forest    (ensemble, more robust)

Both support multi-day forecasting (1, 7, or 30 days) via
iterative rolling prediction.
"""

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
import warnings

warnings.filterwarnings("ignore")

WINDOW = 10   # sliding-window size (increased for better feature richness)


# ─────────────────────────────────────────────
# Shared feature preparation
# ─────────────────────────────────────────────

def prepare_features(close_prices: list, window: int = WINDOW) -> tuple:
    """
    Build a sliding-window feature matrix from closing prices.
    Returns (X, y) numpy arrays.
    """
    prices = np.array(close_prices, dtype=float)
    X, y = [], []
    for i in range(window, len(prices)):
        X.append(prices[i - window:i])
        y.append(prices[i])
    return np.array(X), np.array(y)


# ─────────────────────────────────────────────
# Model training
# ─────────────────────────────────────────────

def train_model(close_prices: list, window: int = WINDOW,
                model_type: str = "linear") -> dict:
    """
    Train a forecasting model on historical closing prices.

    Args:
        close_prices : List of historical close prices.
        window       : Number of past days per feature vector.
        model_type   : "linear" | "random_forest"

    Returns:
        Dict with trained model artefacts + evaluation metrics, or error.
    """
    if len(close_prices) < window + 10:
        return {"error": f"Not enough data. Need at least {window + 10} trading days."}

    try:
        X, y = prepare_features(close_prices, window)

        # Scale X (but NOT y – we predict raw prices so we can read them directly)
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)

        split = int(len(X_scaled) * 0.8)
        X_train, X_test = X_scaled[:split], X_scaled[split:]
        y_train, y_test = y[:split], y[split:]

        # Choose model
        if model_type == "random_forest":
            model = RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model_name = "Random Forest"
        else:
            model = LinearRegression()
            model_name = "Linear Regression"

        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        mae = round(float(mean_absolute_error(y_test, y_pred)), 4)
        r2  = round(float(r2_score(y_test, y_pred)), 4)

        return {
            "model":      model,
            "scaler":     scaler,
            "window":     window,
            "model_type": model_type,
            "model_name": model_name,
            "mae":        mae,
            "r2":         r2,
            "train_size": len(X_train),
            "test_size":  len(X_test),
            "error":      None
        }

    except Exception as e:
        return {"error": f"Training failed: {str(e)}"}


# ─────────────────────────────────────────────
# Multi-day iterative prediction
# ─────────────────────────────────────────────

def predict_next_price(close_prices: list, trained_model: dict,
                       forecast_days: int = 1) -> dict:
    """
    Predict the next `forecast_days` closing prices using the trained model.
    Uses iterative rolling: each predicted day becomes input for the next.

    Args:
        close_prices  : Historical closing prices list.
        trained_model : Dict returned by train_model().
        forecast_days : 1, 7, or 30 day horizon.

    Returns:
        Dict with final predicted price, full forecast series, and trend.
    """
    if trained_model.get("error"):
        return {"error": trained_model["error"]}

    try:
        model  = trained_model["model"]
        scaler = trained_model["scaler"]
        window = trained_model["window"]

        # Rolling buffer initialised with real historical closes
        prices_buffer = list(map(float, close_prices))
        forecast_series = []

        for _ in range(forecast_days):
            last_window = np.array(prices_buffer[-window:]).reshape(1, -1)
            last_window_scaled = scaler.transform(last_window)
            next_price = float(model.predict(last_window_scaled)[0])
            forecast_series.append(round(next_price, 4))
            prices_buffer.append(next_price)   # feed prediction back in

        predicted_price = forecast_series[-1]
        last_actual     = float(close_prices[-1])

        change     = predicted_price - last_actual
        change_pct = (change / last_actual) * 100 if last_actual != 0 else 0
        trend      = "UP 📈" if change >= 0 else "DOWN 📉"
        trend_key  = "up"    if change >= 0 else "down"

        return {
            "predicted_price":  round(predicted_price, 4),
            "last_actual_price": round(last_actual, 4),
            "change":            round(change, 4),
            "change_pct":        round(change_pct, 2),
            "trend":             trend,
            "trend_key":         trend_key,
            "forecast_series":   forecast_series,   # all intermediate days
            "forecast_days":     forecast_days,
            "model_name":        trained_model.get("model_name", "Linear Regression"),
            "mae":               trained_model.get("mae"),
            "r2":                trained_model.get("r2"),
            "error":             None
        }

    except Exception as e:
        return {"error": f"Prediction failed: {str(e)}"}
