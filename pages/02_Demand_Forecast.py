
import streamlit as st, polars as pl, plotly.graph_objects as go
from oi.core.utils import init_page
from oi.core.forecasting import forecast
from oi.core.backtest import rolling_backtest
from oi.core.data_io import read_csv

init_page("Demand Forecast")
st.header("🔮 Demand Forecast & Backtest")

df = st.session_state.get("sales_df") or read_csv("oi/data/sample_sales.csv").with_columns(pl.col("date").str.strptime(pl.Date, strict=False))
skus = df["sku"].unique().to_list()
sku = st.selectbox("SKU", skus)
h = st.slider("Horyzont (tyg.)", 4, 26, 12)
algo = st.selectbox("Algorytm", ["sarimax","holt","sma","naive"])

res = forecast(df, sku, h, algo)
hist = res.history; fc = res.forecast

fig = go.Figure()
fig.add_scatter(y=hist, mode="lines+markers", name="History")
fig.add_scatter(y=[None]*(len(hist)-1)+[hist[-1]]+list(fc), mode="lines+markers", name="Forecast")
fig.update_layout(height=420, template="plotly_dark", title=f"{sku} — {res.model}")
st.plotly_chart(fig, use_container_width=True)

st.subheader("🔁 Backtest (rolling)")
series = df.filter(pl.col("sku")==sku).sort("date")["qty"].to_list()
bt = rolling_backtest(series, horizon=min(4,h), window=12)
st.json(bt)
st.caption(f"Najlepszy algorytm wg RMSSE: **{bt['best_algo']}**")
