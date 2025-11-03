# oi/optimization.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict
from scipy.stats import norm
from .config import CONFIG

def z_value(service_level: float) -> float:
    return norm.ppf(service_level)

def calc_safety_stock(
    demand_std: float,
    lead_time_days: int,
    service_level: float = 0.95,
) -> float:
    # klasyczna formuła
    z = z_value(service_level)
    return z * demand_std * np.sqrt(lead_time_days)

def calc_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: float
) -> float:
    return avg_daily_demand * lead_time_days + safety_stock

def calc_eoq(
    annual_demand: float,
    order_cost: float,
    holding_cost: float
) -> float:
    # klasyczny wzór Wilsona
    if annual_demand <= 0 or order_cost <= 0 or holding_cost <= 0:
        return 0.0
    return np.sqrt((2 * annual_demand * order_cost) / holding_cost)

def build_inventory_recommendation(
    forecast_df: pd.Series,
    current_stock: float,
    lead_time_days: int = 7,
    service_level: float = 0.95,
    order_cost: float = 50.0,
    holding_cost: float = 2.0
) -> Dict:
    # forecast_df – seria prognozy okresowej (np. tygodniowej)
    daily_demand_est = forecast_df.mean() / 7.0  # gdy mamy TYG
    demand_std = forecast_df.std() / 7.0
    ss = calc_safety_stock(demand_std, lead_time_days, service_level)
    rop = calc_reorder_point(daily_demand_est, lead_time_days, ss)
    annual_demand = daily_demand_est * 365
    eoq = calc_eoq(annual_demand, order_cost, holding_cost)

    order_qty = 0.0
    if current_stock < rop:
        order_qty = max(eoq, rop - current_stock)

    return {
        "daily_demand_est": daily_demand_est,
        "demand_std_daily": demand_std,
        "safety_stock": ss,
        "reorder_point": rop,
        "eoq": eoq,
        "current_stock": current_stock,
        "suggested_order_qty": order_qty,
    }
