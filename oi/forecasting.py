# oi/forecasting.py
from __future__ import annotations
import pandas as pd
from typing import Dict, Any
from datetime import timedelta
from .config import CONFIG

def naive_forecast(series: pd.Series, periods: int) -> pd.Series:
    # bardzo prosty forecast: ostatnia wartość
    last_val = series.iloc[-1] if not series.empty else 0
    return pd.Series([last_val] * periods)

def moving_average_forecast(series: pd.Series, periods: int, window: int = 4) -> pd.Series:
    if len(series) < window:
        avg = series.mean() if len(series) > 0 else 0
    else:
        avg = series.tail(window).mean()
    return pd.Series([avg] * periods)

def forecast_sku(
    df: pd.DataFrame,
    sku: str,
    location: str | None = None,
    periods: int = 8,
    freq: str = "W"
) -> Dict[str, Any]:
    # filtr
    cond = df[CONFIG.sku_col] == sku
    if location and CONFIG.location_col in df.columns:
        cond &= df[CONFIG.location_col] == location
    sdf = df[cond].sort_values(CONFIG.date_col)
    if sdf.empty:
        return {"history": sdf, "forecast": None}

    sdf = sdf.set_index(CONFIG.date_col).asfreq(freq)
    y = sdf[CONFIG.qty_col].fillna(0)

    # tu można podpiąć Prophet / statsmodels / darts / neuralforecast
    fc = moving_average_forecast(y, periods, window=4)
    last_idx = y.index[-1]
    future_index = pd.date_range(last_idx + pd.tseries.frequencies.to_offset(freq), periods=periods, freq=freq)
    fc.index = future_index

    return {
        "history": y,
        "forecast": fc,
    }
