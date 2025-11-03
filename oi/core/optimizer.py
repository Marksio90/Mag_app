
from __future__ import annotations
from typing import Dict, Tuple
import numpy as np
from .inventory import calc_policy

def total_cost_per_year(weekly_mean: float, weekly_std: float,
                        lead_mean: float, lead_std: float,
                        service_level: float, holding_rate: float, ordering_cost: float,
                        unit_cost: float, min_order_qty: float, penalty_per_unit: float) -> Tuple[float, Dict]:
    pol = calc_policy(weekly_mean, weekly_std, lead_mean, lead_std, service_level,
                      holding_rate, ordering_cost, unit_cost, min_order_qty)
    D = weekly_mean * 52.0
    orders_per_year = max(1.0, D / max(pol.order_qty, 1e-6))
    holding_cost_year = 0.5 * pol.order_qty * holding_rate * unit_cost  # proxy (cycle stock half)
    ordering_cost_year = orders_per_year * ordering_cost
    # stockout proxy ~ (1-service_level) * demand
    stockout_units = (1.0 - min(service_level, 0.999)) * D
    stockout_cost_year = stockout_units * penalty_per_unit
    cost = holding_cost_year + ordering_cost_year + stockout_cost_year
    return cost, {"policy": pol, "holding": holding_cost_year, "ordering": ordering_cost_year,
                  "stockout": stockout_cost_year, "orders_per_year": orders_per_year}

def optimize_service_level(weekly_mean: float, weekly_std: float,
                            lead_mean: float, lead_std: float,
                            unit_cost: float, min_order_qty: float,
                            holding_rate: float=0.2, ordering_cost: float=150.0,
                            penalty_per_unit: float=25.0):
    grid = [0.90,0.92,0.95,0.97,0.98,0.99]
    best = None
    for sl in grid:
        c, details = total_cost_per_year(weekly_mean, weekly_std, lead_mean, lead_std, sl,
                                         holding_rate, ordering_cost, unit_cost, min_order_qty, penalty_per_unit)
        if best is None or c < best[0]:
            best = (c, sl, details)
    return {"best_cost": best[0], "best_service_level": best[1], **best[2]}
