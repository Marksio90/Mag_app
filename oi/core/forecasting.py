
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict
import numpy as np, polars as pl
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

@dataclass
class ForecastResult:
    history: np.ndarray
    forecast: np.ndarray
    model: str

def _series(df: pl.DataFrame, sku: str, qty_col="qty", date_col="date") -> np.ndarray:
    s = df.filter(pl.col("sku")==sku).sort(date_col)[qty_col].to_numpy()
    return s.astype(float)

def naive_last(s: np.ndarray, h: int)->np.ndarray:
    return np.repeat(s[-1], h) if len(s) else np.zeros(h)
def sma(s: np.ndarray, h: int, w:int=4)->np.ndarray:
    if len(s)==0: return np.zeros(h)
    avg = np.mean(s[-w:]) if len(s)>=w else np.mean(s)
    return np.repeat(avg, h)
def holt_winters(s: np.ndarray, h: int)->np.ndarray:
    if len(s) < 8: return sma(s, h, 4)
    try:
        model = ExponentialSmoothing(s, trend="add", seasonal="add", seasonal_periods=12).fit()
        fc = model.forecast(h)
        return np.maximum(fc, 0.0)
    except Exception:
        return sma(s, h, 4)
def sarimax(s: np.ndarray, h: int)->np.ndarray:
    if len(s) < 12: return holt_winters(s, h)
    try:
        model = SARIMAX(s, order=(1,1,1), seasonal_order=(1,1,1,12), enforce_stationarity=False, enforce_invertibility=False)
        res = model.fit(disp=False)
        fc = res.forecast(h)
        return np.maximum(fc, 0.0)
    except Exception:
        return holt_winters(s, h)

def forecast(df: pl.DataFrame, sku: str, horizon:int=12, algo:str="sarimax")->ForecastResult:
    s = _series(df, sku)
    if algo=="naive": fc = naive_last(s, horizon); m="naive"
    elif algo=="sma": fc = sma(s, horizon, 4); m="sma"
    elif algo=="holt": fc = holt_winters(s, horizon); m="holt-winters"
    else: fc = sarimax(s, horizon); m="sarimax"
    return ForecastResult(history=s, forecast=fc, model=m)
