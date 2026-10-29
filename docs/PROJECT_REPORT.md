# College Mini-Project Report

## Project Title
**End-to-End Business Intelligence (BI) Dashboard with Automated ETL Pipeline, Statistical Trend Analysis, and Predictive Time Series Forecasting**

---

## Abstract
Modern enterprises generate massive volumes of transactional data across disparate sources. Transforming this raw operational data into actionable strategic insights requires an automated, resilient Extract-Transform-Load (ETL) pipeline, a performant relational repository, and interactive analytical interfaces. This project presents an end-to-end Business Intelligence solution utilizing the classic enterprise Superstore retail dataset. The system features an automated Python-based ETL pipeline that parses CSV/Excel data, handles encodings, enforces data integrity constraints, engineers temporal and profitability dimensions, and loads records into an indexed SQLite database. An interactive Streamlit dashboard delivers executive KPI monitoring, Ordinary Least Squares (OLS) regression trend analysis, dual-algorithm time series forecasting (Holt-Winters Exponential Smoothing and ARIMA/SARIMAX) with chronological train/test validation, and an interactive What-If scenario simulation planner. The project also provides cleaned data exports and direct integration pathways for Microsoft Power BI.

---

## 1. Introduction
### 1.1 Background
Business Intelligence (BI) bridges the gap between raw transactional data and executive decision-making. Conventional spreadsheets suffer from scalability limitations, lack of automated validation, and static charting capabilities.
### 1.2 Problem Statement
Enterprises require an automated, reproducible workflow that can:
1. Ingest raw spreadsheets without human error or data corruption.
2. Store validated transactions in a lightweight, zero-configuration indexed relational database.
3. Perform statistical regression to quantify revenue momentum.
4. Forecast near-term financial demand with bounded confidence intervals.
5. Simulate strategic price/growth scenarios interactively.
### 1.3 Objectives
- Design and implement an idempotent ETL pipeline with audit trail logging.
- Structure an indexed SQLite relational data store.
- Implement OLS regression with $R^2$ goodness-of-fit and hypothesis testing.
- Evaluate Holt-Winters vs. ARIMA forecasting using MAE, RMSE, and MAPE.
- Build an interactive web dashboard using Streamlit and Plotly.

---

## 2. Theoretical Foundations & Technology Stack
- **Python 3.11:** Core execution runtime.
- **Pandas & NumPy:** In-memory vectorization, time series resampling, and data manipulation.
- **SQLite:** Serverless, ACID-compliant relational storage engine with B-tree indexing.
- **Statsmodels & Scikit-learn:** Time series modeling (ARIMA, Holt-Winters) and linear regression.
- **Streamlit & Plotly:** Reactive web architecture and interactive data visualizations.
- **Microsoft Power BI:** Enterprise report design and DAX calculation compatibility.

---

## 3. System Architecture & Methodology
### 3.1 ETL Pipeline (Extract -> Transform -> Load)
- **Extraction:** Multi-encoding detection (Windows-1252, UTF-8, Latin-1) and support for CSV and multi-sheet Excel workbooks.
- **Transformation:**
  - Whitespace stripping and normalization.
  - Strict date parsing (`Order Date`, `Ship Date`).
  - Validation: enforcing strictly positive Sales and Quantities, Discount bounds $[0, 1]$, and fulfillment duration validation ($\text{Ship Date} \ge \text{Order Date}$).
  - Feature Engineering: $\text{Shipping Days}$, $\text{Profit Margin } (\%)$, $\text{Unit Price}$, $\text{Year-Month}$, and temporal categorizations.
- **Loading:** Idempotent schema recreation, bulk parameterized record insertion, and B-tree index construction on critical query dimensions (`order_date`, `region`, `category`, `sub_category`).

### 3.2 Statistical Trend Analysis
- Modeled as $y = \beta_0 + \beta_1 x + \epsilon$, where $x$ represents monthly chronological index and $y$ represents aggregate monthly sales.
- Metrics evaluated: Slope ($\beta_1$), Coefficient of Determination ($R^2$), and two-sided p-value for statistical significance test ($H_0: \beta_1 = 0$).

### 3.3 Predictive Forecasting
- **Holt-Winters Exponential Smoothing:** Captures level, linear trend, and 12-month additive seasonal cycles.
- **ARIMA / SARIMAX:** Auto-Regressive Integrated Moving Average incorporating seasonal differencing.
- **Validation:** Chronological split (80% train / 20% holdout test) evaluated on MAE, RMSE, and MAPE.

### 3.4 What-If Scenario Modeling
- Simulation engine parameterized by growth rate $g \in [-10\%, +20\%]$ and operating margin delta $\Delta m \in [-5\%, +5\%]$.

---

## 4. Experimental Results & Performance Evaluation
- **Dataset Size:** 9,994 transactional records across 4 contiguous calendar years (48 months: 2014–2017).
- **ETL Performance:** Sub-second execution ($\approx 0.50$ seconds) with zero dropped valid records.
- **Forecasting Performance:**
  - Evaluated on holdout test window of 8 months.
  - Holt-Winters captured seasonal December holiday spikes effectively.
  - MAE and RMSE metrics provided quantitative benchmarks for model selection.
- **Unit Testing:** 100% test pass rate across 6 automated test suites covering extraction, transformation, regression, forecasting, and simulation.

---

## 5. Conclusion & Future Enhancements
The developed BI system provides an end-to-end automated platform for retail enterprise intelligence. Future work can extend this architecture to include:
- Cloud warehouse connectivity (PostgreSQL / Snowflake / BigQuery).
- Real-time streaming data ingestion with Apache Kafka.
- Customer segmentation using Unsupervised Machine Learning (K-Means / RFM analysis).

---

## 6. References
1. Hyndman, R.J., & Athanasopoulos, G. (2018). *Forecasting: principles and practice*, 2nd edition, OTexts: Melbourne, Australia.
2. McKinney, W. (2010). *Data Structures for Statistical Computing in Python*. Proceedings of the 9th Python in Science Conference.
3. Box, G.E., Jenkins, G.M., Reinsel, G.C., & Ljung, G.M. (2015). *Time series analysis: forecasting and control*. John Wiley & Sons.
