
import streamlit as st, polars as pl
from oi.core.utils import init_page
from oi.core.data_io import read_csv
from oi.core.recommender import supplier_reco

init_page("Supplier Scoring")
st.header("🏭 Supplier Scoring")

sup = st.session_state.get("sup_df") or read_csv("oi/data/sample_suppliers.csv")

weights = {
    "sla_on_time_pct": st.slider("Waga: Terminowość", 0.0, 1.0, 0.35),
    "defect_rate_pct": st.slider("Waga: Jakość (odwrotność)", 0.0, 1.0, 0.25),
    "unit_cost_index": st.slider("Waga: Koszt", 0.0, 1.0, 0.20),
    "partnership_tier": st.slider("Waga: Partnerstwo", 0.0, 1.0, 0.20),
}

def tier_score(v:str)->float:
    return {"gold":1.0,"silver":0.8,"bronze":0.6}.get(str(v).lower(), 0.5)

rows = []
for r in sup.iter_rows(named=True):
    s = r["sla_on_time_pct"]
    q = 1.0 - r["defect_rate_pct"]/100.0
    c = 1.0 / max(1e-9, r["unit_cost_index"])
    t = tier_score(r["partnership_tier"])
    score = (weights["sla_on_time_pct"]*s + weights["defect_rate_pct"]*q + weights["unit_cost_index"]*c + weights["partnership_tier"]*t)
    rows.append({"supplier": r["supplier"], "score": score, **r})

df = pl.DataFrame(rows).sort("score", descending=True)
st.dataframe(df)

if st.button("Rekomendacje OpenAI"):
    st.write(supplier_reco([dict(x) for x in df.iter_rows(named=True)]))
