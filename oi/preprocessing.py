# oi/preprocessing.py
from __future__ import annotations
import pandas as pd
from typing import Optional
from .config import CONFIG

def normalize_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rename_map = {}
    for col in df.columns:
        lc = col.lower().strip()

        # data
        if lc.startswith("data"):
            rename_map[col] = CONFIG.date_col

        # sku / towar / produkt
        elif lc in ("sku", "produkt", "towar", "kod", "id_produktu", "id_sku"):
            rename_map[col] = CONFIG.sku_col

        # ilość / quantity
        elif lc in ("ilosc", "ilość", "quantity", "qty", "sprzedaz", "sprzedaż", "wolumen"):
            rename_map[col] = CONFIG.qty_col

        # magazyn / lokalizacja
        elif "magaz" in lc or "lokal" in lc or "oddział" in lc:
            rename_map[col] = CONFIG.location_col

    df = df.rename(columns=rename_map)

    # spróbuj jeszcze raz znaleźć kolumnę z datą jeśli nie została nazwana
    if CONFIG.date_col not in df.columns:
        for col in df.columns:
            if "data" in col.lower():
                df = df.rename(columns={col: CONFIG.date_col})
                break

    # konwersja na datetime
    if CONFIG.date_col in df.columns:
        df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")

    return df

def aggregate_sales(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    df = df.copy()

    # 🔐 jeśli ktoś wywoła aggregate_sales na nienormalizowanym df – spróbujmy naprawić
    if CONFIG.date_col not in df.columns:
        df = normalize_sales_df(df)

    if CONFIG.date_col not in df.columns:
        # dalej nie ma – oddaj pusty, niech UI to obsłuży
        return pd.DataFrame(columns=[CONFIG.date_col, CONFIG.sku_col, CONFIG.qty_col])

    df = df.set_index(CONFIG.date_col)

    group_cols = [CONFIG.sku_col]
    if CONFIG.location_col in df.columns:
        group_cols.append(CONFIG.location_col)

    agg = (
        df
        .groupby(group_cols + [pd.Grouper(freq=freq)])
        .agg({CONFIG.qty_col: "sum"})
        .reset_index()
        .rename(columns={CONFIG.date_col: "data"})
    )
    return agg
