
import streamlit as st
from oi.core.utils import init_page

init_page("Główna strona — Optimal Inventory Planner")
st.title("🏠 Główna strona")
st.caption("Prognozy • Backtesty • SS/ROP/EOQ • Fill‑rate • Optymalizacja kosztów • Scoring dostawców • PDF/PPTX • MLflow • Optuna")

st.markdown("""
<div class="dg-card">
  <span class="dg-badge">v3</span>
  <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:.5rem">
    <div><div class="metric">🔁 Backtesty</div><div class="small dg-muted">MAPE / RMSE / RMSSE</div></div>
    <div><div class="metric">🎯 Fill-rate</div><div class="small dg-muted">optymalizacja</div></div>
    <div><div class="metric">🧠 Optuna</div><div class="small dg-muted">dobór algorytmu</div></div>
    <div><div class="metric">📈 MLflow</div><div class="small dg-muted">logi eksperymentów</div></div>
    <div><div class="metric">📄 PDF/PPTX</div><div class="small dg-muted">Executive</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
st.info("Użyj menu **Pages** po lewej, aby przejść do modułów.")
