# oi/optimization.py
from __future__ import annotations
"""
Moduł optymalizacji zapasu

Cele:
- na podstawie prognozy popytu wyznaczyć: zapas bezpieczeństwa, punkt ponownego zamówienia (ROP),
  ekonomiczną wielkość zamówienia (EOQ) i finalną sugerowaną ilość zamówienia,
- uwzględnić niepewność prognozy (std, krótka historia),
- uwzględnić ograniczenia biznesowe (MOQ, wielkość partii, pojemność),
- oddać w wyniku komplet informacji do pokazania w UI i do wyjaśnień przez AI.

Współpracuje bezpośrednio z:
- oi.forecasting (podajemy forecast i meta)
- oi.config (domyślne parametry logistyczne)
"""

from typing import Dict, Any, Optional, Literal

import numpy as np
import pandas as pd
from scipy.stats import norm

from .config import CONFIG


# ─────────────────────────────────────────────────────────────
# Core matematyka
# ─────────────────────────────────────────────────────────────

def z_value(service_level: float) -> float:
    """Zwraca wartość z-rozkładu normalnego dla wymaganego poziomu obsługi."""
    return norm.ppf(service_level)


def calc_safety_stock(
    demand_std_daily: float,
    lead_time_days: int,
    service_level: float,
    volatility_factor: float = 1.0,
) -> float:
    """
    Zapas bezpieczeństwa wg klasycznej formuły, z opcjonalnym wzmocnieniem
    volatility_factor – jeśli prognoza była robiona na małej próbce albo model mówi, że jest niepewna.
    """
    z = z_value(service_level)
    return z * demand_std_daily * np.sqrt(lead_time_days) * volatility_factor


def calc_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: float,
) -> float:
    """Klasyczny ROP."""
    return avg_daily_demand * lead_time_days + safety_stock


def calc_eoq(
    annual_demand: float,
    order_cost: float,
    holding_cost: float,
) -> float:
    """
    Klasyczny wzór Wilsona (EOQ).
    Jeśli któreś z wejść nie ma sensu – zwróć 0 i nie blokuj dalszej kalkulacji.
    """
    if annual_demand <= 0 or order_cost <= 0 or holding_cost <= 0:
        return 0.0
    return np.sqrt((2.0 * annual_demand * order_cost) / holding_cost)


# ─────────────────────────────────────────────────────────────
# Helpery do przeliczeń częstotliwości prognozy
# ─────────────────────────────────────────────────────────────

def _infer_forecast_freq(series: pd.Series) -> Literal["D", "W", "M"]:
    """Próbuje rozpoznać częstotliwość prognozy z indeksu datetime."""
    if series.index.freq is not None:
        # pandas czasem daje 'W-SUN', 'W-MON' – weźmy tylko literę
        freq_str = series.index.freqstr.upper()
        if freq_str.startswith("D"):
            return "D"
        if freq_str.startswith("W"):
            return "W"
        if freq_str.startswith("M"):
            return "M"
    # fallback – zgaduj po diffs
    diffs = series.index.to_series().diff().dropna().unique()
    if len(diffs) == 1:
        delta = diffs[0].days
        if delta == 1:
            return "D"
        if 6 <= delta <= 8:
            return "W"
        if 27 <= delta <= 32:
            return "M"
    return "W"  # bezpieczny default


def _to_daily_demand_stats(
    forecast_df: pd.Series,
    freq: Optional[str] = None,
) -> Dict[str, float]:
    """
    Na podstawie prognozy okresowej (D/W/M) policz średni dzienny popyt i dzienne odchylenie.
    """
    if forecast_df.empty:
        return {"daily_mean": 0.0, "daily_std": 0.0}

    if freq is None:
        freq = _infer_forecast_freq(forecast_df)

    if freq == "D":
        daily_mean = float(forecast_df.mean())
        daily_std = float(forecast_df.std())
    elif freq == "W":
        # zakładamy 7 dni w tygodniu
        daily_mean = float(forecast_df.mean()) / 7.0
        daily_std = float(forecast_df.std()) / 7.0
    elif freq == "M":
        # przybliżenie: 30 dni w miesiącu
        daily_mean = float(forecast_df.mean()) / 30.0
        daily_std = float(forecast_df.std()) / 30.0
    else:
        # fallback – traktuj jak tygodniową
        daily_mean = float(forecast_df.mean()) / 7.0
        daily_std = float(forecast_df.std()) / 7.0

    return {"daily_mean": daily_mean, "daily_std": daily_std}


# ─────────────────────────────────────────────────────────────
# Główna funkcja – gotowa dla UI
# ─────────────────────────────────────────────────────────────

