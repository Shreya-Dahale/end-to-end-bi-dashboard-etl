"""
Unit tests for Trend Analysis, Forecasting, and What-If simulation modules.
"""

import pandas as pd
import numpy as np
import pytest

from models.trend_analysis import compute_sales_trend
from models.forecasting import generate_forecast, prepare_monthly_series
from models.what_if import simulate_what_if_scenario


@pytest.fixture
def monthly_data():
    """Generates 36 months of realistic retail sales data."""
    dates = pd.date_range(start="2015-01-01", periods=36, freq="MS")
    # Linear upward trend + seasonality + random noise
    base = 20000.0
    trend = np.linspace(0, 15000, 36)
    seasonality = np.sin(np.linspace(0, 6 * np.pi, 36)) * 4000
    sales = base + trend + seasonality
    profit = sales * 0.12

    df = pd.DataFrame({
        "order_date": dates,
        "sales": sales,
        "profit": profit,
    })
    return df


def test_compute_sales_trend(monthly_data):
    """Test linear regression trend line calculation."""
    res = compute_sales_trend(monthly_data, date_col="order_date", value_col="sales")

    assert "slope" in res
    assert "r_squared" in res
    assert "p_value" in res
    assert "trend_direction" in res
    assert res["slope"] > 0  # positive slope expected
    assert 0.0 <= res["r_squared"] <= 1.0
    assert len(res["trend_df"]) == 36


def test_holt_winters_forecasting(monthly_data):
    """Test Holt-Winters Exponential Smoothing forecasting."""
    res = generate_forecast(
        monthly_data,
        model_type="Holt-Winters",
        test_months=6,
        forecast_horizon=4,
        date_col="order_date",
        value_col="sales",
    )

    assert res["model_name"] == "Holt-Winters Exponential Smoothing"
    assert "mae" in res["metrics"]
    assert "rmse" in res["metrics"]
    assert "mape" in res["metrics"]
    assert res["metrics"]["mae"] > 0

    # Check future predictions
    future_df = res["future_forecast_df"]
    assert len(future_df) == 4
    assert (future_df["forecast"] >= 0).all()
    assert (future_df["upper_bound"] >= future_df["lower_bound"]).all()


def test_arima_forecasting(monthly_data):
    """Test ARIMA forecasting model."""
    res = generate_forecast(
        monthly_data,
        model_type="ARIMA",
        test_months=6,
        forecast_horizon=3,
        date_col="order_date",
        value_col="sales",
    )

    assert "ARIMA" in res["model_name"]
    assert res["metrics"]["mae"] > 0
    future_df = res["future_forecast_df"]
    assert len(future_df) == 3


def test_what_if_simulation(monthly_data):
    """Test What-If scenario engine calculations."""
    sim_pos = simulate_what_if_scenario(
        monthly_data,
        growth_rate_pct=10.0,
        margin_expansion_pct=1.0,
        date_col="order_date",
        sales_col="sales",
        profit_col="profit",
    )

    base_sales = sim_pos["total_baseline_sales"]
    scen_sales = sim_pos["total_scenario_sales"]
    assert np.isclose(scen_sales, base_sales * 1.10, rtol=1e-3)
    assert sim_pos["total_sales_delta"] > 0
    assert sim_pos["pct_sales_change"] == 10.0

    # Negative growth scenario (-5%)
    sim_neg = simulate_what_if_scenario(
        monthly_data,
        growth_rate_pct=-5.0,
        margin_expansion_pct=0.0,
        date_col="order_date",
        sales_col="sales",
        profit_col="profit",
    )
    assert sim_neg["total_sales_delta"] < 0
    assert np.isclose(sim_neg["pct_sales_change"], -5.0, rtol=1e-3)
