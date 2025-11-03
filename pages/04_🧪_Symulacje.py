# pages/04_🧪_Symulacje.py
import streamlit as st
from oi.ui_components import render_topbar, render_alert
from oi.simulation import monte_carlo_stockout

st.set_page_config(page_title="Symulacje", page_icon="🧪", layout="wide")

render_topbar("🧪 Symulacje i scenariusze", "Monte Carlo na popycie")

lf = st.session_state.get("last_forecast")

if not lf:
    render_alert("Brak prognozy w sesji. Wygeneruj ją najpierw.", "warn")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        current_stock = st.number_input("Aktualny stan magazynu", min_value=0.0, value=120.0)
    with c2:
        lead_time_days = st.number_input("Czas dostawy (dni)", min_value=1, value=7)
    with c3:
        n_sim = st.slider("Liczba symulacji", 100, 2000, 500, step=100)

    volatility = st.slider("Zmienność popytu", 0.01, 0.5, 0.15, step=0.01)

    res = monte_carlo_stockout(
        forecast=lf["forecast"],
        current_stock=current_stock,
        lead_time_days=lead_time_days,
        n_sim=n_sim,
        demand_volatility=volatility,
    )

    st.metric("Prawdopodobieństwo stock-out", f"{res['prob_stockout']*100:.1f}%")
    st.metric("Średni zapas końcowy", f"{res['avg_ending_stock']:.1f} szt.")
    st.metric("Min zapas końcowy", f"{res['min_ending_stock']:.1f} szt.")
    st.metric("Max zapas końcowy", f"{res['max_ending_stock']:.1f} szt.")

    st.caption("Możesz użyć tego do testowania różnych polityk uzupełnień.")
