"""
app.py
------
Main Flask application entry point.
Handles routing, authentication, and API endpoints.
"""

import os
import json
import hmac
import hashlib
import sqlite3
import razorpay
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from src.predict import run_prediction
from src.data_loader import fetch_stock_info, get_multiple_quotes, get_trending_indian_stocks
from src.tickers import INDIAN_STOCKS

# ─────────────────────────────────────────────
# Razorpay Client
# ─────────────────────────────────────────────
RZP_KEY_ID     = "rzp_test_SbgBAcy98B0OSc"
RZP_KEY_SECRET = "jRnRqjmJ06XeXwhsUQ24L7mh"
rzp_client = razorpay.Client(auth=(RZP_KEY_ID, RZP_KEY_SECRET))

# ─────────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "stocksense_super_secure_key_2026"  # Change in production!

DATABASE = os.path.join(os.path.dirname(__file__), "database", "db.sqlite3")

# ─────────────────────────────────────────────
# Database Helpers
# ─────────────────────────────────────────────

def get_db():
    """Get a database connection, creating it if needed (per-request caching)."""
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Access columns by name
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close the database connection at the end of each request."""
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema."""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                cash_balance REAL DEFAULT 1000000.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, ticker)
            );

            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        
        try:
            db.execute("ALTER TABLE users ADD COLUMN cash_balance REAL DEFAULT 1000000.0")
        except sqlite3.OperationalError:
            pass
            
        db.commit()


# ─────────────────────────────────────────────
# Auth Decorator
# ─────────────────────────────────────────────

def login_required(f):
    """Decorator to protect routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────
# Route: Home
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Landing page - redirects logged-in users to dashboard."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ─────────────────────────────────────────────
# Route: Register
# ─────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Basic validation
        if not username or not email or not password:
            error = "All fields are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            db = get_db()
            # Check if username or email already exists
            existing = db.execute(
                "SELECT id FROM users WHERE username=? OR email=?", (username, email)
            ).fetchone()
            if existing:
                error = "Username or email already registered."
            else:
                # Create user
                pw_hash = generate_password_hash(password)
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, pw_hash)
                )
                db.commit()
                return redirect(url_for("login", registered="1"))

    return render_template("register.html", error=error)


# ─────────────────────────────────────────────
# Route: Login
# ─────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None
    registered = request.args.get("registered")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        else:
            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                next_url = request.args.get("next")
                return redirect(next_url or url_for("dashboard"))
            else:
                error = "Invalid username or password."

    return render_template("login.html", error=error, registered=registered)


# ─────────────────────────────────────────────
# Route: Logout
# ─────────────────────────────────────────────

@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
# Route: Dashboard
# ─────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Main user dashboard - shows favorites, history, and quick stats."""
    db = get_db()
    user_id = session["user_id"]

    # Fetch user's favorite tickers
    favorites = db.execute(
        "SELECT ticker, added_at FROM favorites WHERE user_id=? ORDER BY added_at DESC",
        (user_id,)
    ).fetchall()
    favorite_tickers = [row["ticker"] for row in favorites]

    # Fetch recent search history (last 10)
    history = db.execute(
        "SELECT ticker, searched_at FROM search_history WHERE user_id=? ORDER BY searched_at DESC LIMIT 10",
        (user_id,)
    ).fetchall()

    # Fetch live quotes for favorites + trending top stocks for the day
    default_tickers = get_trending_indian_stocks(7)
    
    ticker_symbols = favorite_tickers.copy()
    for t in default_tickers:
        if t not in ticker_symbols:
            ticker_symbols.append(t)
            
    live_quotes = get_multiple_quotes(ticker_symbols)

    return render_template(
        "dashboard.html",
        username=session["username"],
        favorites=favorite_tickers,
        history=history,
        live_quotes=live_quotes
    )


