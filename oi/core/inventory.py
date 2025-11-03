
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

_Z_TABLE = {
    0.90: 1.2816, 0.95: 1.6449, 0.97: 1.8808, 0.98: 2.0537, 0.99: 2.3263, 0.999: 3.0902
}

@dataclass
class PolicyResult:
    safety_stock: float
    reorder_point: float
    eoq: float
    review_period_days: int
    order_qty: float

def z_from_service(level: float)->float:
    keys = sorted(_Z_TABLE.keys())
    for k in keys:
        if level <= k:
            return _Z_TABLE[k]
    return _Z_TABLE[keys[-1]]

def calc_policy(weekly_mean: float, weekly_std: float, lead_mean_days: float, lead_std_days: float,
                service_level: float=0.95, holding_cost: float=0.20, ordering_cost: float=100.0,
                unit_cost: float=10.0, min_order_qty: float=0.0) -> PolicyResult:
    daily_mean = weekly_mean/7.0
    daily_std = weekly_std/np.sqrt(7.0)
    z = z_from_service(service_level)
    mean_during_lt = daily_mean * lead_mean_days
    std_during_lt = np.sqrt((daily_std**2)*(lead_mean_days) + (daily_mean**2)*(lead_std_days))
    safety_stock = z * std_during_lt
    reorder_point = mean_during_lt + safety_stock
    D = weekly_mean * 52.0
    H = holding_cost * unit_cost
    eoq = np.sqrt(max(1e-9, (2.0*D*ordering_cost)/max(1e-9, H)))
    order_qty = max(eoq, min_order_qty)
    return PolicyResult(safety_stock, reorder_point, eoq, review_period_days=7, order_qty=order_qty)
