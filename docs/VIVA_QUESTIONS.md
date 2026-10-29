# Viva Voce Questions & Model Answers

This document prepares you for technical viva examinations and presentations on the **End-to-End BI Dashboard with ETL** project.

---

### Section 1: ETL Pipeline & Database Design

#### Q1: What does ETL stand for, and why is an ETL pipeline necessary instead of directly querying the raw CSV/Excel file?
**Answer:**
ETL stands for **Extract, Transform, Load**.
Querying raw files directly presents major operational challenges:
1. **Performance:** Raw CSV/Excel parsing on every user request incurs disk I/O and CPU overhead.
2. **Data Quality:** Raw data contains inconsistent casing, corrupted strings, invalid ranges (e.g. negative sales), and missing values.
3. **Data Types:** Dates and numeric fields in raw files may be stored as strings without schema enforcement.
4. **Relational Indexing:** An ETL process normalizes and loads records into an indexed database (like SQLite), allowing instant slicing, filtering, and aggregation.

#### Q2: What is meant by "idempotent ETL execution" or "safe reruns"? How did you implement it?
**Answer:**
An **idempotent** pipeline can be executed multiple times without causing duplicate records, inconsistent states, or database corruption.
In our implementation:
- The ETL uses transactional schema recreation (`DROP TABLE IF EXISTS orders_staging`, atomic creation, or transactional truncate/replace).
- Primary surrogate keys and composite constraints prevent duplicate insertions.
- An `etl_metadata` audit table logs every execution with timestamp, records processed, duration, and status, allowing full observability.

#### Q3: Why did you create indexes in SQLite? Which columns were indexed and why?
**Answer:**
Without indexes, SQLite must perform a full table scan ($\mathcal{O}(N)$) for every filter or aggregation.
We constructed B-Tree indexes on:
- `order_date` and `year_month`: Fast temporal filtering and monthly time-series resampling.
- `region`, `category`, and `sub_category`: Instant evaluation of dimensional slices and multi-select filters.
- `customer_id` and `product_id`: Accelerating customer lifetime value and top-10 product aggregations.

---

### Section 2: Trend Analysis & Linear Regression

#### Q4: How is the trend line calculated, and what does the slope represent?
**Answer:**
The trend line is fitted using **Ordinary Least Squares (OLS) Linear Regression**:
$$\hat{y} = \beta_0 + \beta_1 x$$
- $x$: Time step index (month $0, 1, 2, \dots, n-1$).
- $y$: Aggregated monthly sales revenue.
- $\beta_1$ (Slope): Represents the average marginal growth in monthly revenue in dollars per month ($\Delta \text{Revenue} / \Delta \text{Month}$).
- $\beta_0$ (Intercept): Baseline starting revenue at time $x = 0$.

#### Q5: What is $R^2$ (Coefficient of Determination), and how do you interpret its value in your dashboard?
**Answer:**
$$R^2 = 1 - \frac{\text{SS}_{\text{res}}}{\text{SS}_{\text{tot}}} = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$
$R^2$ measures the proportion of total variance in monthly sales that is explained by the linear time trend.
In retail datasets with heavy seasonal swings (like holiday peaks in Q4), an $R^2$ of $0.30 - 0.60$ is normal, showing that while a secular upward trend exists, seasonal variations account for the remaining variance.

#### Q6: What does the p-value in trend analysis indicate?
**Answer:**
The p-value tests the null hypothesis $H_0: \beta_1 = 0$ (no linear trend).
A p-value $< 0.05$ allows us to reject the null hypothesis at the 95% confidence level, confirming that the upward sales momentum is statistically significant and not random noise.

---

### Section 3: Time Series Forecasting

#### Q7: Why is a chronological train/test split required instead of random k-fold cross-validation in time series?
**Answer:**
Time series data contains temporal dependencies (autocorrelation, trends, seasonality).
Randomly splitting data causes **data leakage** (future information leaking into the training set to predict the past).
A **chronological split** strictly trains on the historical past (e.g., first 40 months) and evaluates predictions on the subsequent chronological holdout test set (e.g., last 8 months), mirroring real-world forecasting.

#### Q8: What is Holt-Winters Exponential Smoothing, and what are its three components?
**Answer:**
Holt-Winters (Triple Exponential Smoothing) models time series with trend and seasonality using three smoothing equations:
1. **Level ($\ell_t$):** Smoothed baseline value of the series.
2. **Trend ($b_t$):** Expected rate of change from one period to the next.
3. **Seasonality ($s_t$):** Additive or multiplicative repeating cyclical fluctuations with period $m = 12$ months.

#### Q9: What does ARIMA stand for, and what do the parameters $(p, d, q)$ mean?
**Answer:**
ARIMA stands for **Auto-Regressive Integrated Moving Average**:
- **$p$ (Auto-Regressive order):** Number of lag observations included in the model.
- **$d$ (Degree of differencing):** Number of times raw observations are differenced to achieve stationarity.
- **$q$ (Moving Average order):** Size of the moving average window of residual errors.
- **Seasonal ARIMA (SARIMAX):** Adds seasonal terms $(P, D, Q)_s$ where $s=12$ for monthly seasonality.

#### Q10: How do you evaluate forecast accuracy using MAE, RMSE, and MAPE?
**Answer:**
- **MAE (Mean Absolute Error):** $\frac{1}{n}\sum |y_i - \hat{y}_i|$. Unbiased average magnitude of error in dollars.
- **RMSE (Root Mean Squared Error):** $\sqrt{\frac{1}{n}\sum (y_i - \hat{y}_i)^2}$. Penalizes large outlier errors more severely due to squaring.
- **MAPE (Mean Absolute Percentage Error):** $\frac{100\%}{n}\sum \left|\frac{y_i - \hat{y}_i}{y_i}\right|$. Scale-independent relative percentage error.

---

### Section 4: What-If Simulation & Business Applications

#### Q11: What is the purpose of the What-If analysis feature?
**Answer:**
What-If analysis enables executive scenario planning:
- By adjusting growth between $-10\%$ and $+20\%$, management can simulate both conservative contraction scenarios and aggressive marketing expansion.
- Incorporating margin expansion tests operational leverage: how a 1% reduction in unnecessary discounting impacts bottom-line net profit.
- It displays both monthly incremental deltas and cumulative revenue trajectory curves.

---

### Section 5: Architecture & Deployment

#### Q12: Why did you choose Streamlit over Flask or Django for this project?
**Answer:**
1. **Data Science Native:** Streamlit seamlessly integrates with Pandas DataFrames, NumPy arrays, Plotly figures, and Statsmodels objects.
2. **Reactive Execution:** State updates and slider adjustments re-render only the affected UI components.
3. **Speed of Delivery:** Allows building production-grade dashboards with complex interactive filters, caching (`@st.cache_data`), and downloads in Python without extensive frontend boilerplate.

#### Q13: How can Power BI connect to this project?
**Answer:**
1. **Direct CSV Import:** Power BI imports `data/cleaned_superstore.csv`, which has clean formatted dates and pre-calculated business features.
2. **ODBC SQLite Connection:** Power BI connects live to `database/superstore_bi.db` via the 64-bit SQLite ODBC driver.