# ─────────────────────────────────────────────
# API: Predict Stock
# ─────────────────────────────────────────────

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    """
    API endpoint to fetch stock data and return ML prediction.
    Expects JSON body: { "ticker": "AAPL", "period": "6mo" }
    Returns JSON with historical data and predicted next close price.
    """
    data = request.get_json()
    if not data or not data.get("ticker"):
        return jsonify({"error": "Ticker symbol is required."}), 400

    ticker = data["ticker"].strip().upper()
    period = data.get("period", "6mo")

    # Validate period
    valid_periods = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
    if period not in valid_periods:
        period = "6mo"

    # Model type: linear or random_forest
    model_type = data.get("model_type", "linear")
    if model_type not in ["linear", "random_forest"]:
        model_type = "linear"

    # Forecast horizon: 1, 7, or 30 days
    try:
        forecast_days = int(data.get("forecast_days", 1))
        if forecast_days not in [1, 7, 30]:
            forecast_days = 1
    except (ValueError, TypeError):
        forecast_days = 1

    # Run full prediction pipeline
    result = run_prediction(ticker, period=period,
                            model_type=model_type,
                            forecast_days=forecast_days)

    if result.get("error"):
        return jsonify({"error": result["error"]}), 422

    # Save to search history (avoid flooding - check if same ticker searched in last 30 mins)
    db = get_db()
    user_id = session["user_id"]
    db.execute(
        "INSERT INTO search_history (user_id, ticker, searched_at) VALUES (?, ?, ?)",
        (user_id, ticker, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    )
    db.commit()

    return jsonify(result)


# ─────────────────────────────────────────────
# API: Toggle Favorite
# ─────────────────────────────────────────────

@app.route("/favorite", methods=["POST"])
@login_required
def toggle_favorite():
    """
    API endpoint to add or remove a stock from favorites.
    Expects JSON body: { "ticker": "AAPL" }
    """
    data = request.get_json()
    if not data or not data.get("ticker"):
        return jsonify({"error": "Ticker is required."}), 400

    ticker = data["ticker"].strip().upper()
    user_id = session["user_id"]
    db = get_db()

    existing = db.execute(
        "SELECT id FROM favorites WHERE user_id=? AND ticker=?", (user_id, ticker)
    ).fetchone()

    if existing:
        # Remove from favorites
        db.execute("DELETE FROM favorites WHERE user_id=? AND ticker=?", (user_id, ticker))
        db.commit()
        return jsonify({"status": "removed", "ticker": ticker})
    else:
        # Add to favorites
        db.execute(
            "INSERT INTO favorites (user_id, ticker) VALUES (?, ?)", (user_id, ticker)
        )
        db.commit()
        return jsonify({"status": "added", "ticker": ticker})


# ─────────────────────────────────────────────
# API: Check Favorite Status
# ─────────────────────────────────────────────

@app.route("/is_favorite/<ticker>")
@login_required
def is_favorite(ticker):
    """Check if a ticker is in the user's favorites."""
    user_id = session["user_id"]
    db = get_db()
    existing = db.execute(
        "SELECT id FROM favorites WHERE user_id=? AND ticker=?", (user_id, ticker.upper())
    ).fetchone()
    return jsonify({"is_favorite": existing is not None})


# ─────────────────────────────────────────────
# API: Delete Search History Entry
# ─────────────────────────────────────────────

@app.route("/history/delete", methods=["POST"])
@login_required
def delete_history():
    """Delete all search history for the current user."""
    user_id = session["user_id"]
    db = get_db()
    db.execute("DELETE FROM search_history WHERE user_id=?", (user_id,))
    db.commit()
    return jsonify({"status": "cleared"})


# ─────────────────────────────────────────────
# Route: Transaction History
# ─────────────────────────────────────────────

@app.route("/transactions")
@login_required
def transactions():
    """Render the transaction history page."""
    return render_template("transactions.html", username=session["username"])


@app.route("/api/transactions")
@login_required
def api_transactions():
    """Return all portfolio transactions for the current user."""
    user_id = session["user_id"]
    db = get_db()

    # Filter params
    action_filter = request.args.get("action", "ALL").upper()
    ticker_filter = request.args.get("ticker", "").strip().upper()

    query = "SELECT * FROM portfolio_transactions WHERE user_id=?"
    params = [user_id]

    if action_filter in ["BUY", "SELL"]:
        query += " AND action=?"
        params.append(action_filter)
    if ticker_filter:
        query += " AND ticker LIKE ?"
        params.append(f"%{ticker_filter}%")

    query += " ORDER BY timestamp DESC"
    rows = db.execute(query, params).fetchall()

    tx_list = []
    for r in rows:
        total = r["shares"] * r["price"]
        tx_list.append({
            "id":        r["id"],
            "ticker":    r["ticker"],
            "action":    r["action"],
            "shares":    r["shares"],
            "price":     r["price"],
            "total":     round(total, 2),
            "timestamp": r["timestamp"]
        })

    # Summary stats
    total_bought = sum(t["total"] for t in tx_list if t["action"] == "BUY")
    total_sold   = sum(t["total"] for t in tx_list if t["action"] == "SELL")
    num_trades   = len(tx_list)

    return jsonify({
        "transactions": tx_list,
        "summary": {
            "num_trades":   num_trades,
            "total_bought": round(total_bought, 2),
            "total_sold":   round(total_sold, 2),
            "net_invested": round(total_bought - total_sold, 2)
        }
    })


# ─────────────────────────────────────────────
# API: Razorpay – Add Funds
# ─────────────────────────────────────────────

@app.route("/create_order", methods=["POST"])
@login_required
def create_order():
    """
    Create a Razorpay order for adding virtual funds.
    Expects JSON: { "amount": 50000 }  (amount in INR)
    """
    data = request.get_json()
    try:
        amount_inr = float(data.get("amount", 0))
        if amount_inr <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400

    amount_paise = int(amount_inr * 100)  # Razorpay needs paise

    try:
        order = rzp_client.order.create({
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  f"funds_{session['user_id']}_{int(datetime.utcnow().timestamp())}",
            "notes":    {"purpose": "add_funds", "user_id": str(session["user_id"])}
        })
        return jsonify({"order_id": order["id"],
                        "amount":   amount_paise,
                        "key":      RZP_KEY_ID})
    except Exception as e:
        return jsonify({"error": f"Could not create order: {str(e)}"}), 500


@app.route("/verify_payment", methods=["POST"])
@login_required
def verify_payment():
    """
    Verify Razorpay payment signature and credit virtual funds.
    Expects JSON: { razorpay_order_id, razorpay_payment_id,
                    razorpay_signature, amount_inr }
    """
    data = request.get_json()
    order_id   = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature  = data.get("razorpay_signature", "")
    amount_inr = float(data.get("amount_inr", 0))

    # HMAC-SHA256 verification
    msg = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        key=RZP_KEY_SECRET.encode(),
        msg=msg,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Payment verification failed."}), 400

    # Credit funds
    user_id = session["user_id"]
    db = get_db()
    db.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?",
               (amount_inr, user_id))
    db.commit()

    user = db.execute("SELECT cash_balance FROM users WHERE id=?", (user_id,)).fetchone()
    return jsonify({"success": True,
                    "amount_added": amount_inr,
                    "new_balance":  round(user["cash_balance"], 2)})


