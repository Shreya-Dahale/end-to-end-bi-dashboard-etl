"""
Trend Analysis Module.
Computes linear regression trend lines, goodness-of-fit metrics (R-squared, p-value),
and human-readable business interpretation.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from scipy import stats


def compute_sales_trend(df_monthly: pd.DataFrame, date_col: str = "order_date", value_col: str = "sales") -> Dict[str, Any]:
    """
    Computes linear regression trend on a monthly aggregated time series.

    Parameters:
        df_monthly: DataFrame with date index or date column and aggregated sales.
        date_col: Name of date column (or uses index if DatetimeIndex).
        value_col: Name of value column to analyze.

    Returns:
        Dictionary containing slope, intercept, r_squared, p_value, std_err,
        trend_direction, explanation, and DataFrame with fitted trend line.
    """
    df = df_monthly.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(by=date_col).reset_index(drop=True)
            df = df.set_index(date_col)
        else:
            raise ValueError(f"Date column '{date_col}' not found and index is not DatetimeIndex.")

    # Ensure contiguous monthly frequency
    series = df[value_col].asfreq("MS").fillna(0.0)
    n = len(series)

    if n < 3:
        raise ValueError(f"Insufficient data points ({n}) for trend regression. Need at least 3 months.")

    x = np.arange(n)
    y = series.values

    # Run Scipy linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    r_squared = r_value ** 2

    # Fitted line values
    y_pred = intercept + slope * x

    # Trend Direction and Business Interpretation
    if slope > 50 and p_value < 0.05:
        direction = "Strong Upward Growth"
        interpretation = (
            f"Sales exhibit a statistically significant upward trajectory (p={p_value:.4f} < 0.05). "
            f"On average, monthly revenue grows by ${slope:,.2f} every month, with the regression model explaining "
            f"{r_squared * 100:.1f}% of the monthly variance (R² = {r_squared:.3f})."
        )
    elif slope > 0:
        direction = "Moderate Upward Trend"
        interpretation = (
            f"Sales show a positive upward tilt (+${slope:,.2f}/month). The R² of {r_squared:.3f} indicates "
            f"underlying seasonal swings typical of retail demand."
        )
    elif slope < -50 and p_value < 0.05:
        direction = "Significant Contraction"
        interpretation = (
            f"Sales show a statistically significant downward trend (-${abs(slope):,.2f}/month, p={p_value:.4f}). "
            f"Immediate review of customer churn and discount strategy is advised."
        )
    else:
        direction = "Stable / Flat"
        interpretation = (
            f"Sales are essentially horizontal (slope = ${slope:,.2f}/month, R² = {r_squared:.3f}), "
            f"reflecting steady cyclical baseline demand without secular decline."
        )

    # Resulting DataFrame
    trend_df = pd.DataFrame({
        "date": series.index,
        "actual_sales": y,
        "trend_line": y_pred,
        "residual": y - y_pred,
    })

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_value": float(r_value),
        "r_squared": float(r_squared),
        "p_value": float(p_value),
        "std_err": float(std_err),
        "trend_direction": direction,
        "interpretation": interpretation,
        "trend_df": trend_df,
    }
