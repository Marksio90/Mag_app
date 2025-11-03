# oi/data_ingestion.py
from __future__ import annotations

import io
import os
from typing import Optional, Dict, List, Any, Tuple

import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────
# Helpers do wczytywania
# ─────────────────────────────────────────────────────────────

def _detect_sep(sample: bytes) -> str:
    """
    Próbuje zgadnąć separator na podstawie pierwszych linii.
    Jeśli się nie uda – wraca przecinek.
    """
    text = sample.decode("utf-8", errors="ignore")
    candidates = [",", ";", "\t", "|"]
    counts = {sep: text.count(sep) for sep in candidates}
    # weź ten, który występuje najczęściej
    best = max(counts, key=counts.get)
    return best or ","


def _read_csv_smart(uploaded_file) -> pd.DataFrame:
    """
    Wczytuje CSV z auto-wykryciem separatora.
    """
    # wczytaj kawałek
    sample = uploaded_file.read(4096)
    sep = _detect_sep(sample)
    # cofnij wskaźnik, żeby pandas mógł czytać od początku
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file, sep=sep, engine="python")


def _read_excel_smart(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file)


def load_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Uniwersalne wczytywanie pojedynczego pliku do DataFrame.
    Obsługuje CSV i Excel.
    """
    if uploaded_file is None:
        return None
    suffix = uploaded_file.name.split(".")[-1].lower()
    if suffix in ("xls", "xlsx"):
        return _read_excel_smart(uploaded_file)
    else:
        return _read_csv_smart(uploaded_file)


def _preview_df(df: pd.DataFrame, label: str) -> None:
    """
    Pokazuje mały podgląd w UI – żeby od razu było widać,
    czy wczytało się to, co trzeba.
    """
    with st.expander(f"Podgląd: {label}", expanded=False):
        st.dataframe(df.head(50))


# ─────────────────────────────────────────────────────────────
# Główna sekcja uploadu
# ─────────────────────────────────────────────────────────────

def upload_data_section() -> Dict[str, Any]:
    """
    Renderuje w UI sekcję wgrywania danych i zwraca słownik z DataFrame’ami
    oraz metadanymi. Dane trafiają też do st.session_state.uploaded_data.

    Zwracana struktura:
    {
        "sprzedaz": [df1, df2, ...] albo None,
        "dostawy": [...],
        "produkcja": [...],
        "stany": [...],
        "_meta": {...}
    }
    """
    st.subheader("📥 Załaduj dane źródłowe")

    st.caption(
        "Możesz wgrać kilka plików dla jednego typu (np. sprzedaż z różnych systemów). "
        "Aplikacja później je zmerguje po kolumnach, które rozpozna."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Formaty:** CSV, XLSX")
    with c2:
        st.write("**Wskazówka:** nazwy kolumn mogą być różne – później je znormalizujemy.")

    # pozwalamy na multiple=True
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        f_sprz_list = st.file_uploader(
            "Sprzedaż (min. 1)", type=["csv", "xlsx"], key="sprzedaz_upl", accept_multiple_files=True
        )
    with c2:
        f_dost_list = st.file_uploader(
            "Dostawy", type=["csv", "xlsx"], key="dostawy_upl", accept_multiple_files=True
        )
    with c3:
        f_prod_list = st.file_uploader(
            "Produkcja", type=["csv", "xlsx"], key="produkcja_upl", accept_multiple_files=True
        )
    with c4:
        f_stan_list = st.file_uploader(
            "Stany magazynowe", type=["csv", "xlsx"], key="stany_upl", accept_multiple_files=True
        )

    def _load_many(files: List[Any], label: str) -> List[pd.DataFrame]:
        dfs: List[pd.DataFrame] = []
        for f in files or []:
            try:
                df = load_uploaded_file(f)
            except Exception as exc:  # pragma: no cover – defensywnie
                st.error(f"❗ Nie udało się wczytać pliku {f.name} ({label}): {exc}")
                continue
            else:
                dfs.append(df)
                _preview_df(df, f"{label}: {f.name}")
        return dfs

    sprzedaz_dfs = _load_many(f_sprz_list, "sprzedaż")
    dostawy_dfs = _load_many(f_dost_list, "dostawy")
    produkcja_dfs = _load_many(f_prod_list, "produkcja")
    stany_dfs = _load_many(f_stan_list, "stany")

    # meta – przydatne do debug/podglądów
    meta = {
        "sprzedaz_files": [f.name for f in (f_sprz_list or [])],
        "dostawy_files": [f.name for f in (f_dost_list or [])],
        "produkcja_files": [f.name for f in (f_prod_list or [])],
        "stany_files": [f.name for f in (f_stan_list or [])],
    }

    # zapis do sesji w formie przyjaznej dalszym modułom
    st.session_state.uploaded_data = {
        "sprzedaz": sprzedaz_dfs if sprzedaz_dfs else None,
        "dostawy": dostawy_dfs if dostawy_dfs else None,
        "produkcja": produkcja_dfs if produkcja_dfs else None,
        "stany": stany_dfs if stany_dfs else None,
        "_meta": meta,
    }

    return st.session_state.uploaded_data


# ─────────────────────────────────────────────────────────────
# Dodatkowe pomocnicze funkcje do łączenia wielu DF
# ─────────────────────────────────────────────────────────────

def concat_frames(frames: Optional[List[pd.DataFrame]]) -> Optional[pd.DataFrame]:
    """
    Jeśli mamy listę DF (np. kilka plików sprzedażowych), łączymy je w jeden.
    Jeśli None – zwracamy None.
    """
    if not frames:
        return None
    if len(frames) == 1:
        return frames[0]
    # alignuj kolumny przez outer join – żeby nie gubić info
    return pd.concat(frames, ignore_index=True, axis=0)
