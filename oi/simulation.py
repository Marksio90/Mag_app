# oi/simulation.py
from __future__ import annotations
"""
Moduł symulacji / Monte Carlo dla magazynu.

Pozwala:
- zasymulować zużycie zapasu przy danym forecastcie i zmienności,
- przetestować prostą politykę uzupełniania (ROP + qty),
- oszacować prawdopodobieństwo stock-outu (service level),
- uruchomić kilka scenariuszy na raz (np. różne poziomy ROP albo lead time).

Do użycia z zakładką "🧪 Symulacje".
"""

from typing import Dict, List, Any, Optional, Sequence
import numpy as np
import pandas as pd

from .config import CONFIG


# ─────────────────────────────────────────────────────────────
# Helpery
# ─────────────────────────────────────────────────────────────

def _to_daily_series(forecast: pd.Series) -> pd.Series:
    """
    Jeśli prognoza jest tygodniowa/miesięczna, spróbuj ją rozbić na dni
    proporcjonalnie (po równo). To daje lepszą symulację “dzień po dniu”.
    """
    if forecast.empty:
        return forecast

    idx = forecast.index
    # jeśli to już jest dzienne – zostaw
    if idx.freq is not None and str(idx.freq).upper().startswith("D"):
        return forecast

    # spróbuj zgadnąć interwał
    diffs = idx.to_series().diff().dropna()
    if diffs.empty:
        return forecast

    days = int(diffs.iloc[0].days)
    if days <= 1:
        return forecast

    # rozbij każdy okres na 'days' dni
    daily_values = []
    daily_index = []
    for i, (ts, val) in enumerate(forecast.items()):
        per_day = val / days
        for d in range(days):
            daily_index.append(ts + pd.Timedelta(days=d))
            daily_values.append(per_day)

    return pd.Series(daily_values, index=pd.DatetimeIndex(daily_index)).sort_index()


# ─────────────────────────────────────────────────────────────
# 1) Prosta symulacja – Twoja, tylko z minimalnymi usprawnieniami
# ─────────────────────────────────────────────────────────────

def monte_carlo_stockout(
    forecast: pd.Series,
    current_stock: float,
    lead_time_days: int,
    n_sim: int = 500,
    demand_volatility: float = 0.15,
) -> Dict[str, float]:
    """
    Bardzo prosty MC: losujemy zapotrzebowanie wokół prognozy
    i patrzymy, ile symulacji skończyło z ujemnym stanem.
    Nie ma tu jeszcze zamówień – to “worst case” jeśli nic nie robimy.
    """
    # urealnij forecast do dni
    daily_forecast = _to_daily_series(forecast)

    stockouts = 0
    ending_stocks: List[float] = []

    for _ in range(n_sim):
        stock = float(current_stock)
        for val in daily_forecast:
            noise = np.random.normal(loc=0.0, scale=demand_volatility * val)
            demand = max(val + noise, 0.0)
            stock -= demand
        ending_stocks.append(stock)
        if stock < 0:
            stockouts += 1

    prob_stockout = stockouts / n_sim if n_sim > 0 else 0.0

    return {
        "prob_stockout": float(prob_stockout),
        "avg_ending_stock": float(np.mean(ending_stocks)) if ending_stocks else 0.0,
        "min_ending_stock": float(np.min(ending_stocks)) if ending_stocks else 0.0,
        "max_ending_stock": float(np.max(ending_stocks)) if ending_stocks else 0.0,
    }


# ─────────────────────────────────────────────────────────────
# 2) Zaawansowana symulacja z polityką uzupełnień
# ─────────────────────────────────────────────────────────────