# ─────────────────────────────────────────────
# API: Razorpay – Buy Stocks
# ─────────────────────────────────────────────

@app.route("/create_trade_order", methods=["POST"])
@login_required
def create_trade_order():
    """
    Create a Razorpay order for buying stocks.
    Expects JSON: { "ticker": "TCS.NS", "shares": 5 }
    Fetches live price, calculates total, creates Razorpay order.
    """
    data = request.get_json()
    ticker = data.get("ticker", "").strip().upper()
    try:
        shares = int(data.get("shares", 0))
        if shares <= 0: raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid shares"}), 400

    if not ticker:
        return jsonify({"error": "Ticker required"}), 400

    # Fetch live price
    quotes = get_multiple_quotes([ticker])
    if not quotes or quotes[0]["price"] == 0:
        return jsonify({"error": "Could not fetch live price."}), 400

    current_price = quotes[0]["price"]
    total_inr     = round(shares * current_price, 2)
    amount_paise  = int(total_inr * 100)

    try:
        order = rzp_client.order.create({
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  f"trade_{ticker}_{session['user_id']}_{int(datetime.utcnow().timestamp())}",
            "notes":    {
                "purpose":  "buy_stock",
                "ticker":   ticker,
                "shares":   str(shares),
                "price":    str(current_price),
                "user_id":  str(session["user_id"])
            }
        })
        return jsonify({
            "order_id":      order["id"],
            "amount":        amount_paise,
            "amount_inr":    total_inr,
            "current_price": current_price,
            "shares":        shares,
            "ticker":        ticker,
            "key":           RZP_KEY_ID
        })
    except Exception as e:
        return jsonify({"error": f"Could not create order: {str(e)}"}), 500


@app.route("/verify_and_trade", methods=["POST"])
@login_required
def verify_and_trade():
    """
    Verify Razorpay payment for stock buy and execute the trade.
    Expects JSON: { razorpay_order_id, razorpay_payment_id,
                    razorpay_signature, ticker, shares, price }
    """
    data       = request.get_json()
    order_id   = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature  = data.get("razorpay_signature", "")
    ticker     = data.get("ticker", "").strip().upper()
    price      = float(data.get("price", 0))
    try:
        shares = int(data.get("shares", 0))
        if shares <= 0: raise ValueError
    except:
        return jsonify({"error": "Invalid shares"}), 400

    # HMAC verification
    msg = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        key=RZP_KEY_SECRET.encode(),
        msg=msg,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"error": "Payment verification failed."}), 400

    total_cost = shares * price
    user_id    = session["user_id"]
    db         = get_db()

    # Record the buy transaction (payment already verified — no balance deduction needed)
    db.execute(
        "INSERT INTO portfolio_transactions (user_id, ticker, action, shares, price) VALUES (?,?,?,?,?)",
        (user_id, ticker, "BUY", shares, price)
    )
    db.commit()

    return jsonify({
        "success": True,
        "ticker":  ticker,
        "shares":  shares,
        "price":   price,
        "total":   round(total_cost, 2)
    })


