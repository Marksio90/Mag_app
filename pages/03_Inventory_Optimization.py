
import streamlit as st, polars as pl, numpy as np, plotly.graph_objects as go
from oi.core.utils import init_page
from oi.core.data_io import read_csv
from oi.core.inventory import calc_policy
from oi.core.optimizer import optimize_service_level
from oi.core.recommender import business_reco

init_page("Inventory Optimization")
st.header("📐 Inventory Optimization & Policy Tuning")

sales = st.session_state.get("sales_df") or read_csv("oi/data/sample_sales.csv").with_columns(pl.col("date").str.strptime(pl.Date, strict=False))
lead  = st.session_state.get("lt_df") or read_csv("oi/data/sample_leadtimes.csv")
inv   = st.session_state.get("inv_df") or read_csv("oi/data/sample_inventory.csv")

skus = sales["sku"].unique().to_list()
sku = st.selectbox("SKU", skus, index=0)

s = sales.filter(pl.col("sku")==sku).sort("date")["qty"].to_list()
weekly_mean = float(np.mean(s))
weekly_std  = float(np.std(s, ddof=1) if len(s)>1 else 0.0)
m = lead.filter(pl.col("sku")==sku)
lead_mean = float(m["lead_time_days_mean"][0]) if m.height>0 else 14.0
lead_std  = float(m["lead_time_days_std"][0]) if m.height>0 else 3.0
moq       = float(m["min_order_qty"][0]) if m.height>0 else 0.0

service = st.slider("Poziom serwisu (policy)", 0.90, 0.999, 0.95)
holding = st.number_input("Koszt utrzymania [%/rok] od ceny", 0.01, 1.0, 0.2)
ordering = st.number_input("Koszt zamówienia [PLN]", 1.0, 10000.0, 150.0, step=10.0)
unit_cost = st.number_input("Koszt jednostkowy [PLN]", 0.1, 10000.0, 10.0)
penalty = st.number_input("Kara za brak [PLN/szt.]", 0.0, 1000.0, 25.0)

res = calc_policy(weekly_mean, weekly_std, lead_mean, lead_std, service, holding, ordering, unit_cost, moq)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Safety Stock", f"{res.safety_stock:.0f}")
col2.metric("Reorder Point", f"{res.reorder_point:.0f}")
col3.metric("EOQ", f"{res.eoq:.0f}")
col4.metric("Zalecana partia", f"{res.order_qty:.0f}")

st.subheader("🎯 Optymalizacja kosztowa (service level)")
opt = optimize_service_level(weekly_mean, weekly_std, lead_mean, lead_std, unit_cost, moq,
                             holding_rate=holding, ordering_cost=ordering, penalty_per_unit=penalty)
st.json({"best_service_level": opt["best_service_level"], "best_cost": round(opt["best_cost"],2),
         "orders_per_year": round(opt["orders_per_year"],2),
         "holding": round(opt["holding"],2), "ordering": round(opt["ordering"],2), "stockout": round(opt["stockout"],2)})

st.subheader("🧠 Rekomendacje (OpenAI)")
ctx = {"sku": sku, "weekly_mean": weekly_mean, "weekly_std": weekly_std,
       "lead": {"mean_days": lead_mean, "std_days": lead_std}, "moq": moq,
       "policy_current": res.__dict__, "policy_opt": {"service_level": opt["best_service_level"], "cost": opt["best_cost"]}}
if st.button("Generuj rekomendacje"):
    st.write(business_reco(ctx))

# Symulacja stanów (8 tyg.) z ROP
on_hand = inv.filter(pl.col("sku")==sku)["on_hand"]
on_hand = float(on_hand[0]) if on_hand.height>0 else 300.0
weeks = list(range(1,9))
pos = on_hand; cons = weekly_mean
orders = []; stock = [pos]
for w in weeks:
    pos -= cons
    if pos <= res.reorder_point:
        pos += res.order_qty
        orders.append({"week": w, "qty": res.order_qty})
    stock.append(pos)

fig = go.Figure()
fig.add_bar(x=weeks, y=stock[1:], name="Proj. stan")
fig.update_layout(height=360, template="plotly_dark", title=f"Symulacja zapasu — {sku}")
st.plotly_chart(fig, use_container_width=True)
