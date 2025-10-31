
from __future__ import annotations
import io, re, json, base64
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Optional deps
STATS_OK = True
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.tsa.seasonal import STL
except Exception:
    STATS_OK = False

from reports.generate_report import build_pdf, build_pptx

st.set_page_config(page_title="Zatowarowanie – Executive AI Suite v6.1", layout="wide")
st.title("👑📦 Zatowarowanie – Executive AI Suite (v6.1)")

BASE = Path(".")
ASSETS = BASE / "assets"
LOGO_PATH = str(ASSETS / "logo_biadvice.png")
BRAND_PATH = str(ASSETS / "branding.json")

# Try load branding
branding = {}
if Path(BRAND_PATH).exists():
    try:
        branding = json.loads(Path(BRAND_PATH).read_text(encoding="utf-8"))
    except Exception:
        branding = {}

pal = branding.get("palette", {})
plotly_theme = branding.get("plotly", {})
colorway = plotly_theme.get("colorway", ["#14b8a6","#f59e0b","#60a5fa","#f472b6","#a78bfa","#34d399","#f87171"])

# Sidebar: upload logo & save to assets
st.sidebar.header("Branding")
logo_upload = st.sidebar.file_uploader("Wgraj logo (PNG/SVG)", type=["png","svg"])
if logo_upload:
    Path(LOGO_PATH).write_bytes(logo_upload.read())
    st.sidebar.success("Logo zaktualizowane.")

# Params
st.sidebar.header("Parametry serwisu / koszty")
service_level = st.sidebar.selectbox("Poziom serwisu", [0.90,0.95,0.975,0.99], index=1)
Z = {0.90:1.2816, 0.95:1.6449, 0.975:1.9599, 0.99:2.3263}[service_level]
LT_default = st.sidebar.number_input("Domyślny LT (tyg.)", 0.5, 26.0, 2.0, 0.5)
K_default = st.sidebar.number_input("K (PLN/zam.)", 0.0, 5000.0, 200.0, 10.0)
h_pct = st.sidebar.number_input("h (% wartości/tydzień)", 0.0, 10.0, 0.5, 0.1)
inter_method = st.sidebar.selectbox("Metoda intermittent", ["SBA","Croston","TSB"], index=0)

# Uploads
c1,c2,c3 = st.columns(3)
with c1: up_asort = st.file_uploader("Asort/Towar", type=["csv"])
with c2: up_sprz  = st.file_uploader("Sprzedaż", type=["csv"])
with c3: up_docs  = st.file_uploader("Dok/PozDok", type=["csv"], accept_multiple_files=True)

def read_csv_any_bytes(data: bytes) -> pd.DataFrame:
    sep = ";" if (b";" in data[:1024] and data.count(b";") >= data.count(b",")) else ","
    return pd.read_csv(io.BytesIO(data), sep=sep, encoding_errors="ignore", low_memory=False)
