/**
 * main.js
 * -------
 * Core JavaScript for Smart Stock Analytics App.
 * Handles stock search, chart rendering, predictions, favorites, and history.
 */

// ─────────────────────────────────────────────
// Global State
// ─────────────────────────────────────────────
let priceChart = null;       // Chart.js instance
let currentTicker = null;    // Currently searched ticker
let isFavorite = false;      // Whether current ticker is favorited

const POPULAR_TICKERS = [
  "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
  "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "HINDUNILVR.NS"
];

// ─────────────────────────────────────────────
// DOM Ready
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  setupTickerPills();
  setupSearchForm();
  setupFavoriteButton();
  setupHistoryItems();
  setupFavoriteChips();
  setupClearHistory();
  setupEnterKey();
  setupTradeModal();
  
  const urlParams = new URLSearchParams(window.location.search);
  const paramTicker = urlParams.get('ticker');
  if(paramTicker) {
    triggerSearch(paramTicker);
  }
});

// ─────────────────────────────────────────────
// Toast Notification System
// ─────────────────────────────────────────────

/**
 * Show a brief toast notification.
 * @param {string} message - Message to display
 * @param {"success"|"error"|"info"} type - Toast type
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);

  // Auto-remove after 3.5 seconds
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ─────────────────────────────────────────────
// Popular Ticker Pills Setup
// ─────────────────────────────────────────────
function setupTickerPills() {
  const container = document.getElementById("ticker-pills");
  if (!container) return;

  POPULAR_TICKERS.forEach(ticker => {
    const pill = document.createElement("span");
    pill.className = "ticker-pill";
    pill.textContent = ticker;
    pill.addEventListener("click", () => {
      const input = document.getElementById("ticker-input");
      if (input) {
        input.value = ticker;
        triggerSearch(ticker);
      }
    });
    container.appendChild(pill);
  });
}

// ─────────────────────────────────────────────
// Search Form
// ─────────────────────────────────────────────
function setupSearchForm() {
  const form = document.getElementById("search-form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const ticker = document.getElementById("ticker-input").value.trim().toUpperCase();
    const period = document.getElementById("period-select")?.value || "6mo";
    if (ticker) triggerSearch(ticker, period);
  });
}

function setupEnterKey() {
  const input = document.getElementById("ticker-input");
  if (!input) return;
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const ticker = input.value.trim().toUpperCase();
      const period = document.getElementById("period-select")?.value || "6mo";
      if (ticker) triggerSearch(ticker, period);
    }
  });
}

// ─────────────────────────────────────────────
// Core: Trigger Stock Search & Prediction
// ─────────────────────────────────────────────

/**
 * Main function: calls /predict endpoint and updates UI.
 * @param {string} ticker - Stock symbol
 * @param {string} period - Time period
 */
async function triggerSearch(ticker, period = "6mo") {
  ticker = ticker.toUpperCase();
  if (ticker.indexOf('.') === -1) {
    ticker = ticker + '.NS';
  }

  // Update UI input
  const input = document.getElementById("ticker-input");
  if (input) input.value = ticker;

  // Show loading state
  showLoadingState();
  hideResultsSection();

  try {
    const modelType   = document.getElementById("model-select")?.value || "linear";
    const forecastDays = parseInt(document.getElementById("forecast-select")?.value || "1");

    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, period, model_type: modelType, forecast_days: forecastDays })
    });

    const data = await response.json();

    if (data.error) {
      showErrorState(data.error);
      showToast(data.error, "error");
      return;
    }

    // Success: update all sections
    currentTicker = ticker;
    updateOHLC(data);
    updatePrediction(data);
    renderChart(data);
    updateNews(data);
    updateFavoriteButton(ticker);
    showResultsSection();
    showToast(`${ticker} loaded successfully!`, "success");

  } catch (err) {
    showErrorState("Network error. Please check your internet connection.");
    showToast("Failed to connect to the server.", "error");
  } finally {
    hideLoadingState();
  }
}

