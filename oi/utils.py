# oi/utils.py
import streamlit as st
from datetime import datetime

def kill_streamlit_nav_header() -> None:
    st.markdown(
        """
        <style>
            header {visibility: hidden;}
            .block-container {padding-top: 1.5rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )

def init_session_state() -> None:
    if "initialization_time" not in st.session_state:
        st.session_state.initialization_time = datetime.now()
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {
            "sprzedaz": None,
            "dostawy": None,
            "produkcja": None,
            "stany": None,
        }
    if "OPENAI_API_KEY" not in st.session_state:
        st.session_state.OPENAI_API_KEY = ""
