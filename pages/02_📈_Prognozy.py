# pages/02_📈_Prognozy.py
import streamlit as st
from oi.ui_components import render_topbar, render_alert
from oi.preprocessing import normalize_sales_df, aggregate_sales
from oi.forecasting import forecast_sku
from oi.config import CONFIG

st.set_page_config(page_title="Prognozy", page_icon="📈", layout="wide")

render_topbar("📈 Prognozy popytu", "ML / TS / fallback")

sprzedaz = st.session_state.uploaded_data.get("sprzedaz")

if sprzedaz is None:
    render_alert("Brak danych sprzedażowych. Przejdź do Dashboard i załaduj.", "err")
else:
    sprzedaz = normalize_sales_df(sprzedaz)
    freq = st.selectbox("Częstotliwość agregacji", ["W", "M", "D"], index=0)
    agg = aggregate_sales(sprzedaz, freq=freq)

    sku_list = agg[CONFIG.sku_col].unique().tolist()
    sku = st.selectbox("Wybierz SKU", sku_list)
    location = None
    if CONFIG.location_col in agg.columns:
        locs = ["(wszystkie)"] + agg[CONFIG.location_col].dropna().unique().tolist()
        location_sel = st.selectbox("Magazyn", locs)
        if location_sel != "(wszystkie)":
            location = location_sel

    horizon = st.slider("Horyzont prognozy (okresy)", 4, 52, 12)
    res = forecast_sku(agg, sku=sku, location=location, periods=horizon, freq=freq)

    if res["forecast"] is None:
        render_alert("Brak danych dla tego SKU/magazynu", "warn")
    else:
        tab1, tab2 = st.tabs(["Wykres", "Tabelka"])
        history = res["history"]
        forecast = res["forecast"]

        with tab1:
            chart_df = (
                history.rename("history")
                .to_frame()
                .join(forecast.rename("forecast"), how="outer")
            )
            st.line_chart(chart_df)
        with tab2:
            st.dataframe(
                forecast.rename("prognoza").to_frame().reset_index().rename(columns={"index": "okres"})
            )

        st.success("Prognoza wygenerowana. Możesz teraz przejść do zakładki Rekomendacje.")
        st.session_state["last_forecast"] = {
            "sku": sku,
            "location": location,
            "freq": freq,
            "history": history,
            "forecast": forecast,
        }
