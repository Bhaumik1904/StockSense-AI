<div align="center">
  <h1>📈 StockSense AI</h1>
  <p><strong>A Full-Stack Smart Stock Analytics & ML Prediction Platform</strong></p>
  
  [![Live Demo](https://img.shields.io/badge/Live_Demo-StockSense_AI-00f2fe?style=for-the-badge&logo=render)](https://stocksenseai-49l5.onrender.com/)
  
  <br />

  [![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
  [![scikit-learn](https://img.shields.io/badge/scikit--learn-Machine_Learning-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://opensource.org/licenses/MIT)

</div>

---

## 🚀 Overview

**StockSense AI** is a comprehensive financial technology platform designed to empower users with real-time stock market data, deep historical analytics, and predictive modeling. Utilizing a robust **Flask** backend, **PostgreSQL** database, and machine learning pipelines powered by **scikit-learn**, it delivers actionable insights wrapped in a high-performance, aesthetically pleasing "glassmorphism" user interface.

[🔴 **View Live Application Here**](https://stocksenseai-49l5.onrender.com/)

## ✨ Key Features

- **Real-Time Market Data**: High-fidelity data fetching capabilities via the `yfinance` API.
- **Machine Learning Integration**: Next-day closing price prediction utilizing a reliable Linear Regression model based on a 5-day sliding window feature set.
- **Sentiment Analysis**: Incorporates `TextBlob` for processing and analyzing contextual market sentiment over specific assets.
- **Secure Authentication System**: Complete password hashing and secure session management scaling via Flask-Login.
- **Integrated Payments**: Ready-to-scale payment gateway processing built with the `Razorpay` SDK.
- **Dynamic Watchlist**: Seamless portfolio and favorites tracking backed by a relational database schema.
- **Premium UI/UX**: Custom-designed dark mode interface leveraging native CSS3 for fluid, hardware-accelerated animations and interactive `Chart.js` visualizations.

---

## 🛠️ Architecture & Tech Stack

| Component | Technology | 
|-----------|------------|
| **Backend** | Python, Flask, Gunicorn | 
| **Database** | PostgreSQL (Production) / SQLite (Local) | 
| **Machine Learning** | scikit-learn, Numpy, Pandas | 
| **Data Providers** | yfinance, yahooquery, curl_cffi |
| **Integrations** | Razorpay, TextBlob |
| **Frontend** | HTML5, Vanilla JS, CSS3, Chart.js |
| **Deployment** | Render, Vercel |

---

## ⚙️ Local Development Setup

To run this project locally, follow these steps:

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/stocksense-ai.git
cd stocksense-ai
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and configure your essential keys:
```env
SECRET_KEY=your_secret_flask_key
DATABASE_URL=your_postgresql_database_url
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
```
*(Note: If `DATABASE_URL` is omitted, the application will default to generating a local SQLite database for ease of use)*

### 5. Run the Server
```bash
python app.py
```
*The application should now be running locally at `http://127.0.0.1:5000/`*

---

## 🧠 Machine Learning Pipeline Walkthrough

1. **Data Extraction**: Pulls 6-12 months of historical closing sequences dynamically via `yfinance`.
2. **Feature Engineering**: Constructs a continuous 5-day sliding window structure as X variables to inform target behavior.
3. **Training & Split**: Standard 80/20 train/test data distribution logic.
4. **Modeling**: Core model is driven by `sklearn.linear_model.LinearRegression`.
5. **Evaluation**: Output efficiency is quantified utilizing Mean Absolute Error (MAE) and R² scoring benchmarks before surfacing recommendations.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE). Applications and algorithms built herein are strictly for educational and portfolio demonstration purposes and do not constitute formal financial advice.