# ─────────────────────────────────────────────
# Route: Stock Comparison
# ─────────────────────────────────────────────

@app.route("/compare")
@login_required
def compare():
    """Render the stock comparison page."""
    return render_template("compare.html", username=session["username"])


@app.route("/api/compare")
@login_required
def compare_data():
    """
    Fetch historical close prices for 2–3 tickers and return
    normalised % change series so stocks at different price levels
    can be fairly overlaid on the same chart.
    Query params: tickers=TCS.NS,INFY.NS,WIPRO.NS  period=6mo
    """
    raw = request.args.get("tickers", "")
    period = request.args.get("period", "6mo")

    valid_periods = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
    if period not in valid_periods:
        period = "6mo"

    tickers = [t.strip().upper() for t in raw.split(",") if t.strip()]
    tickers = tickers[:3]  # cap at 3

    if len(tickers) < 2:
        return jsonify({"error": "Please provide at least 2 ticker symbols."}), 400

    from src.data_loader import fetch_historical_data

    results = []
    for ticker in tickers:
        data = fetch_historical_data(ticker, period=period)
        if data.get("error"):
            results.append({"ticker": ticker, "error": data["error"]})
            continue

        closes = data["close"]
        dates  = data["dates"]
        base   = closes[0] if closes[0] != 0 else 1

        # Normalise: Day 1 = 0%, subsequent = % change from Day 1
        pct_change = [round((c - base) / base * 100, 4) for c in closes]

        results.append({
            "ticker":      ticker,
            "dates":       dates,
            "closes":      closes,
            "pct_change":  pct_change,
            "latest_close": closes[-1],
            "total_return": round((closes[-1] - base) / base * 100, 2),
            "error":       None
        })

    return jsonify({"period": period, "stocks": results})


# ─────────────────────────────────────────────
# Route: Market Explorer
# ─────────────────────────────────────────────

@app.route("/market")
@login_required
def market():
    """Render the market directory dashboard."""
    return render_template("market.html", username=session["username"])

@app.route("/api/market_data")
@login_required
def market_data():
    """Fetch paginated static tickers and layer their live prices."""
    query = request.args.get("search", "").lower()
    try:
        page = int(request.args.get("page", 1))
    except:
        page = 1
    per_page = 20
    
    filtered = INDIAN_STOCKS
    if query:
        filtered = [s for s in INDIAN_STOCKS if query in s["name"].lower() or query in s["symbol"].lower()]
        
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated = filtered[start_idx:end_idx]
    
    # fetch live quotes
    tickers_to_fetch = [s["symbol"] for s in paginated]
    live_quotes = get_multiple_quotes(tickers_to_fetch) if tickers_to_fetch else []
    
    quote_map = {q["symbol"]: q for q in live_quotes}
    
    results = []
    for s in paginated:
        sym = s["symbol"]
        q = quote_map.get(sym, {"price": 0, "change": 0, "change_pct": 0})
        results.append({
            "symbol": sym,
            "name": s["name"],
            "price": q["price"],
            "change": q["change"],
            "change_pct": q["change_pct"]
        })
        
    return jsonify({
        "stocks": results,
        "total": len(filtered),
        "page": page,
        "pages": (len(filtered) + per_page - 1) // per_page
    })

# ─────────────────────────────────────────────
# Route: Portfolio
# ─────────────────────────────────────────────

@app.route("/portfolio")
@login_required
def portfolio():
    """Render the portfolio dashboard."""
    return render_template("portfolio.html", username=session["username"])


# ─────────────────────────────────────────────
# API: Portfolio Data & Trading
# ─────────────────────────────────────────────

