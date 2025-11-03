# pages/01_📊_Dashboard.py
import streamlit as st
from oi.ui_components import render_topbar, render_alert
from oi.data_ingestion import upload_data_section
from oi.preprocessing import normalize_sales_df, aggregate_sales, force_date_column

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

render_topbar("📊 Dashboard", "Bieżąca sytuacja magazynowa i popytowa")
data = upload_data_section()

sprzedaz = data["sprzedaz"]

if sprzedaz is None:
    render_alert("Załaduj przynajmniej plik sprzedażowy, żeby zobaczyć KPI.", "warn")
else:
    sprzedaz = normalize_sales_df(sprzedaz)

    # jeśli po normalizacji wciąż nie ma kolumny 'data' – daj użytkownikowi wybór
    if "data" not in sprzedaz.columns:
        render_alert("Nie znalazłem automatycznie kolumny z datą. Wybierz ją ręcznie poniżej 👇", "err")
        col_to_pick = st.selectbox(
            "Wybierz kolumnę, która jest datą:",
            sprzedaz.columns.tolist(),
        )
        sprzedaz = force_date_column(sprzedaz, col_to_pick)

    # jeśli nadal nie da się sparsować – pokaż i zakończ
    if "data" not in sprzedaz.columns or sprzedaz["data"].isna().all():
        render_alert("Wybrana kolumna nie wygląda na daty (same NaN po konwersji). Sprawdź format w pliku.", "err")
        st.dataframe(sprzedaz.head())
    else:
        agg_w = aggregate_sales(sprzedaz, freq="W")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Liczba rekordów sprzedaży", len(sprzedaz))
        with col2:
            st.metric("Liczba SKU", sprzedaz["sku"].nunique() if "sku" in sprzedaz.columns else 0)
        with col3:
            st.metric("Okres danych", f"{sprzedaz['data'].min().date()} – {sprzedaz['data'].max().date()}")
        with col4:
            st.metric("Magazyny", sprzedaz["magazyn"].nunique() if "magazyn" in sprzedaz.columns else 1)

        st.subheader("📈 Sprzedaż tygodniowa (agregowana)")
        if not agg_w.empty:
            st.line_chart(agg_w.pivot_table(index="data", values="ilosc", aggfunc="sum"))
        else:
            st.write("Brak danych po agregacji – sprawdź czy kolumna ilości została rozpoznana.")