def read_csv_any_path(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists(): return None
    with open(path, "rb") as f:
        head = f.read(4096)
    sep = ";" if (b";" in head and head.count(b";") >= head.count(b",")) else ","
    return pd.read_csv(path, sep=sep, encoding_errors="ignore", low_memory=False)
def infer_cols(df: pd.DataFrame):
    def infer_date(df):
        cand = [c for c in df.columns if re.search(r"data|date|czas|timestamp", c, re.IGNORECASE)]
        for c in cand or df.columns.tolist():
            s = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
            if s.notna().mean()>0.3: return c
        return cand[0] if cand else df.columns[0]
    def infer_qty(df):
        poss = [c for c in df.columns if re.search(r"(ilo|qty|quantity)", c, re.IGNORECASE)]
        for c in poss:
            if pd.api.types.is_numeric_dtype(df[c]): return c
        for c in df.columns:
            if pd.api.types.is_numeric_dtype(df[c]): return c
        return df.columns[0]
    def infer_sku(df):
        poss = [c for c in df.columns if re.search(r"(sku|kod|symbol|tow|id[_ ]*tow|index|produkt)", c, re.IGNORECASE)]
        return poss[0] if poss else df.columns[0]
    return infer_date(df), infer_qty(df), infer_sku(df)

df_sprz = read_csv_any_bytes(up_sprz.read()) if up_sprz else read_csv_any_path(Path("Sprzedaż.csv"))
df_asort = read_csv_any_bytes(up_asort.read()) if up_asort else (read_csv_any_path(Path("Asort.csv")) or read_csv_any_path(Path("Towar.csv")))
df_dok, df_pozdok = None, None
if up_docs and len(up_docs)>=1:
    dfs = [read_csv_any_bytes(f.read()) for f in up_docs]
    dfs = sorted(dfs, key=lambda d: d.shape[1])
    df_dok = dfs[0]; df_pozdok = dfs[-1] if len(dfs)>1 else None
else:
    df_dok = read_csv_any_path(Path("Dok.csv"))
    df_pozdok = read_csv_any_path(Path("PozDok.csv"))

if df_sprz is None or df_sprz.empty:
    st.error("Brak Sprzedaż.csv"); st.stop()

dcol,qcol,scol = infer_cols(df_sprz)
raw = pd.DataFrame({
    "data": pd.to_datetime(df_sprz[dcol], errors="coerce", dayfirst=True),
    "sku":  df_sprz[scol].astype(str).str.strip(),
    "ilosc": pd.to_numeric(df_sprz[qcol], errors="coerce").fillna(0),
})
value_c = next((c for c in df_sprz.columns if re.search(r"(wartosc|value|amount)", c, re.IGNORECASE)), None)
price_c = next((c for c in df_sprz.columns if re.search(r"(cena|price)", c, re.IGNORECASE)), None)
if value_c: raw["wartosc"] = pd.to_numeric(df_sprz[value_c], errors="coerce").fillna(0)
elif price_c: raw["wartosc"] = pd.to_numeric(df_sprz[price_c], errors="coerce") * raw["ilosc"]
else: raw["wartosc"] = raw["ilosc"]
raw = raw.dropna(subset=["data"]); raw = raw[raw["ilosc"]>=0]; raw["tydzien"] = raw["data"].dt.to_period("W").dt.start_time

if df_asort is not None and not df_asort.empty:
    def pick(df, pat):
        for c in df.columns:
            if re.search(pat, c, re.IGNORECASE): return c
        return None
    sku_c = pick(df_asort, r"(sku|kod|symbol|tow|id[_ ]*tow|index)") or df_asort.columns[0]
    name_c = pick(df_asort, r"(nazwa|name|opis)")
    cat_c  = pick(df_asort, r"(kateg|grupa|segment|typ)")
    asort = pd.DataFrame({"sku": df_asort[sku_c].astype(str).str.strip()})
    asort["nazwa"] = df_asort[name_c] if name_c else np.nan
    asort["kategoria"] = df_asort[cat_c] if cat_c else np.nan
else:
    asort = pd.DataFrame(columns=["sku","nazwa","kategoria"])

# KPIs
k1,k2,k3,k4 = st.columns(4)
k1.metric("Rekordów", f"{len(raw):,}")
k2.metric("SKU", f"{raw['sku'].nunique():,}")
k3.metric("Zakres", f"{raw['data'].min().date()} → {raw['data'].max().date()}")
k4.metric("Zero ilości", f"{int((raw['ilosc']==0).sum()):,}")

# Weekly full
week = raw.groupby(["sku","tydzien"], as_index=False)[["ilosc","wartosc"]].sum()
import pandas as pd
weeks_span = pd.date_range(week["tydzien"].min(), week["tydzien"].max(), freq="W-MON")
template = pd.MultiIndex.from_product([week["sku"].unique(), weeks_span], names=["sku","tydzien"])
week_full = week.set_index(["sku","tydzien"]).reindex(template, fill_value=0).reset_index()

# Stats + ABC
val_by_sku = raw.groupby("sku", as_index=False)["wartosc"].sum().rename(columns={"wartosc":"wartosc_sum"})
stats = (week_full.groupby("sku")["ilosc"]
         .agg(mu_tyg="mean", sigma_tyg="std", tyg_total="count", zero_weeks=lambda s: (s==0).mean())
         .reset_index())
stats["sigma_tyg"] = stats["sigma_tyg"].fillna(0.0)
stats = stats.merge(val_by_sku, on="sku", how="left").fillna({"wartosc_sum":0})
tot_val = stats["wartosc_sum"].sum()
stats["udzial"] = stats["wartosc_sum"]/max(1e-9, tot_val) if tot_val>0 else 0.0
stats = stats.sort_values("udzial", ascending=False); stats["kum"] = stats["udzial"].cumsum()
stats["klasa_ABC"] = np.where(stats["kum"]<=0.8,"A", np.where(stats["kum"]<=0.95,"B","C"))
stats["popyt_typ"] = np.where(stats["zero_weeks"]>0.4,"intermittent","ciągły")

# Plotly theming helper
def theme_fig(fig):
    fig.update_layout(
        colorway=colorway,
        paper_bgcolor=branding.get("plotly",{}).get("paper_bgcolor","#0f1117"),
        plot_bgcolor=branding.get("plotly",{}).get("plot_bgcolor","#0f1117"),
        font_color=branding.get("plotly",{}).get("font_color","#e2e8f0"),
    )
    fig.update_xaxes(gridcolor=branding.get("plotly",{}).get("gridcolor","#334155"))
    fig.update_yaxes(gridcolor=branding.get("plotly",{}).get("gridcolor","#334155"))
    return fig

with st.expander("🎨 EDA & Branding", expanded=True):
    pareto = stats.sort_values("udzial", ascending=False).reset_index(drop=True); pareto["cum_%"] = pareto["udzial"].cumsum()*100
    fig_p = go.Figure()
    fig_p.add_bar(x=pareto["sku"], y=pareto["udzial"]*100, name="Udział %")
    fig_p.add_scatter(x=pareto["sku"], y=pareto["cum_%"], name="Skumulowany %", yaxis="y2")
    theme_fig(fig_p)
    fig_p.update_layout(title="Pareto ABC (wartość)", yaxis_title="% udziału", yaxis2=dict(overlaying='y', side='right', title='Skumulowany %'))
    st.plotly_chart(fig_p, use_container_width=True)

    top40 = val_by_sku.sort_values("wartosc_sum", ascending=False)["sku"].head(40)
    heat = week_full[week_full["sku"].isin(top40)].pivot(index="sku", columns="tydzien", values="ilosc").fillna(0)
    fig_h = px.imshow(heat.values, aspect="auto", labels=dict(color="Ilość"), x=heat.columns.astype(str), y=heat.index, title="Heatmapa tygodniowa (Top-40)")
    theme_fig(fig_h)
    st.plotly_chart(fig_h, use_container_width=True)

# Modeling quick (reuse mean/std for μ/σ)
wk = week_full.pivot(index="sku", columns="tydzien", values="ilosc").fillna(0)
def intermittent(series, method="SBA"):
    z = series.astype(float).values
    # simple SBA proxy
    nz = z[z>0]
    if nz.size==0: return 0.0
    avg = nz.mean(); p = (z>0).mean()
    if method=="Croston": return avg/p if p>0 else 0.0
    if method=="TSB": return avg*p
    return avg*(1-0.1/2)/max(p,1e-9)

mu_rows = []
for sku in stats["sku"]:
    s = wk.loc[sku]
    if stats.loc[stats["sku"]==sku, "popyt_typ"].iloc[0]=="intermittent":
        mu = intermittent(s, inter_method); sig = float(s.std())
    else:
        mu = float(s.mean()); sig = float(s.std())
    mu_rows.append({"sku": sku, "mu_hat": mu, "sigma_hat": sig})
mu_df = pd.DataFrame(mu_rows)

# LT (fallback)
LT = (week_full.groupby("sku").size().reset_index(name="n").assign(LT_weeks=LT_default, LT_std_weeks=0.0, LT_n=0))[["sku","LT_weeks","LT_std_weeks","LT_n"]]

res = stats.merge(LT, on="sku", how="left").merge(mu_df, on="sku", how="left")
res["mu_eff"] = res["mu_hat"].fillna(res["mu_tyg"]); res["sigma_eff"] = res["sigma_hat"].fillna(res["sigma_tyg"])
avg_price = (raw.assign(unit_price=lambda d: np.where(d["ilosc"]>0, d["wartosc"]/np.maximum(d["ilosc"],1e-9), np.nan))
               .groupby("sku")["unit_price"].mean().reset_index())
res = res.merge(avg_price, on="sku", how="left"); res["unit_price"] = res["unit_price"].fillna(1.0)
res["SS"] = Z*np.sqrt(res["LT_weeks"]*(res["sigma_eff"]**2) + (res["mu_eff"]**2)*(res["LT_std_weeks"]**2))
res["ROP"] = res["mu_eff"]*res["LT_weeks"] + res["SS"]
res["h_abs"] = (h_pct/100.0) * res["unit_price"]
res["EOQ"] = np.where((res["mu_eff"]>0) & (res["h_abs"]>0), np.sqrt(2*200.0*res["mu_eff"]/res["h_abs"]), np.nan)

final_cols = ["sku","nazwa","kategoria","klasa_ABC","popyt_typ","mu_tyg","mu_hat","mu_eff","sigma_tyg","sigma_hat","sigma_eff","zero_weeks","LT_weeks","LT_std_weeks","LT_n","unit_price","SS","ROP","EOQ","wartosc_sum"]
final_tbl = res.merge(asort[["sku","nazwa","kategoria"]], on="sku", how="left") if not asort.empty else res
final_tbl = final_tbl.reindex(columns=final_cols, fill_value=np.nan)
st.dataframe(final_tbl.sort_values(["klasa_ABC","mu_eff"], ascending=[True, False]), use_container_width=True)

# Export & Report
@st.cache_data
def to_csv(df): return df.to_csv(index=False).encode("utf-8")
st.download_button("📥 CSV: rekomendacje v6.1", data=to_csv(final_tbl), file_name="rekomendacje_v6_1.csv")

st.subheader("🖨️ Raport PDF/PPTX (branding)")
if st.button("Generuj PDF + PPTX (branding)"):
    figs = {}
    try:
        figs["Pareto ABC"] = px.bar(pareto, x="sku", y=pareto["udzial"]*100).to_image(format="png")
    except Exception: figs["Pareto ABC"] = b""
    try:
        figs["Heatmapa Top-40"] = px.imshow(heat.values).to_image(format="png")
    except Exception: figs["Heatmapa Top-40"] = b""
    kpi = {
        "Rekordów": len(raw),
        "SKU": int(raw["sku"].nunique()),
        "Zakres": f"{raw['data'].min().date()} → {raw['data'].max().date()}",
        "A-klasa %": f"{(final_tbl['klasa_ABC'].eq('A').mean()*100):.1f}%",
        "Service": f"{int(service_level*100)}%",
        "LT (tyg.)": f"{LT_default}",
    }
    pdf_path = build_pdf("raport_zatowarowanie_v6_1.pdf", LOGO_PATH, kpi, figs, {"Rekomendacje Top-20": final_tbl.sort_values("mu_eff", ascending=False).head(20)}, branding_path=BRAND_PATH)
    pptx_path = build_pptx("prezentacja_zatowarowanie_v6_1.pptx", LOGO_PATH, kpi, figs, {"Rekomendacje Top-20": final_tbl.sort_values("mu_eff", ascending=False).head(20)}, branding_path=BRAND_PATH)
    with open(pdf_path, "rb") as f:
        st.download_button("📥 Pobierz PDF (branding)", data=f.read(), file_name=pdf_path)
    with open(pptx_path, "rb") as f:
        st.download_button("📥 Pobierz PPTX (branding)", data=f.read(), file_name=pptx_path)

st.success("Branding BI Advice włączony: logo + paleta kolorów + motyw wykresów")
