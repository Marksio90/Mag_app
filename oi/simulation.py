# oi/simulation.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, List

def monte_carlo_stockout(
    forecast: pd.Series,
    current_stock: float,
    lead_time_days: int,
    n_sim: int = 500,
    demand_volatility: float = 0.15,
) -> Dict:
    # prosty MC: losujemy zapotrzebowanie wokół prognozy
    stockouts = 0
    ending_stocks: List[float] = []
    for _ in range(n_sim):
        stock = current_stock
        for val in forecast:
            # zaburz popyt
            noise = np.random.normal(loc=0.0, scale=demand_volatility * val)
            demand = max(val + noise, 0)
            stock -= demand
            # uproszczenie: dostawa przychodzi po lead_time_days — tu możesz rozszerzyć
        ending_stocks.append(stock)
        if stock < 0:
            stockouts += 1
    prob_stockout = stockouts / n_sim
    return {
        "prob_stockout": prob_stockout,
        "avg_ending_stock": float(np.mean(ending_stocks)),
        "min_ending_stock": float(np.min(ending_stocks)),
        "max_ending_stock": float(np.max(ending_stocks)),
    }
