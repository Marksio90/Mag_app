# oi/preprocessing.py
from __future__ import annotations
import pandas as pd
from typing import Optional
from .config import CONFIG

def normalize_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # oczekujemy kolumn podobnych do: data, sku, ilosc, magazyn
    # poniżej miękka normalizacja
    rename_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc.startswith("data"):
            rename_map[col] = CONFIG.date_col
        elif lc in ("sku", "produkt", "towar", "kod"):
            rename_map[col] = CONFIG.sku_col
        elif lc in ("ilosc", "quantity", "qty", "sprzedaz"):
            rename_map[col] = CONFIG.qty_col
        elif "magaz" in lc or "lokal" in lc:
            rename_map[col] = CONFIG.location_col
    df = df.rename(columns=rename_map)
    if CONFIG.date_col in df.columns:
        df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col])
    return df

def aggregate_sales(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    df = df.copy()
    df = df.set_index(CONFIG.date_col)
    group_cols = [CONFIG.sku_col]
    if CONFIG.location_col in df.columns:
        group_cols.append(CONFIG.location_col)
    agg = df.groupby(group_cols + [pd.Grouper(freq=freq)]).agg({CONFIG.qty_col: "sum"}).reset_index()
    return agg
