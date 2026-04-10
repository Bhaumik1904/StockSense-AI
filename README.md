# Smart Stock Analytics & Prediction Web App

A full-stack web application for real-time stock market analysis and ML-powered next-day price prediction.

## 🚀 Features

- **User Authentication** – Register, login, logout with secure password hashing
- **Real-Time Stock Data** – Fetch OHLCV data via Yahoo Finance (yfinance)
- **Interactive Charts** – Beautiful Chart.js price history with prediction overlay
- **ML Prediction** – Linear Regression model predicts next day's closing price
- **Favorites System** – Save and track your watchlist
- **Search History** – Quickly re-analyze recent stocks
- **Premium Dark UI** – Glassmorphism design with animations

## 🧱 Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python, Flask                     |
| Database  | SQLite                            |
| ML Model  | scikit-learn (Linear Regression)  |
| Data      | yfinance (Yahoo Finance)          |
| Charts    | Chart.js                          |
| Frontend  | HTML5, CSS3 (vanilla), JavaScript |

## 📁 Project Structure

```
stock_web_app/
├── app.py                  # Flask entry point, all routes & API
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/style.css       # Premium dark-mode glassmorphism styles
│   └── js/main.js          # Chart rendering, fetch API, UI logic
├── templates/
│   ├── index.html          # Landing page
│   ├── login.html          # Login form
│   ├── register.html       # Registration form
│   └── dashboard.html      # Main user dashboard
├── database/
│   └── db.sqlite3          # SQLite database (auto-created on first run)
└── src/
    ├── __init__.py
    ├── data_loader.py      # yfinance data fetching utilities
    ├── model.py            # Linear Regression training pipeline
    └── predict.py          # Full prediction pipeline (data → train → predict)
```

## ⚙️ Setup & Installation

### 1. Clone / Navigate to project directory

```bash
cd stock_web_app
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python app.py
```

### 5. Open in browser

```
http://localhost:5000
```

## 🔗 API Endpoints

| Method | Route              | Description                             |
|--------|--------------------|-----------------------------------------|
| GET    | `/`                | Landing page                            |
| GET    | `/login`           | Login page                              |
| POST   | `/login`           | Authenticate user                       |
| GET    | `/register`        | Register page                           |
| POST   | `/register`        | Create new user                         |
| GET    | `/logout`          | Clear session, redirect to login        |
| GET    | `/dashboard`       | User dashboard (auth required)          |
| POST   | `/predict`         | Fetch stock data + ML prediction (JSON) |
| POST   | `/favorite`        | Toggle favorite stock (JSON)            |
| GET    | `/is_favorite/<t>` | Check if ticker is favorited (JSON)     |
| POST   | `/history/delete`  | Clear user's search history (JSON)      |

## 🤖 How the ML Model Works

1. **Data**: Fetches 6–12 months of historical closing prices via yfinance
2. **Features**: Uses a sliding window of the last **5 days** as features (X)
3. **Target**: The next day's closing price (y)
4. **Split**: 80% training / 20% testing
5. **Model**: `sklearn.linear_model.LinearRegression`
6. **Metrics**: Reports MAE (Mean Absolute Error) and R² score
7. **Prediction**: Uses the most recent 5 closing prices to predict tomorrow

## ⚠️ Disclaimer

This application is for **educational purposes only**. Stock predictions are not financial advice. Always consult a qualified financial advisor before making investment decisions.

## 📦 Dependencies

```
Flask==3.0.3
Flask-Login==0.6.3
Werkzeug==3.0.3
yfinance==0.2.40
scikit-learn==1.5.1
numpy==1.26.4
pandas==2.2.2
requests==2.32.3
python-dateutil==2.9.0
```
