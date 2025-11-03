import streamlit as st, yaml
from oi.core.utils import init_page, get_secret

init_page("Ustawienia")

st.header("⚙️ Ustawienia aplikacji")

# Sekcja: klucz OpenAI
st.subheader("🔑 OpenAI API Key")
current = st.session_state.get("OPENAI_API_KEY", "") or ""
key = st.text_input(
    "Wklej klucz (zostaje w pamięci **sesji**)",
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

# Podpowiedzi dot. trwałego zapisu
st.caption("Alternatywy (trwały zapis):")
st.code(
    """# .env
OPENAI_API_KEY=sk-...

# .streamlit/secrets.toml
[general]
OPENAI_API_KEY="sk-..."
""",
    language="ini"
)

# Status: skąd brany jest klucz?
resolved = get_secret("OPENAI_API_KEY")
if resolved:
    st.success("Klucz OpenAI jest dostępny (sesja/secrets/.env).")
else:
    st.warning("Brak klucza OpenAI — wklej w pole powyżej albo dodaj do .env / secrets.toml.")

# Podgląd configu
st.subheader("📄 Konfiguracja (read-only)")
cfg_path = "configs/config.yaml"
with open(cfg_path, "r", encoding="utf-8") as f:
    st.code(f.read(), language="yaml")
