# pages/03_📦_Rekomendacje.py
import streamlit as st
from oi.ui_components import render_topbar, render_alert
from oi.optimization import build_inventory_recommendation
from oi.config import CONFIG

st.set_page_config(page_title="Rekomendacje", page_icon="📦", layout="wide")

render_topbar("📦 Rekomendacje zatowarowania", "ROP, safety stock, EOQ")

lf = st.session_state.get("last_forecast")

if not lf:
    render_alert("Brak prognozy w sesji. Najpierw wygeneruj prognozę w zakładce 'Prognozy'.", "warn")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        current_stock = st.number_input("Aktualny stan magazynu (szt.)", min_value=0.0, value=100.0, step=10.0)
    with c2:
        service_level = st.slider("Poziom obsługi", 0.5, 0.999, 0.95)
    with c3:
        lead_time_days = st.number_input("Czas dostawy (dni)", min_value=1, value=7, step=1)

    order_cost = st.number_input("Koszt złożenia zamówienia (PLN)", min_value=1.0, value=50.0)
    holding_cost = st.number_input("Miesięczny koszt utrzymania 1 szt. (PLN)", min_value=0.1, value=2.0)

    rec = build_inventory_recommendation(
        forecast_df=lf["forecast"],
        current_stock=current_stock,
        lead_time_days=lead_time_days,
        service_level=service_level,
        order_cost=order_cost,
        holding_cost=holding_cost,
    )

    st.subheader("📋 Wynik")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Szac. dzienne zużycie", f"{rec['daily_demand_est']:.2f} szt.")
    col2.metric("Zapas bezpieczeństwa", f"{rec['safety_stock']:.0f} szt.")
    col3.metric("Punkt zamówienia (ROP)", f"{rec['reorder_point']:.0f} szt.")
    col4.metric("EOQ", f"{rec['eoq']:.0f} szt.")

    if rec["suggested_order_qty"] > 0:
        st.success(f"✅ Zalecane zamówienie: **{rec['suggested_order_qty']:.0f} szt.**")
    else:
        st.info("Brak konieczności zamawiania na teraz.")

    # AI Copilot
    st.markdown("### 🤖 AI Asystent magazynowy")
    user_q = st.text_input("Zadaj pytanie (np. dlaczego taki ROP?)")
    if user_q:
        from oi.ai_assistant import answer_question
        ai_ans = answer_question(user_q, context={
            "sku": lf["sku"],
            "magazyn": lf["location"],
            "forecast_mean": float(lf["forecast"].mean()),
            "reorder_point": float(rec["reorder_point"]),
            "safety_stock": float(rec["safety_stock"]),
            "suggested_order_qty": float(rec["suggested_order_qty"]),
        })
        st.markdown(ai_ans)
