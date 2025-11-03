# oi/ui_components.py
import streamlit as st

def render_topbar(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="background: linear-gradient(120deg,#0f172a 0%,#1f2937 60%,#111827 100%); padding:1.25rem 1.5rem; border-radius:1rem; margin-bottom:1.5rem;">
            <h1 style="color:white; margin-bottom:0.3rem;">{title}</h1>
            <p style="color:#e2e8f0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_alert(text: str, level: str = "warn"):
    colors = {
        "warn": "#f97316",
        "ok": "#22c55e",
        "err": "#ef4444",
        "info": "#0ea5e9"
    }
    st.markdown(
        f"""
        <div style="border-left: 4px solid {colors.get(level,'#0ea5e9')}; padding:0.75rem 1rem; margin-bottom:0.75rem; background:rgba(15,23,42,0.02); border-radius:0.5rem;">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )
