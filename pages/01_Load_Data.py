
import streamlit as st, polars as pl
from oi.core.utils import init_page
from oi.core.data_io import read_csv

init_page("Load Data")
st.header("📥 Load Data")

st.write("Kolumny:")
st.code("sales: date, warehouse, sku, qty\ninventory: warehouse, sku, on_hand, on_order\nleadtimes: supplier, sku, lead_time_days_mean, lead_time_days_std, min_order_qty\nsuppliers: supplier, name, partnership_tier, sla_on_time_pct, defect_rate_pct, unit_cost_index")

src = st.radio("Źródło", ["Przykładowe", "Wgrywam własne"], horizontal=True)
if src=="Wgrywam własne":
    sales = st.file_uploader("sales.csv", type=["csv"])
    inv = st.file_uploader("inventory.csv", type=["csv"])
    lt = st.file_uploader("leadtimes.csv", type=["csv"])
    sup = st.file_uploader("suppliers.csv", type=["csv"])
    if sales: st.session_state["sales_df"] = read_csv(sales)
    if inv: st.session_state["inv_df"] = read_csv(inv)
    if lt: st.session_state["lt_df"] = read_csv(lt)
    if sup: st.session_state["sup_df"] = read_csv(sup)
    st.success("Pliki wczytane do sesji.")
else:
    import polars as pl
    st.session_state["sales_df"] = read_csv("oi/data/sample_sales.csv").with_columns(pl.col("date").str.strptime(pl.Date, strict=False))
    st.session_state["inv_df"] = read_csv("oi/data/sample_inventory.csv")
    st.session_state["lt_df"]  = read_csv("oi/data/sample_leadtimes.csv")
    st.session_state["sup_df"] = read_csv("oi/data/sample_suppliers.csv")
    st.success("Załadowano dane przykładowe.")

if "sales_df" in st.session_state:
    st.subheader("Podgląd: sales")
    st.dataframe(st.session_state["sales_df"].head(10))
