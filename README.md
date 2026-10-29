# 📊 Enterprise BI Dashboard with Automated ETL Pipeline

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3.0+-003B57.svg)](https://www.sqlite.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.18+-3F4F75.svg)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end, production-ready Business Intelligence (BI) application built with **Python, Pandas, SQLite, Streamlit, Plotly, Statsmodels, and Scikit-learn**. 

Designed for enterprise-level retail analytics using the classic **Superstore** dataset, this project features an automated, idempotent ETL pipeline, an indexed SQLite relational database, interactive executive KPI dashboards, statistical trend analysis, time series forecasting (Holt-Winters and ARIMA), What-If scenario simulations, and Power BI integration.

---

## 🌟 Key Features

1. **Automated & Idempotent ETL Pipeline:**
   - Multi-encoding auto-detection (`Windows-1252`, `UTF-8`, `Latin-1`).
   - Supports both Excel (`.xlsx`, `.xls`) and CSV files.
   - Cleans missing values, validates business constraints (e.g. positive sales, valid discounts), and deduplicates records.
   - Feature engineering: derived fields including `shipping_days`, `profit_margin_pct`, `unit_price`, and temporal attributes (`order_year`, `order_month`, `year_month`).
   - Transactional SQLite database loader with safe rerun idempotency and execution audit logging in `etl_metadata`.
   - Exports Power BI-ready datasets (`data/cleaned_superstore.csv`) and deployment sample previews.

2. **Executive KPI Dashboard:**
   - Real-time KPI summary cards: Total Revenue, Net Profit, Profit Margin %, Total Orders, Units Sold, and Average Order Value (AOV).
   - Dual-axis monthly revenue and profit velocity charts.
   - Hierarchical category and sub-category performance treemaps.
   - Regional revenue and margin distribution matrix.
   - Top 10 revenue-generating products with margin color coding.

3. **Ordinary Least Squares (OLS) Trend Analysis:**
   - Regression line fitted on aggregate monthly sales: $\hat{y} = \beta_0 + \beta_1 x$.
   - Goodness-of-fit evaluation: Slope ($\$/\text{month}$), $R^2$ score, standard error, and hypothesis testing ($p$-value).
   - Automated business interpretation and growth trajectory classification.

4. **Predictive Time Series Forecasting:**
   - Dual-model support: **Holt-Winters Exponential Smoothing** (Level, Trend, Seasonality) and **ARIMA / SARIMAX**.
   - Chronological train/test split with holdout evaluation.
   - Accuracy evaluation metrics: **MAE**, **RMSE**, and **MAPE**.
   - Out-of-sample future projections for 3 to 6 months with shaded 95% confidence intervals.

5. **What-If Scenario Simulation Planner:**
   - Interactive sliders for sales growth ($-10\%$ to $+20\%$) and margin expansion ($-5\%$ to $+5\%$).
   - Real-time comparison between baseline and scenario-projected revenue and profit.
   - Incremental revenue delta visualizations and cumulative trajectory curves.
   - Scenario data export button.

6. **Power BI & SQLite Explorer:**
   - Live SQLite query runner directly inside the UI.
   - One-click CSV export of filtered records.
   - Direct Power BI integration instructions and ready-to-use DAX measures.

---

## 🏗️ Repository Architecture

```
end-to-end-bi-dashboard-etl/
├── .gitignore                      # Excludes venv, caches, databases, and private data
├── requirements.txt                # Python dependencies
├── README.md                       # Comprehensive project documentation
├── app.py                          # Multi-page interactive Streamlit BI application
├── etl/
│   ├── __init__.py
│   └── etl_pipeline.py             # Extract, Clean, Transform, Load, and Export
├── models/
│   ├── __init__.py
│   ├── trend_analysis.py           # OLS Regression and Goodness-of-fit metrics
│   ├── forecasting.py              # Holt-Winters & ARIMA forecasting engines
│   └── what_if.py                  # What-If scenario simulation engine
├── tests/
│   ├── test_etl.py                 # ETL lifecycle and validation tests
│   └── test_models.py              # Trend, forecast, and simulation unit tests
├── docs/
│   ├── ARCHITECTURE.md             # System architecture diagrams and schema
│   ├── POWER_BI_INTEGRATION.md     # Power BI Desktop connection and DAX guide
│   ├── PROJECT_REPORT.md           # College mini-project report outline
│   └── VIVA_QUESTIONS.md           # Viva voce technical questions and answers
├── data/
│   ├── cleaned_superstore.csv      # Exported cleaned dataset (Power BI compatible)
│   └── sample_superstore_preview.csv # Safe sample dataset for cloud deployment
├── database/
│   └── superstore_bi.db            # SQLite relational database with B-tree indexes
└── logs/
    └── etl.log                     # Automated execution audit trail
```

---

## 🚀 Quick Start Guide (Windows)

### 1. Prerequisites
Ensure Python 3.11+ and Git are installed. If needed, install Python and Git:
```powershell
winget install --id Python.Python.3.11 --scope user
```

### 2. Clone or Navigate to Project
```powershell
cd C:\Users\HOME-LAP\.gemini\antigravity\scratch\end-to-end-bi-dashboard-etl
```

### 3. Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run the ETL Pipeline
The pipeline will automatically locate your Superstore file on the Desktop (`Sample - Superstore.csv` or `.xlsx`), clean and validate records, and populate `database/superstore_bi.db`:
```powershell
python -m etl.etl_pipeline
```

### 5. Run the Automated Test Suite
Verify that all unit tests and validation checks pass:
```powershell
pytest -v
```

### 6. Launch the Streamlit BI Dashboard
Launch the dashboard on your local browser:
```powershell
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## 📊 Power BI Connection Instructions

1. Open **Microsoft Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Select `data/cleaned_superstore.csv` from this project.
4. Click **Load**.
5. All dates and calculated columns (`Shipping Days`, `Profit Margin %`, `Year-Month`) are formatted and ready. Refer to [`docs/POWER_BI_INTEGRATION.md`](docs/POWER_BI_INTEGRATION.md) for DAX formulas.

---

## ☁️ Deployment Guide (Streamlit Community Cloud)

1. Push your repository to your GitHub account:
   ```powershell
   git add .
   git commit -m "feat: complete end-to-end BI dashboard with ETL and forecasting"
   git push origin main
   ```
2. Visit **[share.streamlit.io](https://share.streamlit.io)** and sign in with your GitHub account.
3. Click **"New app"**.
4. Select your repository: `<your-username>/end-to-end-bi-dashboard-etl`.
5. Set Main file path: `app.py`.
6. Click **Deploy!**
   - The application automatically detects `requirements.txt` and uses `data/sample_superstore_preview.csv` as fallback when running in the cloud environment, ensuring privacy and persistence.

---

## 🧪 Test Verification Summary

| Test Suite | Module | Test Cases | Status |
|---|---|---|---|
| ETL Lifecycle | `tests/test_etl.py` | `test_etl_lifecycle` | ✅ PASSED |
| Data Validation | `tests/test_etl.py` | `test_missing_critical_fields_filtered` | ✅ PASSED |
| Trend Regression | `tests/test_models.py` | `test_compute_sales_trend` | ✅ PASSED |
| Holt-Winters Forecast | `tests/test_models.py` | `test_holt_winters_forecasting` | ✅ PASSED |
| ARIMA Forecast | `tests/test_models.py` | `test_arima_forecasting` | ✅ PASSED |
| What-If Simulation | `tests/test_models.py` | `test_what_if_simulation` | ✅ PASSED |

**Total:** 6 passed in 26.84s (100% pass rate).

---

## 🎓 Academic Presentation & Viva Voce
Consult [`docs/VIVA_QUESTIONS.md`](docs/VIVA_QUESTIONS.md) for in-depth technical explanations of:
- ETL vs direct file querying
- Idempotency and transactional database integrity
- OLS regression assumptions and $R^2$ / $p$-value interpretation
- Holt-Winters vs ARIMA stationarity and AIC criteria
- Power BI integration architecture
