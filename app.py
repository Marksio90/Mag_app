# app.py
import streamlit as st
from oi.utils import kill_streamlit_nav_header, init_session_state
from oi.ui_components import render_topbar

st.set_page_config(
    page_title="Optymalizacja zatowarowania 2025",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

kill_streamlit_nav_header()
init_session_state()

render_topbar(title="📦 Zaawansowana aplikacja do prognozowania i optymalizacji zatowarowania", subtitle="AI + ML + symulacje + rekomendacje zakupowe")

st.markdown(
    """
    Wybierz moduł z lewego paska bocznego.  
    - **Dashboard** – bieżący stan, KPI, alerty  
    - **Prognozy** – modele ML/TS, podgląd SKU  
    - **Rekomendacje** – ROP, safety stock, EOQ  
    - **Symulacje** – Monte Carlo, co-jeśli  
    - **Ustawienia** – klucz OpenAI, parametry domyślne
    """
)
