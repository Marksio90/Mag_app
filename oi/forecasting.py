# oi/forecasting.py
from __future__ import annotations

"""
Moduł prognozowania popytu dla aplikacji magazynowej.

Założenia:
- działa nawet na bardzo małej liczbie punktów (fallbacki),
- można łatwo podmienić metodę prognozy (rejestr),
- zwracamy nie tylko serię prognozy, ale też meta-info (ile danych, jakie freq, jaka metoda),
- normalizujemy szereg do żądanej częstotliwości (D/W/M),
- wynik ma się łatwo łączyć z modułem optymalizacji.
"""

from typing import Dict, Any, Callable, Optional, Literal
from datetime import timedelta

import numpy as np
import pandas as pd

from .config import CONFIG


# ─────────────────────────────────────────────────────────────
# Podstawowe metody prognozujące
# ─────────────────────────────────────────────────────────────

def naive_forecast(series: pd.Series, periods: int) -> pd.Series:
    """
    Najprostsza możliwa prognoza – powtarza ostatnią wartość.
    Działa zawsze, więc jest świetnym fallbackiem.
    """
    last_val = float(series.iloc[-1]) if not series.empty else 0.0
    return pd.Series([last_val] * periods, dtype="float")


def moving_average_forecast(series: pd.Series, periods: int, window: int = 4) -> pd.Series:
    """
    Prognoza na bazie średniej kroczącej z ostatnich N okresów.
    Jeśli mamy mało danych – bierze średnią ze wszystkiego.
    """
    if len(series) == 0:
        avg = 0.0
    elif len(series) < window:
        avg = float(series.mean())
    else:
        avg = float(series.tail(window).mean())
    return pd.Series([avg] * periods, dtype="float")


def level_trend_forecast(series: pd.Series, periods: int) -> pd.Series:
    """
    Malutka wersja Holt’a – policz poziom + prosty trend liniowy.
    Nie zastępuje ETS, ale daje trochę dynamiki.
    """
    if len(series) < 3:
        # za mało na trend – użyj średniej
        base = float(series.mean()) if len(series) else 0.0
        return pd.Series([base] * periods, dtype="float")

    y = series.values.astype(float)
    # prosty trend: różnica średnia między ostatnimi punktami
    diffs = np.diff(y)
    trend = float(np.mean(diffs[-3:])) if len(diffs) >= 3 else float(np.mean(diffs))
    level = float(y[-1])

    fc_vals = [max(level + (i + 1) * trend, 0.0) for i in range(periods)]
    return pd.Series(fc_vals, dtype="float")


# ─────────────────────────────────────────────────────────────
# Rejestr metod – łatwo dodać Prophet / darts / neuralforecast
# ─────────────────────────────────────────────────────────────

FORECASTERS: Dict[str, Callable[..., pd.Series]] = {
    "naive": naive_forecast,
    "ma": moving_average_forecast,
    "level_trend": level_trend_forecast,
    # "prophet": forecast_with_prophet,  # ← tu możesz kiedyś podpiąć
}


def list_forecasters() -> Dict[str, str]:
    """
    Zwraca listę dostępnych metod – możesz to wyświetlić w UI.
    """
    return {
        "naive": "Powtarzanie ostatniej wartości (działa zawsze)",
        "ma": "Średnia krocząca (stabilizuje szum)",
        "level_trend": "Poziom + prosty trend (gdy widać kierunek)"
    }


# ─────────────────────────────────────────────────────────────
# Helpery do przygotowania szeregu
# ─────────────────────────────────────────────────────────────

