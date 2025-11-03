# oi/preprocessing.py
from __future__ import annotations
"""
Preprocessing danych do aplikacji magazynowej.

Cele:
- ujednolicić nazwy kolumn (data, sku, ilosc, magazyn),
- poradzić sobie z różnymi nazwami z Excela/ERP (DataDok, KodTowaru, IlośćWydana, MagazynŹródłowy),
- zapewnić konwersję kolumny daty do datetime,
- dać helper do ręcznego wymuszenia kolumny daty (z UI),
- zrobić bezpieczną agregację czasową do D/W/M,
- oddać info, czego brakuje – żeby UI mógł to pokazać.

Współpracuje z:
- oi.config (nazywanie kolumn)
- oi.data_ingestion (tam wgrywamy kilka plików)
"""

import pandas as pd
from typing import Optional, Dict, List, Tuple, Any

from .config import CONFIG


# ─────────────────────────────────────────────────────────────
# Słowniki rozpoznawania nazw kolumn
# ─────────────────────────────────────────────────────────────

# tu możesz dopisywać swoje firmowe wynalazki nazw kolumn
DATE_CANDIDATES = [
    "data", "date", "data_dok", "datadok", "datadokumentu", "dokument_data",
    "data_sprzedazy", "data sprzedaży", "d_sprzedazy", "docdate", "postingdate",
]

SKU_CANDIDATES = [
    "sku", "produkt", "towar", "kod", "kod_towaru", "symbol", "indeks", "item", "itemcode",
    "id_produktu", "id_sku", "material", "material_code",
]

QTY_CANDIDATES = [
    "ilosc", "ilość", "quantity", "qty", "sprzedaz", "sprzedaż", "wolumen",
    "wydano", "ilosc_wydana", "qty_issued", "qty_shipped",
]

LOCATION_CANDIDATES = [
    "magazyn", "lokalizacja", "lokalizacja_magazynowa", "oddział", "warehouse", "wh", "storage",
    "miejsce", "miejsce_skladowania",
]


# ─────────────────────────────────────────────────────────────
# Funkcje rozpoznające
# ─────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Zwraca nazwę pierwszej kolumny pasującej do listy kandydatów (case-insensitive, bez spacji)."""
    norm_cols = {c.lower().replace(" ", "").replace("-", "").replace("_", ""): c for c in df.columns}
    for cand in candidates:
        key = cand.lower().replace(" ", "").replace("-", "").replace("_", "")
        if key in norm_cols:
            return norm_cols[key]
    return None


def _auto_rename(df: pd.DataFrame) -> pd.DataFrame:
    """
    Przypina kolumny z pliku do standardowych nazw z CONFIG,
    o ile uda się je odnaleźć.
    """
    df = df.copy()
    rename_map: Dict[str, str] = {}

    # data
    if CONFIG.date_col not in df.columns:
        found = _find_col(df, DATE_CANDIDATES)
        if found:
            rename_map[found] = CONFIG.date_col

    # sku
    if CONFIG.sku_col not in df.columns:
        found = _find_col(df, SKU_CANDIDATES)
        if found:
            rename_map[found] = CONFIG.sku_col

    # ilość
    if CONFIG.qty_col not in df.columns:
        found = _find_col(df, QTY_CANDIDATES)
        if found:
            rename_map[found] = CONFIG.qty_col

    # magazyn
    if CONFIG.location_col not in df.columns:
        found = _find_col(df, LOCATION_CANDIDATES)
        if found:
            rename_map[found] = CONFIG.location_col

    if rename_map:
        df = df.rename(columns=rename_map)

    return df


# ─────────────────────────────────────────────────────────────
# Główne funkcje normalizujące
# ─────────────────────────────────────────────────────────────

def normalize_sales_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Wyspecjalizowana normalizacja dla sprzedaży.
    """
    df = _auto_rename(df)

    # data → datetime
    if CONFIG.date_col in df.columns:
        df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")

    return df


def normalize_any(df: pd.DataFrame, *, expect_qty: bool = True) -> pd.DataFrame:
    """
    Bardziej ogólna normalizacja – do użycia dla dostaw, produkcji, stanów.
    expect_qty – jeśli True, spróbujemy wymusić kolumnę ilości.
    """
    df = _auto_rename(df)

    if CONFIG.date_col in df.columns:
        df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")

    # jeśli nie ma ilości, ale nie jest wymagana – zostaw
    if expect_qty and CONFIG.qty_col not in df.columns:
        # może jest jakaś kolumna z liczbą sztuk
        pass

    return df


def force_date_column(df: pd.DataFrame, selected_col: str) -> pd.DataFrame:
    """
    Ustaw wybraną przez użytkownika kolumnę jako kolumnę daty.
    Przydaje się w UI, gdy auto-rename nie znalazł daty.
    """
    df = df.copy()
    if selected_col in df.columns:
        df = df.rename(columns={selected_col: CONFIG.date_col})
        df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")
    return df


def validate_required_cols(df: pd.DataFrame, *, require_location: bool = False) -> Dict[str, bool]:
    """
    Zwraca słownik {kolumna: czy_jest} – do pokazania w UI.
    """
    expected = [CONFIG.date_col, CONFIG.sku_col, CONFIG.qty_col]
    if require_location:
        expected.append(CONFIG.location_col)
    return {col: (col in df.columns) for col in expected}


# ─────────────────────────────────────────────────────────────
# Agregacja i przygotowanie do prognoz
# ─────────────────────────────────────────────────────────────

def aggregate_sales(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    """
    Agreguje sprzedaż do wybranej częstotliwości.
    - uzupełnia brakującą kolumnę magazynu,
    - pilnuje nazw z CONFIG,
    - zwraca ramkę z kolumną 'data' (żeby wykresy miały normalną nazwę).
    """
    df = df.copy()

    if CONFIG.date_col not in df.columns:
        # nie mamy daty – oddaj pustą ramkę
        return pd.DataFrame(columns=[CONFIG.date_col, CONFIG.sku_col, CONFIG.qty_col])

    # jeśli nie ma SKU – ciężko to sensownie zgrupować
    if CONFIG.sku_col not in df.columns:
        return pd.DataFrame(columns=[CONFIG.date_col, CONFIG.qty_col])

    # index po dacie
    df[CONFIG.date_col] = pd.to_datetime(df[CONFIG.date_col], errors="coerce")
    df = df.set_index(CONFIG.date_col)

    group_cols: List[Any] = [CONFIG.sku_col]
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


# ─────────────────────────────────────────────────────────────
# Łączenie wielu dataframe’ów tego samego typu
# ─────────────────────────────────────────────────────────────

def combine_normalized_frames(frames: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Jeśli wgraliśmy kilka plików sprzedażowych i każdy został znormalizowany,
    to tutaj możemy je bezpiecznie połączyć (outer, bez gubienia kolumn).
    """
    if not frames:
        return pd.DataFrame()
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, ignore_index=True, axis=0)


# ─────────────────────────────────────────────────────────────
# Mały helper do UI
# ─────────────────────────────────────────────────────────────

def build_missing_cols_message(valid: Dict[str, bool]) -> str:
    """
    Z prostego słownika {kolumna: True/False} buduje komunikat gotowy do pokazania.
    """
    missing = [k for k, v in valid.items() if not v]
    if not missing:
        return "✅ Wszystkie wymagane kolumny są obecne."
    return "❗ Brakuje kolumn: " + ", ".join(missing)
