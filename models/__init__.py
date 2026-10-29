"""Models package for Superstore BI."""
from .trend_analysis import compute_sales_trend
from .forecasting import generate_forecast, fit_holt_winters, fit_arima
from .what_if import simulate_what_if_scenario

__all__ = [
    "compute_sales_trend",
    "generate_forecast",
    "fit_holt_winters",
    "fit_arima",
    "simulate_what_if_scenario",
]
