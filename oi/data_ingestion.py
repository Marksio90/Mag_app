# oi/data_ingestion.py
from __future__ import annotations
import pandas as pd
from typing import Optional, Dict
import streamlit as st

def load_uploaded_file(uploaded_file) -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    suffix = uploaded_file.name.split(".")[-1].lower()
    if suffix in ("xls", "xlsx"):
        return pd.read_excel(uploaded_file)
    else:
        return pd.read_csv(uploaded_file, sep=None, engine="python")

def upload_data_section() -> Dict[str, Optional[pd.DataFrame]]:
    st.subheader("📥 Załaduj dane")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        f_sprz = st.file_uploader("Sprzedaż (obowiązkowe)", type=["csv", "xlsx"], key="sprzedaz_upl")
    with c2:
        f_dost = st.file_uploader("Dostawy", type=["csv", "xlsx"], key="dostawy_upl")
    with c3:
        f_prod = st.file_uploader("Produkcja", type=["csv", "xlsx"], key="produkcja_upl")
    with c4:
        f_stan = st.file_uploader("Stany magazynowe", type=["csv", "xlsx"], key="stany_upl")

    sprzedaz = load_uploaded_file(f_sprz)
    dostawy = load_uploaded_file(f_dost)
    produkcja = load_uploaded_file(f_prod)
    stany = load_uploaded_file(f_stan)

    st.session_state.uploaded_data = {
        "sprzedaz": sprzedaz,
        "dostawy": dostawy,
        "produkcja": produkcja,
        "stany": stany,
    }

    return st.session_state.uploaded_data
