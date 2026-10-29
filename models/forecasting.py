"""
Forecasting Module for Superstore Time Series.
Supports Holt-Winters Exponential Smoothing and ARIMA/SARIMAX models,
chronological train/test evaluation (MAE, RMSE, MAPE),
and 3-6 month future forecasting with confidence intervals.
"""

from typing import Dict, Any, Tuple, Optional
import warnings
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")


def prepare_monthly_series(df: pd.DataFrame, date_col: str = "order_date", value_col: str = "sales") -> pd.Series:
    """Aggregates transactional data to monthly sales with Month-Start frequency."""
    df_copy = df.copy()
    if not isinstance(df_copy.index, pd.DatetimeIndex):
        if date_col in df_copy.columns:
            df_copy[date_col] = pd.to_datetime(df_copy[date_col])
            df_copy = df_copy.set_index(date_col)
        else:
            raise ValueError(f"Date column '{date_col}' not found.")

    monthly = df_copy[value_col].resample("MS").sum()
    # Fill any missing intermediate month with 0
    monthly = monthly.asfreq("MS").fillna(0.0)
    return monthly


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, and MAPE."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    # Safe MAPE avoiding division by zero
    non_zero = y_true != 0
    if np.any(non_zero):
        mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100)
    else:
        mape = 0.0
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2),
    }


def fit_holt_winters(
    series: pd.Series,
    test_months: int = 8,
    forecast_horizon: int = 6,
) -> Dict[str, Any]:
    """
    Fits Holt-Winters Exponential Smoothing with chronological train/test split.
    """
    n = len(series)
    if n < test_months + 12:
        raise ValueError(f"Need at least {test_months + 12} months of data for Holt-Winters with annual seasonality.")

    train = series.iloc[:-test_months]
    test = series.iloc[-test_months:]

    # Train model on training set for evaluation
    try:
        model_eval = ExponentialSmoothing(
            train,
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        ).fit()
        pred_test = model_eval.forecast(test_months)
    except Exception:
        # Fallback to simple additive trend if seasonal fitting encounters singular matrix
        model_eval = ExponentialSmoothing(
            train,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        ).fit()
        pred_test = model_eval.forecast(test_months)

    metrics = evaluate_forecast(test.values, pred_test.values)

    # Fit on FULL series for future forecasting
    try:
        full_model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal="add",
            seasonal_periods=12,
            initialization_method="estimated",
        ).fit()
    except Exception:
        full_model = ExponentialSmoothing(
            series,
            trend="add",
            seasonal=None,
            initialization_method="estimated",
        ).fit()

    future_pred = full_model.forecast(forecast_horizon)
    # Estimate standard error of residuals for confidence bands
    resid = full_model.resid
    std_err = float(np.std(resid)) if len(resid) > 0 else 5000.0

    future_dates = pd.date_range(start=series.index[-1] + pd.DateOffset(months=1), periods=forecast_horizon, freq="MS")
    future_df = pd.DataFrame({
        "date": future_dates,
        "forecast": np.maximum(future_pred.values, 0),
        "lower_bound": np.maximum(future_pred.values - 1.96 * std_err, 0),
        "upper_bound": future_pred.values + 1.96 * std_err,
    })

    test_df = pd.DataFrame({
        "date": test.index,
        "actual": test.values,
        "predicted": np.maximum(pred_test.values, 0),
    })

    return {
        "model_name": "Holt-Winters Exponential Smoothing",
        "metrics": metrics,
        "test_evaluation_df": test_df,
        "future_forecast_df": future_df,
        "full_series": series,
        "train_len": len(train),
        "test_len": len(test),
    }


def fit_arima(
    series: pd.Series,
    test_months: int = 8,
    forecast_horizon: int = 6,
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (1, 0, 0, 12),
) -> Dict[str, Any]:
    """
    Fits ARIMA / SARIMAX model with chronological train/test split.
    """
    n = len(series)
    if n < test_months + 6:
        raise ValueError(f"Need at least {test_months + 6} months of data for ARIMA.")

    train = series.iloc[:-test_months]
    test = series.iloc[-test_months:]

    # Train model on training set
    try:
        model_eval = ARIMA(train, order=order, seasonal_order=seasonal_order)
        fit_eval = model_eval.fit()
        pred_test = fit_eval.forecast(steps=test_months)
    except Exception:
        # Fallback to non-seasonal ARIMA(1,1,1)
        model_eval = ARIMA(train, order=(1, 1, 1))
        fit_eval = model_eval.fit()
        pred_test = fit_eval.forecast(steps=test_months)

    metrics = evaluate_forecast(test.values, pred_test.values)

    # Fit on FULL series for future forecasting
    try:
        full_model = ARIMA(series, order=order, seasonal_order=seasonal_order)
        full_fit = full_model.fit()
        forecast_res = full_fit.get_forecast(steps=forecast_horizon)
        future_pred = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int(alpha=0.05)
        lower_bound = np.maximum(conf_int.iloc[:, 0].values, 0)
        upper_bound = conf_int.iloc[:, 1].values
    except Exception:
        full_model = ARIMA(series, order=(1, 1, 1))
        full_fit = full_model.fit()
        forecast_res = full_fit.get_forecast(steps=forecast_horizon)
        future_pred = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int(alpha=0.05)
        lower_bound = np.maximum(conf_int.iloc[:, 0].values, 0)
        upper_bound = conf_int.iloc[:, 1].values

    future_dates = pd.date_range(start=series.index[-1] + pd.DateOffset(months=1), periods=forecast_horizon, freq="MS")
    future_df = pd.DataFrame({
        "date": future_dates,
        "forecast": np.maximum(future_pred.values, 0),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    })

    test_df = pd.DataFrame({
        "date": test.index,
        "actual": test.values,
        "predicted": np.maximum(pred_test.values, 0),
    })

    return {
        "model_name": f"ARIMA{order}x{seasonal_order}",
        "metrics": metrics,
        "test_evaluation_df": test_df,
        "future_forecast_df": future_df,
        "full_series": series,
        "train_len": len(train),
        "test_len": len(test),
    }


def generate_forecast(
    df: pd.DataFrame,
    model_type: str = "Holt-Winters",
    test_months: int = 8,
    forecast_horizon: int = 6,
    date_col: str = "order_date",
    value_col: str = "sales",
) -> Dict[str, Any]:
    """Unified entry point for forecasting models."""
    series = prepare_monthly_series(df, date_col=date_col, value_col=value_col)

    if model_type.lower().startswith("arima"):
        return fit_arima(series, test_months=test_months, forecast_horizon=forecast_horizon)
    else:
        return fit_holt_winters(series, test_months=test_months, forecast_horizon=forecast_horizon)
