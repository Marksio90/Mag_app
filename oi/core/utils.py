
from __future__ import annotations
import os
from typing import Optional
from dotenv import load_dotenv
import streamlit as st

def init_page(title: str):
    st.set_page_config(page_title=title, page_icon="📦", layout="wide")
    st.markdown('<style>'+open("oi/assets/theme.css","r", encoding="utf-8").read()+'</style>', unsafe_allow_html=True)

def get_secret(name: str) -> Optional[str]:
    # 1) Runtime (Settings page) — sesja użytkownika
    if name in st.session_state and st.session_state.get(name):
        return st.session_state.get(name)
    # 2) Streamlit secrets
    if "secrets" in dir(st) and name in st.secrets:
        return st.secrets.get(name)  # type: ignore
    # 3) .env
    load_dotenv()
    return os.getenv(name)
