
import streamlit as st, polars as pl, plotly.graph_objects as go, json, os
from oi.core.utils import init_page
from oi.core.data_io import read_csv
from oi.core.exporting import export_pdf, export_pptx

init_page("Reports & Export")
st.header("📤 Reports & Export (PDF/PPTX)")

sales = read_csv("oi/data/sample_sales.csv").with_columns(pl.col("date").str.strptime(pl.Date, strict=False))
skus = sales["sku"].unique().to_list()
sku = st.selectbox("SKU do raportu", skus)

series = sales.filter(pl.col("sku")==sku).sort("date")["qty"].to_list()

fig = go.Figure()
fig.add_scatter(y=series, mode="lines+markers", name="History")
fig.update_layout(height=360, template="plotly_dark", title=f"{sku} — historia popytu")

tables = [{"title": "Parametry", "data": {"sku": sku, "obserwacje": len(series)}}]

col1, col2 = st.columns(2)
with col1:
    if st.button("Eksport do PDF"):
        path = "reports/inventory_report.pdf"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        export_pdf(path, f"Raport — {sku}", [fig], tables)
        with open(path, "rb") as f:
            st.download_button("Pobierz PDF", data=f.read(), file_name="inventory_report.pdf", mime="application/pdf")
with col2:
    if st.button("Eksport do PPTX"):
        path = "reports/inventory_report.pptx"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        export_pptx(path, f"Raport — {sku}", [fig], tables)
        with open(path, "rb") as f:
            st.download_button("Pobierz PPTX", data=f.read(), file_name="inventory_report.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")