def monte_carlo_policy(
    forecast: pd.Series,
    current_stock: float,
    reorder_point: float,
    order_qty: float,
    lead_time_days: int,
    n_sim: int = 500,
    demand_volatility: float = 0.15,
    service_level_target: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Symuluje politykę:
    - idziemy dzień po dniu,
    - jeśli na początku dnia stan < ROP -> składamy zamówienie, które przychodzi po lead_time_days,
    - zużywamy zapas wg forecastu +/- losowy szum,
    - mierzymy ile razy stan spadł poniżej zera.

    Zwraca:
    - prawdopodobieństwo stock-outu
    - średnią liczbę stock-outów na przebieg
    - procent przebiegów spełniających target service level
    """

    daily_forecast = _to_daily_series(forecast)
    n_days = len(daily_forecast)

    stockout_runs = 0
    stockouts_per_run: List[int] = []
    service_ok_runs = 0

    for _ in range(n_sim):
        stock = float(current_stock)
        # kolejka dostaw: lista (day_arrives, qty)
        deliveries: List[tuple[int, float]] = []
        stockouts_this_run = 0

        for day_idx, val in enumerate(daily_forecast):
            # sprawdź, czy dziś coś przychodzi
            # (tu dla prostoty day_idx to liczba dni od startu)
            if deliveries and deliveries[0][0] == day_idx:
                _, qty = deliveries.pop(0)
                stock += qty

            # jeśli stan poniżej ROP – złóż zamówienie
            if stock < reorder_point and order_qty > 0:
                deliveries.append((day_idx + lead_time_days, order_qty))

            # zużycie
            noise = np.random.normal(loc=0.0, scale=demand_volatility * val)
            demand = max(val + noise, 0.0)
            stock -= demand

            if stock < 0:
                stockouts_this_run += 1

        stockouts_per_run.append(stockouts_this_run)
        if stockouts_this_run > 0:
            stockout_runs += 1

        # service level run-level (brak stock-outu w ogóle)
        if service_level_target is not None:
            # target np. 0.95 oznacza: 95% przebiegów bez stock-outu
            # tu zapisujemy po prostu info, czy ten przebieg był OK
            if stockouts_this_run == 0:
                service_ok_runs += 1

    prob_any_stockout = stockout_runs / n_sim if n_sim > 0 else 0.0
    avg_stockouts = float(np.mean(stockouts_per_run)) if stockouts_per_run else 0.0

    res: Dict[str, Any] = {
        "prob_any_stockout": float(prob_any_stockout),
        "avg_stockouts_per_run": avg_stockouts,
        "runs": int(n_sim),
    }

    if service_level_target is not None and n_sim > 0:
        achieved = service_ok_runs / n_sim
        res["service_level_achieved"] = float(achieved)
        res["service_level_target"] = float(service_level_target)

    return res


# ─────────────────────────────────────────────────────────────
# 3) Runner wielu scenariuszy – np. różne ROP albo różna zmienność
# ─────────────────────────────────────────────────────────────

def run_scenarios(
    forecast: pd.Series,
    current_stock: float,
    lead_time_days: int,
    scenarios: Sequence[Dict[str, Any]],
    n_sim: int = 500,
) -> List[Dict[str, Any]]:
    """
    Uruchamia kilka wariantów symulacji z różnymi parametrami.
    Każdy scenariusz powinien mieć klucze:
    - name (str)
    - reorder_point (float)
    - order_qty (float)
    - demand_volatility (float)

    Zwracamy listę wyników z nazwą scenariusza.
    """
    results: List[Dict[str, Any]] = []
    for sc in scenarios:
        name = sc.get("name", "scenario")
        rop = float(sc.get("reorder_point", 0))
        oq = float(sc.get("order_qty", 0))
        vol = float(sc.get("demand_volatility", 0.15))

        sim_res = monte_carlo_policy(
            forecast=forecast,
            current_stock=current_stock,
            reorder_point=rop,
            order_qty=oq,
            lead_time_days=lead_time_days,
            n_sim=n_sim,
            demand_volatility=vol,
        )
        sim_res["scenario"] = name
        sim_res["reorder_point"] = rop
        sim_res["order_qty"] = oq
        sim_res["demand_volatility"] = vol
        results.append(sim_res)
    return results