// ─────────────────────────────────────────────
// UI State Helpers
// ─────────────────────────────────────────────
function showLoadingState() {
  const el = document.getElementById("loading-state");
  if (el) el.classList.remove("hidden");
  const btn = document.getElementById("search-btn");
  if (btn) { btn.disabled = true; btn.innerHTML = '⏳ Loading...'; }
}

function hideLoadingState() {
  const el = document.getElementById("loading-state");
  if (el) el.classList.add("hidden");
  const btn = document.getElementById("search-btn");
  if (btn) { btn.disabled = false; btn.innerHTML = '🔍 Analyze'; }
}

function showResultsSection() {
  const el = document.getElementById("results-section");
  if (el) { el.classList.remove("hidden"); el.classList.add("fade-in"); }
}

function hideResultsSection() {
  const el = document.getElementById("results-section");
  if (el) el.classList.add("hidden");
}

function showErrorState(message) {
  hideLoadingState();
  const el = document.getElementById("error-state");
  if (el) {
    el.textContent = `⚠️ ${message}`;
    el.classList.remove("hidden");
    setTimeout(() => el.classList.add("hidden"), 6000);
  }
}

// ─────────────────────────────────────────────
// Update OHLC Stats
// ─────────────────────────────────────────────
function updateOHLC(data) {
  const h = data.historical;
  const formatPrice = (v) => `₹${Number(v).toFixed(2)}`;
  const formatVol = (v) => {
    if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
    if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(2)}K`;
    return v;
  };

  setText("stat-open",   formatPrice(h.latest_open));
  setText("stat-close",  formatPrice(h.latest_close));
  setText("stat-high",   formatPrice(h.latest_high));
  setText("stat-low",    formatPrice(h.latest_low));
  setText("stat-volume", formatVol(h.latest_volume));
  setText("stat-date",   h.latest_date);
  setText("current-ticker-name", data.ticker);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ─────────────────────────────────────────────
// Update Prediction Section
// ─────────────────────────────────────────────
function updatePrediction(data) {
  const p = data.prediction;
  const m = data.model_metrics;

  // Model badge
  setText("pred-model-badge", p.model_name || "Linear Regression");

  // Main predicted price
  const days = p.forecast_days || 1;
  setText("pred-price", `₹${p.predicted_price.toFixed(2)}`);

  // Horizon note
  const horizonNote = days === 1
    ? "Predicted for next trading day"
    : `Predicted price after ${days} trading days`;
  setText("pred-horizon-note", horizonNote);

  setText("pred-actual", `₹${p.last_actual_price.toFixed(2)}`);
  setText("pred-change", `${p.change >= 0 ? "+" : ""}₹${p.change.toFixed(2)} (${p.change_pct >= 0 ? "+" : ""}${p.change_pct.toFixed(2)}%)`);

  // Trend badge
  const trendEl = document.getElementById("pred-trend");
  if (trendEl) {
    trendEl.textContent = p.trend;
    trendEl.className = "prediction-trend " + (p.trend_key === "up" ? "up" : "down");
  }

  // Change color
  const changeEl = document.getElementById("pred-change");
  if (changeEl) {
    changeEl.className = p.change >= 0 ? "text-success text-mono" : "text-danger text-mono";
  }

  // Forecast series: show mini bars for 7/30-day forecasts
  const seriesSection = document.getElementById("forecast-series-section");
  const seriesBars    = document.getElementById("forecast-series-bars");
  if (p.forecast_series && p.forecast_series.length > 1 && seriesSection && seriesBars) {
    seriesSection.style.display = "block";
    const minVal = Math.min(...p.forecast_series);
    const maxVal = Math.max(...p.forecast_series);
    const range  = maxVal - minVal || 1;
    seriesBars.innerHTML = "";
    p.forecast_series.forEach((price, i) => {
      const heightPct = 30 + ((price - minVal) / range) * 50;
      const color = price >= p.last_actual_price ? "#10b981" : "#ef4444";
      const bar = document.createElement("div");
      bar.title = `Day ${i+1}: ₹${price.toFixed(2)}`;
      bar.style.cssText = `
        width: ${days <= 7 ? 28 : 16}px;
        height: ${heightPct}px;
        background: ${color};
        border-radius: 3px;
        opacity: 0.75;
        transition: opacity 0.2s;
        cursor: default;
      `;
      bar.addEventListener("mouseenter", () => bar.style.opacity = "1");
      bar.addEventListener("mouseleave", () => bar.style.opacity = "0.75");
      seriesBars.appendChild(bar);
    });
  } else if (seriesSection) {
    seriesSection.style.display = "none";
  }

  // Model metrics
  if (m) {
    setText("metric-mae", m.mae !== null ? `₹${m.mae.toFixed(2)}` : "N/A");
    setText("metric-r2",  m.r2  !== null ? m.r2.toFixed(3)       : "N/A");
  }
}

// ─────────────────────────────────────────────
// Update News & Sentiment
// ─────────────────────────────────────────────
function updateNews(data) {
  const news = data.news;
  if (!news) return;

  const badge = document.getElementById("news-sentiment-badge");
  const list  = document.getElementById("news-list");

  if (badge) {
    badge.innerText = news.overall_sentiment;
    if (news.overall_sentiment.includes("Bullish")) {
      badge.className = "badge badge-up";
    } else if (news.overall_sentiment.includes("Bearish")) {
      badge.className = "badge badge-down";
    } else {
      badge.className = "badge badge-neutral";
    }
  }

  if (!list) return;
  list.innerHTML = "";

  if (!news.articles || news.articles.length === 0) {
    list.innerHTML = `<li class="news-item"><span class="news-title" style="color:var(--text-muted);">No recent news found for this stock.</span></li>`;
    return;
  }

  news.articles.forEach(art => {
    const score = art.sentiment_score;
    let sentClass, sentLabel, sentDot;
    if (score > 0.05)       { sentClass = "sent-up";      sentLabel = "Bullish"; sentDot = "#22c55e"; }
    else if (score < -0.05) { sentClass = "sent-down";    sentLabel = "Bearish"; sentDot = "#ef4444"; }
    else                    { sentClass = "sent-neutral";  sentLabel = "Neutral"; sentDot = "#f59e0b"; }

    const li = document.createElement("li");
    li.className = "news-item";
    li.innerHTML = `
      <div style="display:flex; align-items:flex-start; gap:10px;">
        <span class="news-sent-dot" style="background:${sentDot}; margin-top:5px;"></span>
        <div style="flex:1; min-width:0;">
          <a href="${art.link}" target="_blank" class="news-title">${art.title}</a>
          <div class="news-meta">
            <span class="news-source">${art.publisher}</span>
            <span class="news-sep">·</span>
            <span class="news-sent-badge ${sentClass}">${sentLabel}</span>
            <span class="news-sep">·</span>
            <span class="news-score">${score > 0 ? '+' : ''}${score.toFixed(3)}</span>
          </div>
        </div>
      </div>
    `;
    list.appendChild(li);
  });
}

// ─────────────────────────────────────────────
// Chart.js Rendering
// ─────────────────────────────────────────────

/**
 * Render (or update) the price chart using Chart.js.
 * @param {Object} data - Response from /predict API
 */
function renderChart(data) {
  const ctx = document.getElementById("price-chart");
  if (!ctx) return;

  const h      = data.historical;
  const closes = h.close;
  const dates  = h.dates;
  const isUp   = data.prediction.trend_key === "up";
  const trendColor = isUp ? "#22c55e" : "#ef4444";

  // Build forecast label for multi-day
  const horizon = data.prediction.horizon || 1;
  const forecastLabel = horizon === 1 ? "Predicted (Tomorrow)" : `Predicted (+${horizon}d)`;

  if (priceChart) { priceChart.destroy(); priceChart = null; }

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [...dates, forecastLabel],
      datasets: [
        {
          label: `${data.ticker} Close`,
          data: closes,
          borderColor: "#3b82f6",
          backgroundColor: createGradient(ctx, "#3b82f6"),
          borderWidth: 1, 
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBorderWidth: 1,
          pointHoverBackgroundColor: "#3b82f6",
          pointHoverBorderColor: "#fff",
          tension: 0, 
          fill: true,
        },
        {
          label: forecastLabel,
          data: Array(closes.length - 1).fill(null).concat([closes[closes.length - 1], data.prediction.predicted_price]),
          borderColor: trendColor,
          backgroundColor: "transparent",
          borderWidth: 1,
          borderDash: [5, 4],
          pointRadius: (ctx2) => ctx2.dataIndex === closes.length ? 5 : 0,
          pointHoverRadius: (ctx2) => ctx2.dataIndex === closes.length ? 7 : 4,
          pointBackgroundColor: trendColor,
          pointBorderColor: "#111620",
          pointBorderWidth: 1,
          tension: 0,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600, easing: "easeOutCubic" },
      // Crosshair-style interaction
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: {
            color: "#4a5568",
            font: { family: "'Inter', sans-serif", size: 10 },
            boxWidth: 12, boxHeight: 2, padding: 12,
            usePointStyle: false,
          }
        },
        tooltip: {
          backgroundColor: "#111620",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          padding: { x: 12, y: 8 },
          titleColor: "#e8edf5",
          bodyColor: "#7c8a99",
          titleFont: { size: 11, weight: "700", family: "'JetBrains Mono', monospace" },
          bodyFont: { size: 11, family: "'JetBrains Mono', monospace" },
          displayColors: true,
          boxWidth: 8, boxHeight: 8,
          callbacks: {
            title: (items) => items[0].label,
            label: (ctx2) => {
              if (ctx2.raw === null) return null;
              const sign = ctx2.datasetIndex === 1 ? (isUp ? "↑" : "↓") : "";
              return `  ${ctx2.dataset.label}: ₹${Number(ctx2.raw).toLocaleString("en-IN", {minimumFractionDigits:2, maximumFractionDigits:2})} ${sign}`;
            }
          }
        },
        // Crosshair vertical line plugin (inline)
        crosshair: false
      },
      scales: {
        x: {
          border: { display: false },
          grid: {
            color: "rgba(255,255,255,0.02)",
            drawTicks: false,
          },
          ticks: {
            color: "#3d4a58",
            maxTicksLimit: 10,
            maxRotation: 0,
            font: { size: 9, family: "'Inter', sans-serif" },
            padding: 4,
          }
        },
        y: {
          position: "right",
          border: { display: false },
          grid: {
            color: (ctx2) => {
              return "rgba(255,255,255,0.02)";
            },
            drawTicks: false,
          },
          ticks: {
            color: "#3d4a58",
            count: 6,
            font: { size: 9, family: "'JetBrains Mono', monospace" },
            padding: 8,
            callback: (v) => `₹${v.toLocaleString("en-IN", {maximumFractionDigits:0})}`
          }
        }
      }
    }
  });

  // ── Crosshair vertical line via custom plugin ──────────────
  Chart.register({
    id: "crosshairLine",
    afterDraw(chart) {
      if (chart.tooltip._active && chart.tooltip._active.length) {
        const ctx2 = chart.ctx;
        const x = chart.tooltip._active[0].element.x;
        const y = chart.tooltip._active[0].element.y;
        const yTop = chart.scales.y.top;
        const yBot = chart.scales.y.bottom;
        ctx2.save();
        ctx2.beginPath();
        ctx2.moveTo(0, y);
        ctx2.lineTo(chart.width, y);
        ctx2.moveTo(x, yTop);
        ctx2.lineTo(x, yBot);
        ctx2.setLineDash([3, 3]);
        ctx2.lineWidth = 1;
        ctx2.strokeStyle = "rgba(255,255,255,0.15)";
        ctx2.stroke();
        ctx2.restore();
      }
    }
  });
}

/**
 * Create a gradient fill for the chart.
 */
function createGradient(ctx, color) {
  const gradient = ctx.getContext("2d").createLinearGradient(0, 0, 0, 280);
  gradient.addColorStop(0, color + "22");   // more subtle, 13% opacity
  gradient.addColorStop(1, color + "00");
  return gradient;
}

// ─────────────────────────────────────────────
// Favorite Button
// ─────────────────────────────────────────────
function setupFavoriteButton() {
  const btn = document.getElementById("favorite-btn");
  if (!btn) return;
  btn.addEventListener("click", toggleFavorite);
}

async function updateFavoriteButton(ticker) {
  const btn = document.getElementById("favorite-btn");
  if (!btn) return;

  try {
    const res = await fetch(`/is_favorite/${ticker}`);
    const data = await res.json();
    isFavorite = data.is_favorite;
    renderFavoriteBtn();
  } catch (_) {}
}

async function toggleFavorite() {
  if (!currentTicker) return;
  try {
    const res = await fetch("/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker: currentTicker })
    });
    const data = await res.json();
    isFavorite = data.status === "added";
    renderFavoriteBtn();
    showToast(
      isFavorite ? `${currentTicker} added to favorites ⭐` : `${currentTicker} removed from favorites`,
      "success"
    );
    // Reload favorite chips
    refreshFavoriteChips();
  } catch (_) {
    showToast("Failed to update favorites.", "error");
  }
}

function renderFavoriteBtn() {
  const btn = document.getElementById("favorite-btn");
  if (!btn) return;
  if (isFavorite) {
    btn.innerHTML = "⭐ Favorited";
    btn.className = "btn btn-success btn-sm";
  } else {
    btn.innerHTML = "☆ Add to Favorites";
    btn.className = "btn btn-secondary btn-sm";
  }
}

// ─────────────────────────────────────────────
// History Items (clicking refreshes search)
// ─────────────────────────────────────────────
function setupHistoryItems() {
  document.querySelectorAll(".history-item").forEach(item => {
    item.addEventListener("click", () => {
      const ticker = item.getAttribute("data-ticker");
      if (ticker) triggerSearch(ticker);
    });
  });
}

// ─────────────────────────────────────────────
// Favorite Chips (clicking refreshes search)
// ─────────────────────────────────────────────
function setupFavoriteChips() {
  document.querySelectorAll(".favorite-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const ticker = chip.getAttribute("data-ticker");
      if (ticker) triggerSearch(ticker);
    });
  });
}

async function refreshFavoriteChips() {
  // Reload the page to refresh sidebar (simple approach)
  // A more sophisticated approach would be AJAX-refresh
  window.location.reload();
}

// ─────────────────────────────────────────────
// Clear History
// ─────────────────────────────────────────────
function setupClearHistory() {
  const btn = document.getElementById("clear-history-btn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (!confirm("Clear all search history?")) return;
    try {
      await fetch("/history/delete", { method: "POST" });
      document.getElementById("history-list").innerHTML =
        `<div class="empty-state"><span class="empty-icon">🗂️</span><p>No history yet</p></div>`;
      showToast("History cleared.", "info");
    } catch (_) {
      showToast("Failed to clear history.", "error");
    }
  });
}

// ─────────────────────────────────────────────
// Trade Modal Logic
// ─────────────────────────────────────────────
function setupTradeModal() {
  const tradeBtn = document.getElementById("trade-modal-btn");
  const modal = document.getElementById("trade-modal");
  const closeBtn = document.getElementById("close-trade-modal");
  const submitBtn = document.getElementById("submit-trade-btn");
  const sharesInput = document.getElementById("trade-shares");
  const currentPriceEl = document.getElementById("trade-current-price");
  const totalCostEl = document.getElementById("trade-total-cost");

  if (!tradeBtn || !modal) return;

  let activePrice = 0;

  tradeBtn.addEventListener("click", () => {
    if (!currentTicker) return;
    const closeText = document.getElementById("stat-close").textContent;
    activePrice = parseFloat(closeText.replace(/[^0-9.]/g, "")) || 0;
    document.getElementById("trade-ticker-name").textContent = currentTicker;
    currentPriceEl.textContent = `₹${activePrice.toFixed(2)}`;
    sharesInput.value = 1;
    updateTotal();
    modal.classList.remove("hidden");
  });

  closeBtn.addEventListener("click", () => { modal.classList.add("hidden"); });

  const updateTotal = () => {
    const shares = parseInt(sharesInput.value) || 0;
    const total = shares * activePrice;
    totalCostEl.textContent = `₹${total.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}`;
  };
  sharesInput.addEventListener("input", updateTotal);

  submitBtn.addEventListener("click", async () => {
    const action = document.getElementById("trade-action").value;
    const shares = parseInt(sharesInput.value);

    if (shares <= 0 || isNaN(shares)) {
      showToast("Please enter a valid number of shares.", "error");
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";

    // ── SELL: use /trade endpoint directly ───────────────────
    if (action === "SELL") {
      try {
        const res = await fetch("/trade", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: currentTicker, action, shares })
        });
        const data = await res.json();
        if (data.error) {
          showToast(data.error, "error");
        } else {
          showToast(`✅ Sold ${data.shares} shares of ${data.ticker} @ ₹${data.price.toFixed(2)}!`, "success");
          modal.classList.add("hidden");
        }
      } catch (e) {
        showToast("Trade request failed.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Confirm Trade";
      }
      return;
    }

    // ── BUY: go through Razorpay payment ─────────────────────
    try {
      // Step 1: Create Razorpay order on server
      const orderRes  = await fetch("/create_trade_order", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ ticker: currentTicker, shares })
      });
      const orderData = await orderRes.json();

      if (orderData.error) {
        showToast(orderData.error, "error");
        submitBtn.disabled = false;
        submitBtn.innerText = "Confirm Trade";
        return;
      }

      // Step 2: Close our modal, open real Razorpay checkout
      modal.classList.add("hidden");

      const options = {
        key:         orderData.key,
        amount:      orderData.amount,
        currency:    "INR",
        name:        "StockSense AI",
        description: `Buy ${orderData.shares} × ${orderData.ticker}`,
        order_id:    orderData.order_id,
        notes:       { ticker: orderData.ticker, shares: String(orderData.shares) },
        theme:       { color: "#3b82f6" },
        config: {
          display: {
            blocks: {
              wallet: {
                name: "Pay via Wallet",
                instruments: [
                  { method: "wallet", wallets: ["paytm", "phonepe", "mobikwik", "freecharge", "jiomoney", "olamoney"] }
                ]
              },
              other: {
                name: "Other Payment Methods",
                instruments: [
                  { method: "upi" },
                  { method: "card" },
                  { method: "netbanking" }
                ]
              }
            },
            sequence: ["block.wallet", "block.other"],
            preferences: { show_default_blocks: false }
          }
        },
        handler: async function(response) {
          // Step 3: Verify & record trade
          const verRes = await fetch("/verify_and_trade", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({
              razorpay_order_id:   response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature:  response.razorpay_signature,
              ticker:  orderData.ticker,
              shares:  orderData.shares,
              price:   orderData.current_price
            })
          });
          const verData = await verRes.json();
          if (verData.success) {
            showToast(`✅ Bought ${verData.shares} shares of ${verData.ticker} @ ₹${verData.price.toFixed(2)}!`, "success");
          } else {
            showToast(verData.error || "Trade verification failed.", "error");
          }
        },
        modal: { ondismiss: () => {} }
      };

      const rzp = new Razorpay(options);
      rzp.open();

    } catch (e) {
      showToast("Failed to initiate payment. Please try again.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerText = "Confirm Trade";
    }
  });
}
