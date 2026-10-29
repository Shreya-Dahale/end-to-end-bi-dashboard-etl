"""
What-If Scenario Simulation Engine.
Applies adjustable growth rates (-10% to +20%) to baseline projections,
comparing baseline and scenario-adjusted revenue, profit, and cumulative margins.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def simulate_what_if_scenario(
    df_series: pd.DataFrame,
    growth_rate_pct: float = 5.0,
    margin_expansion_pct: float = 0.0,
    date_col: str = "date",
    sales_col: str = "sales",
    profit_col: Optional[str] = "profit",
    baseline_profit_margin_pct: float = 12.0,
) -> Dict[str, Any]:
    """
    Simulates What-If business scenarios with adjustable revenue growth and profit margin changes.

    Parameters:
        df_series: DataFrame containing monthly baseline dates, sales, and optional profit.
        growth_rate_pct: Percentage change in sales (-10.0 to +20.0).
        margin_expansion_pct: Absolute percentage points change in profit margin (e.g. +1.0% or 0.0%).
        date_col: Date column name.
        sales_col: Baseline sales column name.
        profit_col: Baseline profit column name.
        baseline_profit_margin_pct: Fallback profit margin % if profit column not present.

    Returns:
        Dictionary containing comparison summary, scenario DataFrame, and KPI deltas.
    """
    df = df_series.copy()
    if date_col not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df[date_col] = df.index
        else:
            df[date_col] = pd.date_range(start="2018-01-01", periods=len(df), freq="MS")

    df[sales_col] = pd.to_numeric(df[sales_col], errors="coerce").fillna(0.0)

    # Compute baseline profit if not provided
    if profit_col and profit_col in df.columns:
        df[profit_col] = pd.to_numeric(df[profit_col], errors="coerce").fillna(0.0)
    else:
        profit_col = "profit"
        df[profit_col] = df[sales_col] * (baseline_profit_margin_pct / 100.0)

    # Growth factor
    growth_multiplier = 1.0 + (growth_rate_pct / 100.0)

    # Effective scenario profit margin
    avg_hist_margin = (
        (df[profit_col].sum() / df[sales_col].sum() * 100.0)
        if df[sales_col].sum() > 0
        else baseline_profit_margin_pct
    )
    scenario_margin_pct = avg_hist_margin + margin_expansion_pct

    # Scenario calculations
    df["scenario_sales"] = df[sales_col] * growth_multiplier
    df["sales_delta"] = df["scenario_sales"] - df[sales_col]

    df["scenario_profit"] = df["scenario_sales"] * (scenario_margin_pct / 100.0)
    df["profit_delta"] = df["scenario_profit"] - df[profit_col]

    # Cumulative series
    df["cum_baseline_sales"] = df[sales_col].cumsum()
    df["cum_scenario_sales"] = df["scenario_sales"].cumsum()
    df["cum_sales_delta"] = df["cum_scenario_sales"] - df["cum_baseline_sales"]

    # Totals
    total_base_sales = float(df[sales_col].sum())
    total_scenario_sales = float(df["scenario_sales"].sum())
    total_sales_delta = float(df["sales_delta"].sum())

    total_base_profit = float(df[profit_col].sum())
    total_scenario_profit = float(df["scenario_profit"].sum())
    total_profit_delta = float(df["profit_delta"].sum())

    pct_sales_change = ((total_scenario_sales - total_base_sales) / total_base_sales * 100) if total_base_sales > 0 else 0.0
    pct_profit_change = ((total_scenario_profit - total_base_profit) / total_base_profit * 100) if total_base_profit > 0 else 0.0

    return {
        "growth_rate_pct": float(growth_rate_pct),
        "margin_expansion_pct": float(margin_expansion_pct),
        "total_baseline_sales": round(total_base_sales, 2),
        "total_scenario_sales": round(total_scenario_sales, 2),
        "total_sales_delta": round(total_sales_delta, 2),
        "pct_sales_change": round(pct_sales_change, 2),
        "total_baseline_profit": round(total_base_profit, 2),
        "total_scenario_profit": round(total_scenario_profit, 2),
        "total_profit_delta": round(total_profit_delta, 2),
        "pct_profit_change": round(pct_profit_change, 2),
        "scenario_margin_pct": round(scenario_margin_pct, 2),
        "scenario_df": df,
    }
