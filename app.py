"""
Executive BI Dashboard with ETL, Trend Analysis, Forecasting & What-If Simulation.
Technologies: Python, Pandas, SQLite, Streamlit, Plotly, Statsmodels, Scikit-learn.
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Ensure project modules are importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from etl.etl_pipeline import ETLPipeline, DATABASE_PATH, CLEANED_DATA_PATH
from models.trend_analysis import compute_sales_trend
from models.forecasting import generate_forecast
from models.what_if import simulate_what_if_scenario

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Enterprise BI Dashboard | Superstore Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- MODERN STYLING ---
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
    }
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    .kpi-title {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .kpi-value {
        color: #0f172a;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .kpi-delta {
        font-size: 0.85rem;
        font-weight: 600;
    }
    .delta-pos {
        color: #10b981;
    }
    .delta-neg {
        color: #ef4444;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #dbeafe;
        color: #1e40af;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- DATA ACCESS LAYER ---
@st.cache_data(ttl=3600, show_spinner="Loading data from SQLite Database...")
def load_data_from_db():
    """Load orders data from SQLite database, initializing ETL if missing."""
    if not DATABASE_PATH.exists():
        with st.spinner("Database not found. Executing initial ETL pipeline..."):
            pipeline = ETLPipeline()
            pipeline.run()

    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT * FROM orders"
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_date"] = pd.to_datetime(df["ship_date"])
    return df


@st.cache_data(ttl=3600)
def get_etl_metadata():
    """Fetch latest ETL execution metadata."""
    if not DATABASE_PATH.exists():
        return None
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        query = "SELECT * FROM etl_metadata ORDER BY id DESC LIMIT 5"
        meta = pd.read_sql_query(query, conn)
    except Exception:
        meta = None
    finally:
        conn.close()
    return meta


# Load Dataset
try:
    df_raw = load_data_from_db()
except Exception as e:
    st.error(f"Failed to load dataset: {e}")
    st.info("Attempting to run ETL pipeline now...")
    try:
        ETLPipeline().run()
        st.cache_data.clear()
        df_raw = load_data_from_db()
    except Exception as err:
        st.error(f"Could not initialize ETL: {err}")
        st.stop()


# --- SIDEBAR & FILTERS ---
st.sidebar.image("https://img.icons8.com/fluency/96/dashboard-layout.png", width=64)
st.sidebar.title("Superstore BI Hub")
st.sidebar.caption("End-to-End Enterprise Analytics & Forecasting")

# Navigation Selector
nav_page = st.sidebar.radio(
    "Navigation Menu",
    [
        "📊 Executive KPI Overview",
        "📈 Sales & Profit Deep-Dive",
        "📉 Trend & Regression Analysis",
        "🔮 Time Series Forecasting",
        "🎛️ What-If Scenario Planner",
        "🗺️ Regional & Customer Insights",
        "🗄️ ETL Pipeline & Data Explorer",
    ],
    index=0,
)

st.sidebar.divider()
st.sidebar.subheader("Filter Dimensions")

# Date Range Filter
min_date = df_raw["order_date"].min().date()
max_date = df_raw["order_date"].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Region Filter
all_regions = sorted(df_raw["region"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Region", options=all_regions, default=all_regions)

# Category Filter
all_categories = sorted(df_raw["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Category", options=all_categories, default=all_categories)

# Sub-Category Filter (Dynamic)
available_subcats = sorted(
    df_raw[df_raw["category"].isin(selected_categories)]["sub_category"].dropna().unique().tolist()
)
selected_subcats = st.sidebar.multiselect("Sub-Category", options=available_subcats, default=available_subcats)

# Segment Filter
all_segments = sorted(df_raw["segment"].dropna().unique().tolist())
selected_segments = st.sidebar.multiselect("Customer Segment", options=all_segments, default=all_segments)

# Apply Filters
start_d, end_d = min_date, max_date
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range

filter_mask = (
    (df_raw["order_date"].dt.date >= start_d)
    & (df_raw["order_date"].dt.date <= end_d)
    & (df_raw["region"].isin(selected_regions))
    & (df_raw["category"].isin(selected_categories))
    & (df_raw["sub_category"].isin(selected_subcats))
    & (df_raw["segment"].isin(selected_segments))
)

filtered_df = df_raw[filter_mask].copy()

# Sidebar Data Stats Pill
st.sidebar.divider()
st.sidebar.markdown(f"**Filtered Records:** `{len(filtered_df):,}` / `{len(df_raw):,}`")
if len(filtered_df) == 0:
    st.sidebar.error("No records match the selected filters. Please broaden filter criteria.")
    st.warning("No data available for the selected filters. Displaying empty dashboard.")
    st.stop()


# --- HELPER FUNCTIONS ---
def render_kpi_cards(df: pd.DataFrame):
    """Render top responsive executive KPI metric cards."""
    total_sales = df["sales"].sum()
    total_profit = df["profit"].sum()
    profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    total_orders = df["order_id"].nunique()
    total_quantity = df["quantity"].sum()
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Revenue</div>
            <div class="kpi-value">${total_sales:,.0f}</div>
            <div class="kpi-delta delta-pos">Avg Order: ${avg_order_value:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        profit_color = "delta-pos" if total_profit >= 0 else "delta-neg"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Net Profit</div>
            <div class="kpi-value ${profit_color}">${total_profit:,.0f}</div>
            <div class="kpi-delta {profit_color}">{total_profit / total_sales * 100:.1f}% Margin</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        margin_color = "delta-pos" if profit_margin >= 10 else "delta-neg"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Profit Margin</div>
            <div class="kpi-value ${margin_color}">{profit_margin:.2f}%</div>
            <div class="kpi-delta {margin_color}">Benchmark: 12.0%</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Orders</div>
            <div class="kpi-value">{total_orders:,}</div>
            <div class="kpi-delta delta-pos">Unique Customers: {df['customer_id'].nunique():,}</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Units Sold</div>
            <div class="kpi-value">{total_quantity:,}</div>
            <div class="kpi-delta delta-pos">Avg per Order: {total_quantity / total_orders:.1f}</div>
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: EXECUTIVE KPI OVERVIEW
# ==============================================================================
if nav_page == "📊 Executive KPI Overview":
    st.title("📊 Executive Performance Overview")
    st.caption("High-level executive metrics, sales velocity, profitability, and categorical health.")

    render_kpi_cards(filtered_df)

    col_left, col_right = st.columns([7, 5])

    with col_left:
        st.subheader("Monthly Sales & Profit Velocity")
        monthly_df = (
            filtered_df.set_index("order_date")
            .resample("MS")[["sales", "profit"]]
            .sum()
            .reset_index()
        )
        monthly_df["profit_margin"] = (monthly_df["profit"] / monthly_df["sales"] * 100).fillna(0)

        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
        fig_monthly.add_trace(
            go.Bar(
                x=monthly_df["order_date"],
                y=monthly_df["sales"],
                name="Sales ($)",
                marker_color="#3b82f6",
                opacity=0.85,
            ),
            secondary_y=False,
        )
        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["order_date"],
                y=monthly_df["profit"],
                name="Profit ($)",
                line=dict(color="#10b981", width=3),
                mode="lines+markers",
            ),
            secondary_y=False,
        )
        fig_monthly.add_trace(
            go.Scatter(
                x=monthly_df["order_date"],
                y=monthly_df["profit_margin"],
                name="Margin (%)",
                line=dict(color="#f59e0b", width=2, dash="dot"),
                mode="lines",
            ),
            secondary_y=True,
        )
        fig_monthly.update_layout(
            template="plotly_white",
            height=420,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10),
        )
        fig_monthly.update_yaxes(title_text="Sales & Profit ($)", secondary_y=False)
        fig_monthly.update_yaxes(title_text="Profit Margin (%)", secondary_y=True)
        st.plotly_chart(fig_monthly, use_container_width=True)

    with col_right:
        st.subheader("Revenue by Category & Sub-Category")
        cat_tree = (
            filtered_df.groupby(["category", "sub_category"])[["sales", "profit"]]
            .sum()
            .reset_index()
        )
        fig_treemap = px.treemap(
            cat_tree,
            path=["category", "sub_category"],
            values="sales",
            color="profit",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            title="",
        )
        fig_treemap.update_layout(height=420, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(fig_treemap, use_container_width=True)

    # Lower Grid: Regional Performance & Top Products
    c_lower1, c_lower2 = st.columns([5, 7])

    with c_lower1:
        st.subheader("Regional Revenue & Margin")
        reg_df = (
            filtered_df.groupby("region")[["sales", "profit"]]
            .sum()
            .reset_index()
        )
        reg_df["margin_pct"] = (reg_df["profit"] / reg_df["sales"] * 100).round(1)

        fig_reg = px.bar(
            reg_df,
            x="region",
            y="sales",
            color="margin_pct",
            text="margin_pct",
            color_continuous_scale="Viridis",
            labels={"sales": "Sales ($)", "region": "Region", "margin_pct": "Margin %"},
        )
        fig_reg.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_reg.update_layout(template="plotly_white", height=360, margin=dict(t=20, b=10))
        st.plotly_chart(fig_reg, use_container_width=True)

    with c_lower2:
        st.subheader("Top 10 Products by Sales")
        top_prods = (
            filtered_df.groupby("product_name")[["sales", "profit", "quantity"]]
            .sum()
            .reset_index()
            .sort_values(by="sales", ascending=True)
            .tail(10)
        )
        top_prods["margin_pct"] = (top_prods["profit"] / top_prods["sales"] * 100).round(1)

        fig_top = px.bar(
            top_prods,
            y="product_name",
            x="sales",
            orientation="h",
            color="profit",
            color_continuous_scale="Tropic",
            labels={"sales": "Sales ($)", "product_name": "Product", "profit": "Profit ($)"},
        )
        fig_top.update_layout(template="plotly_white", height=360, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_top, use_container_width=True)


# ==============================================================================
# PAGE 2: SALES & PROFITABILITY DEEP-DIVE
# ==============================================================================
elif nav_page == "📈 Sales & Profit Deep-Dive":
    st.title("📈 Sales & Profitability Deep-Dive")
    st.caption("Segment breakdown, sub-category profit matrix, discount analysis, and shipping efficiency.")

    render_kpi_cards(filtered_df)

    t1, t2 = st.tabs(["Sub-Category Matrix", "Discount vs Profit Sensitivity"])

    with t1:
        subcat_df = (
            filtered_df.groupby(["category", "sub_category"])[["sales", "profit", "quantity", "discount"]]
            .agg({"sales": "sum", "profit": "sum", "quantity": "sum", "discount": "mean"})
            .reset_index()
        )
        subcat_df["profit_margin_pct"] = (subcat_df["profit"] / subcat_df["sales"] * 100).round(2)
        subcat_df["avg_discount_pct"] = (subcat_df["discount"] * 100).round(1)

        fig_sub = px.scatter(
            subcat_df,
            x="sales",
            y="profit",
            size="quantity",
            color="category",
            hover_name="sub_category",
            text="sub_category",
            labels={"sales": "Total Sales ($)", "profit": "Total Profit ($)"},
            title="Sub-Category Performance Matrix (Bubble Size = Units Sold)",
        )
        fig_sub.add_hline(y=0, line_dash="dash", line_color="red")
        fig_sub.update_traces(textposition="top center")
        fig_sub.update_layout(template="plotly_white", height=480)
        st.plotly_chart(fig_sub, use_container_width=True)

        st.dataframe(
            subcat_df.sort_values(by="profit", ascending=False).style.format({
                "sales": "${:,.2f}",
                "profit": "${:,.2f}",
                "quantity": "{:,}",
                "profit_margin_pct": "{:.2f}%",
                "avg_discount_pct": "{:.1f}%",
            }),
            use_container_width=True,
        )

    with t2:
        st.subheader("Impact of Discount on Profitability")
        disc_bins = pd.cut(
            filtered_df["discount"],
            bins=[-0.01, 0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0],
            labels=["0%", "1-10%", "11-20%", "21-30%", "31-50%", "51-80%", "80%+"],
        )
        disc_analysis = (
            filtered_df.groupby(disc_bins)[["sales", "profit", "order_id"]]
            .agg({"sales": "sum", "profit": "sum", "order_id": "count"})
            .reset_index()
            .rename(columns={"discount": "Discount Band", "order_id": "Orders"})
        )
        disc_analysis["profit_margin"] = (disc_analysis["profit"] / disc_analysis["sales"] * 100).round(2)

        fig_disc = px.bar(
            disc_analysis,
            x="Discount Band",
            y="profit",
            color="profit_margin",
            color_continuous_scale="RdBu",
            text="profit_margin",
            title="Net Profit by Discount Band",
            labels={"profit": "Net Profit ($)", "profit_margin": "Margin %"},
        )
        fig_disc.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_disc.update_layout(template="plotly_white", height=420)
        st.plotly_chart(fig_disc, use_container_width=True)

        st.info(
            "💡 **Key Insight:** Orders with discounts greater than 20% routinely plunge into net negative territory. "
            "Re-evaluating promotional thresholds can immediately boost operating income."
        )


# ==============================================================================
# PAGE 3: TREND ANALYSIS & REGRESSION
# ==============================================================================
elif nav_page == "📉 Trend & Regression Analysis":
    st.title("📉 Trend Analysis & OLS Regression")
    st.caption("Ordinary Least Squares (OLS) regression on monthly revenue, goodness-of-fit metrics, and growth interpretation.")

    monthly_series = (
        filtered_df.set_index("order_date")
        .resample("MS")["sales"]
        .sum()
        .reset_index()
    )

    if len(monthly_series) < 3:
        st.warning("Insufficient monthly points in current filter to perform regression. Please broaden date range.")
        st.stop()

    trend_result = compute_sales_trend(monthly_series, date_col="order_date", value_col="sales")

    # Display Metrics Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Growth Velocity (Slope)", f"${trend_result['slope']:,.2f} / mo")
    m2.metric("Coefficient of Determination (R²)", f"{trend_result['r_squared']:.4f}")
    m3.metric("p-value (Significance)", f"{trend_result['p_value']:.4e}", "Statistically Significant" if trend_result['p_value'] < 0.05 else "Not Significant")
    m4.metric("Trend Classification", trend_result["trend_direction"])

    # Trend Plot
    trend_df = trend_result["trend_df"]
    fig_trend = go.Figure()

    fig_trend.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["actual_sales"],
            mode="lines+markers",
            name="Actual Monthly Sales",
            line=dict(color="#2563eb", width=2.5),
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=trend_df["date"],
            y=trend_df["trend_line"],
            mode="lines",
            name=f"OLS Trendline (y = {trend_result['slope']:,.2f}x + {trend_result['intercept']:,.2f})",
            line=dict(color="#ef4444", width=3, dash="dash"),
        )
    )

    fig_trend.update_layout(
        title="Monthly Sales Trend with OLS Fitted Regression Line",
        template="plotly_white",
        height=450,
        hovermode="x unified",
        xaxis_title="Timeline",
        yaxis_title="Revenue ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Explanation Callout
    st.markdown("### 📋 Statistical Summary & Business Explanation")
    st.success(f"**Interpretation:** {trend_result['interpretation']}")

    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
        st.markdown("**Regression Parameter Estimates:**")
        st.markdown(f"""
        - **Intercept ($):** `${trend_result['intercept']:,.2f}`
        - **Monthly Slope ($):** `${trend_result['slope']:,.2f}` per month
        - **Annualized Growth Run-rate:** `${trend_result['slope'] * 12:,.2f}` per year
        - **Standard Error:** `${trend_result['std_err']:,.2f}`
        """)
    with col_sub2:
        st.markdown("**Goodness of Fit Diagnostics:**")
        st.markdown(f"""
        - **R² Score:** `{trend_result['r_squared']:.4f}` ({trend_result['r_squared']*100:.2f}% of monthly revenue variance explained by time trend)
        - **Correlation Coefficient (r):** `{trend_result['r_value']:.4f}`
        - **Hypothesis Test (H₀: slope = 0):** `p = {trend_result['p_value']:.4e}` (Reject H₀ if p < 0.05)
        """)


# ==============================================================================
# PAGE 4: TIME SERIES FORECASTING
# ==============================================================================
elif nav_page == "🔮 Time Series Forecasting":
    st.title("🔮 Predictive Time Series Forecasting")
    st.caption("Chronological train/test split evaluation, Holt-Winters / ARIMA models, and 3-6 month future outlook.")

    monthly_sales = (
        filtered_df.set_index("order_date")
        .resample("MS")["sales"]
        .sum()
        .reset_index()
    )

    if len(monthly_sales) < 18:
        st.warning(
            f"Forecasting requires at least 18 continuous monthly observations (currently {len(monthly_sales)}). "
            "Please broaden your filters to view full forecasting."
        )
        st.stop()

    # Controls
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
    with ctrl_col1:
        selected_model = st.selectbox(
            "Forecasting Algorithm",
            ["Holt-Winters Exponential Smoothing", "ARIMA / SARIMAX"],
            index=0,
        )
    with ctrl_col2:
        test_window = st.slider(
            "Evaluation Test Window (Months)",
            min_value=4,
            max_value=12,
            value=8,
            help="Chronological holdout sample size for MAE/RMSE calculation.",
        )
    with ctrl_col3:
        horizon = st.slider(
            "Future Forecast Horizon (Months)",
            min_value=3,
            max_value=6,
            value=6,
            help="Number of future months to project into the future.",
        )

    # Run Forecasting
    model_key = "arima" if "ARIMA" in selected_model else "holt-winters"
    with st.spinner("Fitting time series model and calculating prediction intervals..."):
        try:
            fc_res = generate_forecast(
                filtered_df,
                model_type=model_key,
                test_months=test_window,
                forecast_horizon=horizon,
                date_col="order_date",
                value_col="sales",
            )
        except Exception as err:
            st.error(f"Forecasting calculation failed: {err}")
            st.stop()

    # Metrics Row
    metrics = fc_res["metrics"]
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Selected Model", fc_res["model_name"])
    e2.metric("Mean Absolute Error (MAE)", f"${metrics['mae']:,.2f}")
    e3.metric("Root Mean Squared Error (RMSE)", f"${metrics['rmse']:,.2f}")
    e4.metric("Mean Absolute % Error (MAPE)", f"{metrics['mape']:.2f}%")

    # Evaluation Plot: In-sample Holdout Test Set
    st.subheader("1. In-Sample Train/Test Split Evaluation")
    eval_df = fc_res["test_evaluation_df"]
    full_series = fc_res["full_series"]
    train_series = full_series.iloc[:-test_window]

    fig_eval = go.Figure()
    fig_eval.add_trace(
        go.Scatter(
            x=train_series.index,
            y=train_series.values,
            mode="lines+markers",
            name="Training Set (History)",
            line=dict(color="#64748b", width=2),
        )
    )
    fig_eval.add_trace(
        go.Scatter(
            x=eval_df["date"],
            y=eval_df["actual"],
            mode="lines+markers",
            name="Actual Holdout Test Sales",
            line=dict(color="#2563eb", width=3),
        )
    )
    fig_eval.add_trace(
        go.Scatter(
            x=eval_df["date"],
            y=eval_df["predicted"],
            mode="lines+markers",
            name=f"Model Predicted (MAE: ${metrics['mae']:,.0f})",
            line=dict(color="#f59e0b", width=3, dash="dash"),
        )
    )
    fig_eval.update_layout(
        template="plotly_white",
        height=380,
        hovermode="x unified",
        xaxis_title="Timeline",
        yaxis_title="Revenue ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_eval, use_container_width=True)

    # Future Forecast Plot: Out-of-sample Projection
    st.subheader(f"2. Future {horizon}-Month Out-of-Sample Projections (with 95% Confidence Bounds)")
    future_df = fc_res["future_forecast_df"]

    fig_future = go.Figure()
    fig_future.add_trace(
        go.Scatter(
            x=full_series.index,
            y=full_series.values,
            mode="lines+markers",
            name="Historical Sales",
            line=dict(color="#1e293b", width=2),
        )
    )
    fig_future.add_trace(
        go.Scatter(
            x=future_df["date"],
            y=future_df["forecast"],
            mode="lines+markers",
            name=f"{horizon}-Month Projected Outlook",
            line=dict(color="#10b981", width=3.5),
        )
    )
    # Upper & Lower bounds
    fig_future.add_trace(
        go.Scatter(
            x=future_df["date"].tolist() + future_df["date"].tolist()[::-1],
            y=future_df["upper_bound"].tolist() + future_df["lower_bound"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            showlegend=True,
            name="95% Confidence Interval",
        )
    )
    fig_future.update_layout(
        template="plotly_white",
        height=420,
        hovermode="x unified",
        xaxis_title="Timeline",
        yaxis_title="Revenue ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_future, use_container_width=True)

    # Future Predictions Table
    st.subheader("Projected Numbers Breakdown")
    disp_future = future_df.copy()
    disp_future["Date"] = disp_future["date"].dt.strftime("%B %Y")
    disp_future["Projected Sales"] = disp_future["forecast"].apply(lambda v: f"${v:,.2f}")
    disp_future["95% Lower Bound"] = disp_future["lower_bound"].apply(lambda v: f"${v:,.2f}")
    disp_future["95% Upper Bound"] = disp_future["upper_bound"].apply(lambda v: f"${v:,.2f}")

    st.dataframe(
        disp_future[["Date", "Projected Sales", "95% Lower Bound", "95% Upper Bound"]],
        use_container_width=True,
    )


# ==============================================================================
# PAGE 5: WHAT-IF SCENARIO PLANNER
# ==============================================================================
elif nav_page == "🎛️ What-If Scenario Planner":
    st.title("🎛️ What-If Scenario Simulation Planner")
    st.caption("Adjust revenue growth (-10% to +20%) and margin factors to stress-test financial projections against baseline.")

    monthly_summary = (
        filtered_df.set_index("order_date")
        .resample("MS")[["sales", "profit"]]
        .sum()
        .reset_index()
    )

    # Interactive Sliders
    sc_col1, sc_col2 = st.columns(2)
    with sc_col1:
        growth_slider = st.slider(
            "Adjustable Sales Growth Scenario (%)",
            min_value=-10.0,
            max_value=20.0,
            value=8.0,
            step=1.0,
            help="Simulate top-line sales contraction (-10%) to aggressive expansion (+20%).",
        )
    with sc_col2:
        margin_slider = st.slider(
            "Margin Expansion / Contraction (points)",
            min_value=-5.0,
            max_value=5.0,
            value=1.0,
            step=0.5,
            help="Simulate operational leverage: pricing or discount optimization.",
        )

    # Run Simulation
    sim = simulate_what_if_scenario(
        monthly_summary,
        growth_rate_pct=growth_slider,
        margin_expansion_pct=margin_slider,
        date_col="order_date",
        sales_col="sales",
        profit_col="profit",
    )

    # Scenario Metric Cards
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Baseline Revenue",
        f"${sim['total_baseline_sales']:,.0f}",
        "Historic Basis",
    )
    sales_delta_color = "normal" if sim["total_sales_delta"] >= 0 else "inverse"
    k2.metric(
        f"Scenario Revenue ({growth_slider:+0.1f}%)",
        f"${sim['total_scenario_sales']:,.0f}",
        f"{sim['total_sales_delta']:+,.0f} ({sim['pct_sales_change']:+.1f}%)",
        delta_color=sales_delta_color,
    )
    k3.metric(
        "Baseline Profit",
        f"${sim['total_baseline_profit']:,.0f}",
        f"{sim['total_baseline_profit']/sim['total_baseline_sales']*100:.1f}% Margin",
    )
    profit_delta_color = "normal" if sim["total_profit_delta"] >= 0 else "inverse"
    k4.metric(
        f"Scenario Profit ({sim['scenario_margin_pct']:.1f}% Margin)",
        f"${sim['total_scenario_profit']:,.0f}",
        f"{sim['total_profit_delta']:+,.0f} ({sim['pct_profit_change']:+.1f}%)",
        delta_color=profit_delta_color,
    )

    # Comparative Plot
    scenario_df = sim["scenario_df"]
    fig_sim = go.Figure()
    fig_sim.add_trace(
        go.Scatter(
            x=scenario_df["order_date"],
            y=scenario_df["sales"],
            mode="lines+markers",
            name="Baseline Sales ($)",
            line=dict(color="#64748b", width=2.5),
        )
    )
    fig_sim.add_trace(
        go.Scatter(
            x=scenario_df["order_date"],
            y=scenario_df["scenario_sales"],
            mode="lines+markers",
            name=f"Scenario Projected Sales ({growth_slider:+0.1f}%)",
            line=dict(color="#3b82f6", width=3),
        )
    )
    fig_sim.add_trace(
        go.Bar(
            x=scenario_df["order_date"],
            y=scenario_df["sales_delta"],
            name="Incremental Revenue Delta",
            marker_color="#10b981" if growth_slider >= 0 else "#ef4444",
            opacity=0.6,
        )
    )
    fig_sim.update_layout(
        title=f"Monthly Trajectory Comparison: Baseline vs {growth_slider:+0.1f}% Scenario",
        template="plotly_white",
        height=450,
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="Revenue ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_sim, use_container_width=True)

    # Cumulative Trajectory
    st.subheader("Cumulative Revenue Trajectory")
    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Scatter(
            x=scenario_df["order_date"],
            y=scenario_df["cum_baseline_sales"],
            mode="lines",
            name="Baseline Cumulative Revenue",
            line=dict(color="#64748b", width=2, dash="dash"),
        )
    )
    fig_cum.add_trace(
        go.Scatter(
            x=scenario_df["order_date"],
            y=scenario_df["cum_scenario_sales"],
            mode="lines",
            name="Scenario Cumulative Revenue",
            line=dict(color="#10b981", width=3),
        )
    )
    fig_cum.update_layout(
        template="plotly_white",
        height=380,
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="Cumulative Sales ($)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_cum, use_container_width=True)

    # Data export for this scenario
    st.download_button(
        label="📥 Download Scenario Simulation Data (CSV)",
        data=scenario_df.to_csv(index=False).encode("utf-8"),
        file_name=f"scenario_simulation_growth_{growth_slider}pct.csv",
        mime="text/csv",
    )


# ==============================================================================
# PAGE 6: REGIONAL & CUSTOMER INSIGHTS
# ==============================================================================
elif nav_page == "🗺️ Regional & Customer Insights":
    st.title("🗺️ Regional & Customer Demographic Insights")
    st.caption("State breakdown, customer lifetime value, shipping duration efficiency, and segment matrices.")

    render_kpi_cards(filtered_df)

    tab_geo, tab_cust, tab_ship = st.tabs(["State-Level Heatmap", "Top Customers", "Shipping Logistics"])

    with tab_geo:
        state_df = (
            filtered_df.groupby("state")[["sales", "profit", "order_id"]]
            .agg({"sales": "sum", "profit": "sum", "order_id": "count"})
            .reset_index()
            .sort_values(by="sales", ascending=False)
        )
        state_df["margin_pct"] = (state_df["profit"] / state_df["sales"] * 100).round(2)

        fig_states = px.bar(
            state_df.head(20),
            x="sales",
            y="state",
            orientation="h",
            color="profit",
            color_continuous_scale="RdBu",
            labels={"sales": "Sales ($)", "state": "State", "profit": "Profit ($)"},
            title="Top 20 States by Revenue & Net Profit",
        )
        fig_states.update_layout(template="plotly_white", height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_states, use_container_width=True)

    with tab_cust:
        cust_df = (
            filtered_df.groupby(["customer_id", "customer_name", "segment"])[["sales", "profit", "order_id"]]
            .agg({"sales": "sum", "profit": "sum", "order_id": "count"})
            .reset_index()
            .sort_values(by="sales", ascending=False)
            .rename(columns={"order_id": "Orders", "sales": "Lifetime Sales", "profit": "Lifetime Profit"})
        )
        cust_df["Margin %"] = (cust_df["Lifetime Profit"] / cust_df["Lifetime Sales"] * 100).round(2)

        st.dataframe(
            cust_df.head(25).style.format({
                "Lifetime Sales": "${:,.2f}",
                "Lifetime Profit": "${:,.2f}",
                "Orders": "{:,}",
                "Margin %": "{:.2f}%",
            }),
            use_container_width=True,
        )

    with tab_ship:
        ship_df = (
            filtered_df.groupby("ship_mode")[["shipping_days", "sales", "profit"]]
            .agg({"shipping_days": "mean", "sales": "sum", "profit": "sum"})
            .reset_index()
        )
        ship_df["shipping_days"] = ship_df["shipping_days"].round(1)

        c_s1, c_s2 = st.columns(2)
        with c_s1:
            fig_sm = px.bar(
                ship_df,
                x="ship_mode",
                y="shipping_days",
                text="shipping_days",
                color="ship_mode",
                title="Average Shipping Duration (Days)",
            )
            fig_sm.update_traces(texttemplate="%{text} days", textposition="outside")
            fig_sm.update_layout(template="plotly_white", height=380)
            st.plotly_chart(fig_sm, use_container_width=True)
        with c_s2:
            fig_sm2 = px.pie(
                ship_df,
                names="ship_mode",
                values="sales",
                title="Revenue Share by Ship Mode",
                hole=0.4,
            )
            fig_sm2.update_layout(template="plotly_white", height=380)
            st.plotly_chart(fig_sm2, use_container_width=True)


# ==============================================================================
# PAGE 7: ETL PIPELINE & DATA EXPLORER
# ==============================================================================
elif nav_page == "🗄️ ETL Pipeline & Data Explorer":
    st.title("🗄️ ETL Pipeline Health & SQLite Explorer")
    st.caption("Pipeline orchestration, audit trail, live SQLite query console, and Power BI integration guide.")

    # ETL Controls
    col_e1, col_e2 = st.columns([8, 4])
    with col_e1:
        st.subheader("Pipeline Health & Operational Controls")
        st.write(
            "The ETL engine extracts from Excel/CSV, executes schema enforcement and deduplication, "
            "transforms derived temporal features, and indexes records into SQLite."
        )
    with col_e2:
        if st.button("🚀 Trigger ETL Pipeline Rerun", use_container_width=True, type="primary"):
            with st.spinner("Executing ETL Pipeline..."):
                try:
                    pipeline = ETLPipeline()
                    results = pipeline.run()
                    st.cache_data.clear()
                    st.success(f"ETL completed! Loaded {results['records_loaded']:,} records in {results['total_duration_seconds']:.2f}s.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"ETL rerun failed: {ex}")

    # Audit Trail
    meta_df = get_etl_metadata()
    if meta_df is not None and not meta_df.empty:
        st.subheader("ETL Execution Audit Trail (SQLite Metadata)")
        st.dataframe(meta_df, use_container_width=True)

    # Live SQLite Query Console
    st.divider()
    st.subheader("Interactive SQLite Query Console")
    default_sql = "SELECT category, count(*) AS order_count, round(sum(sales),2) AS total_sales, round(sum(profit),2) AS total_profit FROM orders GROUP BY category ORDER BY total_sales DESC;"
    user_query = st.text_area("Write SQL Query:", value=default_sql, height=100)

    if st.button("Run SQL Query", type="secondary"):
        conn = sqlite3.connect(DATABASE_PATH)
        try:
            sql_res = pd.read_sql_query(user_query, conn)
            st.dataframe(sql_res, use_container_width=True)
            st.caption(f"Query returned {len(sql_res)} records.")
        except Exception as q_err:
            st.error(f"SQL Execution Error: {q_err}")
        finally:
            conn.close()

    # Data Download Section
    st.divider()
    st.subheader("Data Export & Power BI Direct Integration")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("**Download Filtered Dataset:**")
        csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Current Filtered Data (CSV)",
            data=csv_bytes,
            file_name=f"superstore_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_d2:
        st.markdown("**Download Power BI Ready Clean Dataset:**")
        if CLEANED_DATA_PATH.exists():
            with open(CLEANED_DATA_PATH, "rb") as f:
                cleaned_bytes = f.read()
            st.download_button(
                label="📊 Download Power BI Dataset (cleaned_superstore.csv)",
                data=cleaned_bytes,
                file_name="cleaned_superstore.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Run ETL to generate Power BI export.")

    with st.expander("📖 Step-by-Step Instructions: Connecting Power BI to SQLite or CSV"):
        st.markdown("""
        ### Connecting to this Project in Power BI Desktop:
        1. **Option A (Instant CSV Import):**
           - Open **Power BI Desktop**.
           - Click **Get Data** -> **Text/CSV**.
           - Browse to: `end-to-end-bi-dashboard-etl/data/cleaned_superstore.csv`.
           - Click **Load**. All types, dates, and calculated columns (`Shipping Days`, `Profit Margin %`, `Year-Month`) are ready out-of-the-box.
        2. **Option B (Direct SQLite ODBC Connection):**
           - Install the free **SQLite ODBC Driver** (e.g. from `ch-werner.de/sqliteodbc`).
           - Open Power BI -> **Get Data** -> **ODBC**.
           - In the connection string, enter: `Driver={SQLite3 ODBC Driver};Database=<PATH_TO_PROJECT>\database\superstore_bi.db`.
           - Select the `orders` table. Now your Power BI dashboard queries the SQLite database directly!
        3. **DAX Measures Included:**
           - `Total Sales = SUM(orders[Sales])`
           - `Total Profit = SUM(orders[Profit])`
           - `Profit Margin = DIVIDE([Total Profit], [Total Sales], 0)`
           - `Order Count = DISTINCTCOUNT(orders[Order ID])`
        """)

# --- FOOTER ---
st.markdown("---")
st.caption(
    "🎓 **College Mini-Project:** End-to-End BI Dashboard with ETL, OLS Trend Regression, "
    "ARIMA/Holt-Winters Forecasting, and What-If Simulation. Built with Python, Pandas, SQLite, Streamlit & Plotly."
)