def build_inventory_recommendation(
    forecast_df: pd.Series,
    current_stock: float,
    lead_time_days: Optional[int] = None,
    service_level: Optional[float] = None,
    order_cost: Optional[float] = None,
    holding_cost: Optional[float] = None,
    forecast_meta: Optional[Dict[str, Any]] = None,
    min_order_qty: float = 0.0,
    lot_size: float = 0.0,
    max_storage_qty: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Wyznacza komplet rekomendacji magazynowej.

    Parametry:
    - forecast_df: seria prognozy popytu (D/W/M, indeks datetime)
    - current_stock: aktualny stan w magazynie
    - lead_time_days: czas dostawy w dniach (jak None → z CONFIG)
    - service_level: wymagany poziom obsługi (jak None → z CONFIG)
    - order_cost: koszt złożenia zamówienia (jak None → z CONFIG)
    - holding_cost: koszt utrzymania 1 szt. (jak None → z CONFIG)
    - forecast_meta: opcjonalne meta z modułu prognoz – wtedy możemy podbić volatility_factor
    - min_order_qty: minimalna wielkość zamówienia (MOQ)
    - lot_size: zaokrąglanie do wielkości partii (np. 10, 50, karton)
    - max_storage_qty: górne ograniczenie pojemności magazynu

    Zwraca dict gotowy do pokazania w UI.
    """

    # ── 1. Domyślne wartości z configu
    lead_time_days = lead_time_days or CONFIG.default_lead_time_days
    service_level = service_level or CONFIG.default_service_level
    order_cost = order_cost or CONFIG.default_order_cost
    holding_cost = holding_cost or CONFIG.default_holding_cost

    # ── 2. Jeśli prognoza pusta – nie kombinujemy
    if forecast_df is None or forecast_df.empty:
        return {
            "status": "no_forecast",
            "reason": "Brak prognozy – nie można policzyć ROP.",
            "current_stock": current_stock,
        }

    # ── 3. Przeliczenie na dzienny popyt
    freq = _infer_forecast_freq(forecast_df)
    daily_stats = _to_daily_demand_stats(forecast_df, freq=freq)
    daily_demand_est = daily_stats["daily_mean"]
    demand_std_daily = daily_stats["daily_std"]

    # ── 4. Volatility factor – jeśli meta mówi, że danych było mało → zwiększ zapas
    volatility_factor = 1.0
    if forecast_meta:
        n_history = forecast_meta.get("n_history", 0)
        mape_last = forecast_meta.get("mape_last", None)
        # jeśli bardzo mało okresów historii – zwiększ o 20%
        if n_history and n_history < 6:
            volatility_factor *= 1.2
        # jeśli błąd na końcu duży – dołóż
        if mape_last and mape_last > 15:
            volatility_factor *= 1.15

    # ── 5. Safety stock
    safety_stock = calc_safety_stock(
        demand_std_daily=demand_std_daily,
        lead_time_days=lead_time_days,
        service_level=service_level,
        volatility_factor=volatility_factor,
    )

    # ── 6. ROP
    reorder_point = calc_reorder_point(
        avg_daily_demand=daily_demand_est,
        lead_time_days=lead_time_days,
        safety_stock=safety_stock,
    )

    # ── 7. EOQ (na bazie rocznego popytu)
    annual_demand = daily_demand_est * 365.0
    eoq = calc_eoq(
        annual_demand=annual_demand,
        order_cost=order_cost,
        holding_cost=holding_cost,
    )

    # ── 8. Surowa propozycja zamówienia
    suggested_order_qty = 0.0
    if current_stock < reorder_point:
        # zamów tyle, żeby przekroczyć ROP + zapas albo minimum EOQ
        suggested_order_qty = max(eoq, reorder_point - current_stock)

    # ── 9. MOQ / lot size
    if suggested_order_qty > 0:
        # minimalna partia
        if min_order_qty and suggested_order_qty < min_order_qty:
            suggested_order_qty = float(min_order_qty)
        # zaokrąglenie do partii
        if lot_size and lot_size > 0:
            suggested_order_qty = float(np.ceil(suggested_order_qty / lot_size) * lot_size)

    # ── 10. Ograniczenie pojemnością magazynu
    if max_storage_qty is not None and suggested_order_qty > 0:
        free_space = max_storage_qty - current_stock
        if free_space < 0:
            # magazyn przepełniony
            suggested_order_qty = 0.0
        else:
            suggested_order_qty = min(suggested_order_qty, free_space)

    # ── 11. Szybka ocena ryzyka (jeśli nic nie zamówimy)
    # oszacuj ile dni pokryjemy obecnym zapasem
    days_of_cover = current_stock / daily_demand_est if daily_demand_est > 0 else float("inf")
    stockout_risk = 0.0
    if days_of_cover < lead_time_days:
        # jeśli nie mamy zapasu na czas dostawy → wysokie ryzyko
        stockout_risk = min(1.0, (lead_time_days - days_of_cover) / lead_time_days)

    return {
        "status": "ok",
        "freq": freq,
        "daily_demand_est": daily_demand_est,
        "demand_std_daily": demand_std_daily,
        "volatility_factor": volatility_factor,
        "safety_stock": float(safety_stock),
        "reorder_point": float(reorder_point),
        "eoq": float(eoq),
        "current_stock": float(current_stock),
        "suggested_order_qty": float(suggested_order_qty),
        "service_level": float(service_level),
        "lead_time_days": int(lead_time_days),
        "order_cost": float(order_cost),
        "holding_cost": float(holding_cost),
        "annual_demand_est": float(annual_demand),
        "days_of_cover": float(days_of_cover),
        "stockout_risk": float(stockout_risk),
        "constraints": {
            "min_order_qty": float(min_order_qty),
            "lot_size": float(lot_size),
            "max_storage_qty": float(max_storage_qty) if max_storage_qty is not None else None,
        },
        "raw_forecast_len": int(len(forecast_df)),
    }
