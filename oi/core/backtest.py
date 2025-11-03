
from __future__ import annotations
import numpy as np, polars as pl
from typing import Dict, List, Tuple
from .forecasting import naive_last, sma, holt_winters, sarimax

def mape(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    denom = np.where(y_true==0, 1.0, y_true)
    return np.mean(np.abs((y_true - y_pred)/denom))*100.0

def rmse(y_true, y_pred):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true - y_pred)**2)))

def rmsse(y_train, y_true, y_pred):
    y_train = np.array(y_train, dtype=float)
    scale = np.mean((y_train[1:] - y_train[:-1])**2) if len(y_train)>1 else 1.0
    return float(np.sqrt(np.mean((y_true - y_pred)**2) / max(scale,1e-9)))

def rolling_backtest(series: List[float], horizon=4, window=12, algos=None) -> Dict:
    if algos is None:
        algos = {"naive": naive_last, "sma": lambda s,h: sma(s,h,4), "holt": holt_winters, "sarimax": sarimax}
    results = {}
    for name, algo in algos.items():
        preds, trues = [], []
        for t in range(window, len(series)-horizon+1):
            train = np.array(series[:t], dtype=float)
            test = np.array(series[t:t+horizon], dtype=float)
            fc = algo(train, horizon)
            preds.extend(fc)
            trues.extend(test)
        if len(trues)==0:
            results[name] = {"MAPE": None, "RMSE": None, "RMSSE": None}
        else:
            results[name] = {
                "MAPE": mape(trues, preds),
                "RMSE": rmse(trues, preds),
                "RMSSE": rmsse(series[:window], trues, preds),
            }
    # pick best by RMSSE then RMSE
    best = sorted(results.items(), key=lambda kv: (kv[1]["RMSSE"] if kv[1]["RMSSE"] is not None else 1e9,
                                                   kv[1]["RMSE"] if kv[1]["RMSE"] is not None else 1e9))[0][0]
    return {"metrics": results, "best_algo": best}
