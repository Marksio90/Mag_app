# pages/05_⚙️_Ustawienia.py
import streamlit as st
from oi.ui_components import render_topbar

st.set_page_config(page_title="Ustawienia", page_icon="⚙️", layout="wide")

render_topbar("⚙️ Ustawienia", "Klucze, parametry domyślne, tryb lokalny")

st.subheader("🔑 OpenAI API Key")
current = st.session_state.get("OPENAI_API_KEY", "")
key = st.text_input(
    "Wklej klucz (zostaje w pamięci sesji)", 
    value=current, 
    type="password",
    help="Do trwałego zapisu użyj .env lub .streamlit/secrets.toml"
)
col1, col2 = st.columns(2)
with col1:
    if st.button("Zapisz klucz w sesji"):
        if key.strip():
            st.session_state["OPENAI_API_KEY"] = key.strip()
            st.success("Zapisano klucz dla bieżącej sesji.")
        else:
            st.warning("Klucz jest pusty.")
with col2:
    if st.button("Wyczyść klucz z sesji"):
        st.session_state.pop("OPENAI_API_KEY", None)
        st.info("Usunięto klucz z sesji.")

st.subheader("ℹ️ Info")
st.markdown(
    """
    - Aplikacja działa **lokalnie**.
    - Moduły są rozdzielone – możesz je rozwijać (np. podmiana forecastingu na Prophet/neuralforecast).
    - Dane nie są wysyłane na zewnątrz, chyba że pytasz OpenAI i podasz klucz.
    """
)