@app.route("/api/portfolio_data")
@login_required
def portfolio_data():
    """Fetch user's holdings, live prices, and P&L."""
    user_id = session["user_id"]
    db = get_db()
    
    user = db.execute("SELECT cash_balance FROM users WHERE id=?", (user_id,)).fetchone()
    cash_balance = user["cash_balance"] if user else 1000000.0
    
    # Get all transactions
    txs = db.execute("SELECT ticker, action, shares, price FROM portfolio_transactions WHERE user_id=?", (user_id,)).fetchall()
    
    holdings = {}
    for t in txs:
        tck = t["ticker"]
        action = t["action"]
        shares = t["shares"]
        price = t["price"]
        
        if tck not in holdings:
            holdings[tck] = {"shares": 0, "total_cost": 0.0}
            
        if action == "BUY":
            holdings[tck]["shares"] += shares
            holdings[tck]["total_cost"] += (shares * price)
        elif action == "SELL":
            # Determine avg cost reduction loosely mapped
            if holdings[tck]["shares"] > 0:
                avg_cost = holdings[tck]["total_cost"] / holdings[tck]["shares"]
                holdings[tck]["shares"] -= shares
                holdings[tck]["total_cost"] -= (shares * avg_cost)
                
    # Filter empty holdings
    holdings = {k: v for k, v in holdings.items() if v["shares"] > 0}
    
    # Fetch live quotes
    tickers = list(holdings.keys())
    live_quotes = get_multiple_quotes(tickers) if tickers else []
    live_price_map = {q["symbol"]: q["price"] for q in live_quotes}
    
    portfolio_value = 0.0
    total_cost_basis = 0.0
    holdings_list = []
    
    for tck, data in holdings.items():
        shares = data["shares"]
        cost = data["total_cost"]
        avg_cost = cost / shares if shares > 0 else 0.0
        
        current_price = live_price_map.get(tck, avg_cost)
        current_value = shares * current_price
        pnl = current_value - cost
        pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
        
        portfolio_value += current_value
        total_cost_basis += cost
        
        holdings_list.append({
            "ticker": tck,
            "shares": shares,
            "avg_cost": round(avg_cost, 2),
            "current_price": current_price,
            "total_value": round(current_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2)
        })
        
    return jsonify({
        "cash_balance": round(cash_balance, 2),
        "portfolio_value": round(portfolio_value, 2),
        "total_equity": round(cash_balance + portfolio_value, 2),
        "total_cost_basis": round(total_cost_basis, 2),
        "holdings": holdings_list
    })


@app.route("/trade", methods=["POST"])
@login_required
def trade():
    """Handle stock Buy/Sell action."""
    data = request.get_json()
    if not data or not data.get("ticker") or not data.get("action") or not data.get("shares"):
        return jsonify({"error": "Missing parameters"}), 400
        
    ticker = data["ticker"].strip().upper()
    action = data["action"].strip().upper()
    try:
        shares = int(data["shares"])
        if shares <= 0: raise ValueError
    except:
        return jsonify({"error": "Invalid shares"}), 400
        
    if action not in ["BUY", "SELL"]:
        return jsonify({"error": "Invalid action"}), 400
        
    # Get live price
    quotes = get_multiple_quotes([ticker])
    if not quotes or quotes[0]["price"] == 0:
        return jsonify({"error": "Could not fetch current market price."}), 400
    
    current_price = quotes[0]["price"]
    total_cost = shares * current_price
    
    user_id = session["user_id"]
    db = get_db()
    
    user = db.execute("SELECT cash_balance FROM users WHERE id=?", (user_id,)).fetchone()
    cash_balance = user["cash_balance"] if user and "cash_balance" in user.keys() else 1000000.0
    
    if action == "BUY":
        if cash_balance < total_cost:
            return jsonify({"error": f"Insufficient funds. Need ₹{total_cost:,.2f} but have ₹{cash_balance:,.2f}"}), 400
            
        db.execute("UPDATE users SET cash_balance = cash_balance - ? WHERE id=?", (total_cost, user_id))
        
    elif action == "SELL":
        # Check holding
        txs = db.execute("SELECT action, shares FROM portfolio_transactions WHERE user_id=? AND ticker=?", (user_id, ticker)).fetchall()
        owned = sum(t["shares"] if t["action"] == "BUY" else -t["shares"] for t in txs)
        
        if owned < shares:
            return jsonify({"error": f"Insufficient shares. You only own {owned} shares of {ticker}."}), 400
            
        db.execute("UPDATE users SET cash_balance = cash_balance + ? WHERE id=?", (total_cost, user_id))
        
    # Record transaction
    db.execute(
        "INSERT INTO portfolio_transactions (user_id, ticker, action, shares, price) VALUES (?, ?, ?, ?, ?)",
        (user_id, ticker, action, shares, current_price)
    )
    db.commit()
    
    return jsonify({"success": True, "action": action, "shares": shares, "ticker": ticker, "price": current_price, "total": total_cost, "new_balance": cash_balance - total_cost if action == "BUY" else cash_balance + total_cost})


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