def _ensure_datetime_index(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """
    Ustawia kolumnę daty jako index i resampluje do zadanej częstotliwości.
    Brakujące okresy uzupełnia zerem – w magazynie brak sprzedaży też jest informacją.
    """
    df = df.copy()
    df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")
    df = df.set_index(CONFIG.date_col).sort_index()

    # resample: agregujemy ilości
    rs = df[CONFIG.qty_col].resample(freq).sum().fillna(0)
    return rs.to_frame(name=CONFIG.qty_col)


def _build_future_index(last_timestamp: pd.Timestamp, periods: int, freq: str) -> pd.DatetimeIndex:
    """
    Tworzy indeks przyszłych okresów w zależności od częstotliwości.
    """
    return pd.date_range(
        last_timestamp + pd.tseries.frequencies.to_offset(freq),
        periods=periods,
        freq=freq,
    )


def _calc_simple_mape(y_true: pd.Series, y_pred: pd.Series) -> Optional[float]:
    """
    Bardzo prosty MAPE – na potrzeby podglądu jakości.
    Jeśli za mało danych – zwracamy None.
    """
    if len(y_true) < 3 or len(y_true) != len(y_pred):
        return None
    mask = y_true != 0
    if not mask.any():
        return None
    return float((np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])).mean() * 100)


# ─────────────────────────────────────────────────────────────
# Główna funkcja prognozująca dla SKU
# ─────────────────────────────────────────────────────────────

def forecast_sku(
    df: pd.DataFrame,
    sku: str,
    location: Optional[str] = None,
    periods: int = 8,
    freq: str = "W",
    method: str = "ma",
) -> Dict[str, Any]:
    """
    Buduje prognozę dla konkretnego SKU i (opcjonalnie) magazynu.

    Zwraca dict:
    {
        "history": pd.Series,
        "forecast": pd.Series | None,
        "meta": {...}
    }
    """
    # ── 1. filtrowanie po SKU + lokalizacji
    cond = df[CONFIG.sku_col] == sku
    if location and CONFIG.location_col in df.columns:
        cond &= df[CONFIG.location_col] == location
    sdf = df[cond].copy()

    if sdf.empty:
        return {
            "history": pd.Series(dtype="float"),
            "forecast": None,
            "meta": {
                "status": "empty",
                "reason": "Brak danych dla wskazanego SKU/magazynu.",
            },
        }

    # ── 2. normalizacja czasu
    # jeśli kolumna daty nie istnieje – nie prognozujemy
    if CONFIG.date_col not in sdf.columns:
        return {
            "history": pd.Series(dtype="float"),
            "forecast": None,
            "meta": {
                "status": "error",
                "reason": f"Brak kolumny daty ({CONFIG.date_col}) w danych.",
            },
        }

    # przekształć w regularny szereg czasowy
    ts_df = _ensure_datetime_index(sdf, freq=freq)
    y = ts_df[CONFIG.qty_col]

    # ── 3. wybór metody
    if method not in FORECASTERS:
        # fallback
        method = "ma"
    forecaster = FORECASTERS[method]

    # ── 4. prognoza
    fc_vals = forecaster(y, periods=periods)
    # indeks przyszły
    future_index = _build_future_index(y.index[-1], periods, freq)
    fc_vals.index = future_index

    # ── 5. prosty błąd na końcówce (porównujemy ostatnie 3 punkty z MA)
    # to nie jest pełny backtest, tylko szybka informacja do UI
    tail = min(3, len(y))
    mape = None
    if tail >= 2:
        # spróbujmy oszacować jak by wyglądała prognoza na ostatnie punkty
        # (użyjemy tej samej metody na y bez ostatniego punktu)
        hist_part = y.iloc[:-1]
        if len(hist_part) >= 2:
            pseudo_fc = forecaster(hist_part, periods=1)
            pseudo_fc.index = [y.index[-1]]
            mape = _calc_simple_mape(y.iloc[-1:], pseudo_fc)

    meta = {
        "status": "ok",
        "method": method,
        "freq": freq,
        "periods": periods,
        "n_history": int(len(y)),
        "mape_last": mape,
        "sku": sku,
        "location": location,
    }

    return {
        "history": y,
        "forecast": fc_vals,
        "meta": meta,
    }
